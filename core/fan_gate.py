"""Frame-thickness plate fed by a fan gate + sprue (``docs/spec.md``).

Top-down layout, grid frame (mm, y up, x right; the gate block sits below
the product like sim's film gate)::

    y_plate_top   = y_edge + plate_h
    y_edge        = y_fan_end + land_len         product long edge (display y = 0)
    y_flat_start  = y_edge - land_flat_len       land: flat 0.6 next to the edge
    y_fan_end     = y_axis + fan_len             land: ramp end (2.5), fan long edge
    y_axis        = pad + well_d / 2             sprue axis = well center = trapezoid
                                                 short edge (width = well_d)
    y = pad                                      half-circle bottom

Silhouette = half-circle (well) ∪ trapezoid (fan) ∪ land band ∪ plate.
The land band spans the **full product width** (not the fan width); the
fan's long edge (``fan_w``) joins the land's 2.5 mm end.

Thickness (mm, continuous in y except at the frame/inner step):

- plate: ``frame_thk`` on the ``frame_w`` border, ``inner_thk`` inside
- land: ``land_flat_thk`` on ``[y_flat_start, y_edge]``; linear
  ``land_end_thk → land_flat_thk`` on ``[y_fan_end, y_flat_start]``
- fan (half-circle + trapezoid): ``fan_thk`` uniform, or a linear taper
  ``fan_thk_well → fan_thk`` from the axis line to the long edge when
  ``fan_thk_well`` is set
- well: disc ``well_d`` at the axis, thickness ``max(well_depth, fan)``
- cold slug: disc ``slug_d`` under the axis, ``well_depth + slug_depth``
- sprue: the Hele-Shaw model has no vertical channel; the sprue foot
  (``sprue_bottom_d`` disc) is the Dirichlet τ=0 injection point.
  ``sprue_len`` / ``sprue_top_d`` are carried for a future nozzle
  pressure-loss term only.

Compression (ICM): **product + land band** inflate together
(``compression_mask``); the fan / well / slug are the fixed gate block.
``product_mask`` is the plate alone so the display origin stays on the
product edge.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .geometry import Geometry


@dataclass(frozen=True)
class FanGatePlateConfig:
    """Parameters for :func:`build_fan_gate_plate_geometry`. Defaults are the
    spec'd mold (``docs/spec.md``)."""

    # product
    plate_w_mm: float = 315.0
    plate_h_mm: float = 183.0
    frame_w_mm: float = 15.0
    frame_thk_mm: float = 1.0
    inner_thk_mm: float = 4.0
    # land band (product edge → fan), full product width
    land_len_mm: float = 10.0
    land_flat_len_mm: float = 2.0
    land_flat_thk_mm: float = 0.6
    land_end_thk_mm: float = 2.5
    # fan gate: trapezoid long edge (land side) → short edge = well_d (axis line)
    fan_w_mm: float = 250.0
    fan_len_mm: float = 50.0  # axis line → land 2.5 end
    fan_thk_mm: float = 2.5  # at the land end (uniform when fan_thk_well_mm is None)
    fan_thk_well_mm: float | None = None  # at the axis line; enables a linear taper
    # well (pocket at the sprue foot) and cold slug
    well_d_mm: float = 20.0
    well_depth_mm: float = 3.0
    slug_d_mm: float = 6.0
    slug_depth_mm: float = 5.0
    # sprue bush (top = injection point)
    sprue_len_mm: float = 15.0
    sprue_top_d_mm: float = 4.0
    sprue_bottom_d_mm: float = 6.0
    # discretisation
    cell_size_mm: float = 1.0
    pad_mm: float = 5.0

    def validate(self) -> None:
        eps = 1e-6
        positives = (
            ("plate_w_mm", self.plate_w_mm),
            ("plate_h_mm", self.plate_h_mm),
            ("frame_thk_mm", self.frame_thk_mm),
            ("inner_thk_mm", self.inner_thk_mm),
            ("land_len_mm", self.land_len_mm),
            ("land_flat_thk_mm", self.land_flat_thk_mm),
            ("land_end_thk_mm", self.land_end_thk_mm),
            ("fan_w_mm", self.fan_w_mm),
            ("fan_len_mm", self.fan_len_mm),
            ("fan_thk_mm", self.fan_thk_mm),
            ("well_d_mm", self.well_d_mm),
            ("well_depth_mm", self.well_depth_mm),
            ("slug_d_mm", self.slug_d_mm),
            ("sprue_len_mm", self.sprue_len_mm),
            ("sprue_top_d_mm", self.sprue_top_d_mm),
            ("sprue_bottom_d_mm", self.sprue_bottom_d_mm),
            ("cell_size_mm", self.cell_size_mm),
        )
        for name, val in positives:
            if val <= 0:
                raise ValueError(f"{name} must be positive (got {val})")
        for name, val in (
            ("frame_w_mm", self.frame_w_mm),
            ("land_flat_len_mm", self.land_flat_len_mm),
            ("slug_depth_mm", self.slug_depth_mm),
            ("pad_mm", self.pad_mm),
        ):
            if val < 0:
                raise ValueError(f"{name} must be ≥ 0 (got {val})")
        if self.fan_thk_well_mm is not None and self.fan_thk_well_mm <= 0:
            raise ValueError(
                f"fan_thk_well_mm must be positive when set (got {self.fan_thk_well_mm})"
            )
        if 2 * self.frame_w_mm >= min(self.plate_w_mm, self.plate_h_mm) - eps:
            raise ValueError(
                f"frame_w_mm ({self.frame_w_mm}) must be < half of the smaller plate side"
            )
        if self.land_flat_len_mm > self.land_len_mm + eps:
            raise ValueError(
                f"land_flat_len_mm ({self.land_flat_len_mm}) must be ≤ land_len_mm ({self.land_len_mm})"
            )
        if self.fan_w_mm > self.plate_w_mm + eps:
            raise ValueError(f"fan_w_mm ({self.fan_w_mm}) must be ≤ plate_w_mm ({self.plate_w_mm})")
        if self.fan_w_mm < self.well_d_mm - eps:
            raise ValueError(
                f"fan_w_mm ({self.fan_w_mm}) must be ≥ well_d_mm ({self.well_d_mm}); "
                f"inverted trapezoid is not supported"
            )
        if self.slug_d_mm > self.well_d_mm + eps:
            raise ValueError(f"slug_d_mm ({self.slug_d_mm}) must be ≤ well_d_mm ({self.well_d_mm})")
        if self.sprue_bottom_d_mm > self.well_d_mm + eps:
            raise ValueError(
                f"sprue_bottom_d_mm ({self.sprue_bottom_d_mm}) must be ≤ well_d_mm ({self.well_d_mm})"
            )

    # ----- derived y-levels (grid frame, mm) -----
    @property
    def y_axis_mm(self) -> float:
        return self.pad_mm + self.well_d_mm / 2.0

    @property
    def y_fan_end_mm(self) -> float:
        return self.y_axis_mm + self.fan_len_mm

    @property
    def y_edge_mm(self) -> float:
        """Product long edge (display ``y = 0``)."""
        return self.y_fan_end_mm + self.land_len_mm

    @property
    def y_plate_top_mm(self) -> float:
        return self.y_edge_mm + self.plate_h_mm

    @property
    def axis_x_mm(self) -> float:
        return self.pad_mm + self.plate_w_mm / 2.0


def build_fan_gate_plate_geometry(cfg: FanGatePlateConfig) -> Geometry:
    """Rasterise :class:`FanGatePlateConfig` onto a square-cell grid."""
    cfg.validate()

    pad = cfg.pad_mm
    dx = cfg.cell_size_mm
    cx = cfg.axis_x_mm
    y_axis = cfg.y_axis_mm
    y_fan_end = cfg.y_fan_end_mm
    y_edge = cfg.y_edge_mm
    y_top = cfg.y_plate_top_mm
    y_flat_start = y_edge - cfg.land_flat_len_mm
    r_well = cfg.well_d_mm / 2.0

    total_w = 2 * pad + cfg.plate_w_mm
    total_h = pad + r_well + cfg.fan_len_mm + cfg.land_len_mm + cfg.plate_h_mm + pad
    nx = int(round(total_w / dx))
    ny = int(round(total_h / dx))

    iy_idx, ix_idx = np.meshgrid(np.arange(ny), np.arange(nx), indexing="ij")
    yy = (iy_idx + 0.5) * dx
    xx = (ix_idx + 0.5) * dx
    ax = np.abs(xx - cx)
    r2_axis = (xx - cx) ** 2 + (yy - y_axis) ** 2

    # --- silhouette ---
    in_half_circle = (r2_axis <= r_well**2) & (yy <= y_axis)
    t_fan = np.clip((yy - y_axis) / max(cfg.fan_len_mm, 1e-12), 0.0, 1.0)
    half_w_at_y = 0.5 * (cfg.well_d_mm + (cfg.fan_w_mm - cfg.well_d_mm) * t_fan)
    in_trapezoid = (yy >= y_axis) & (yy <= y_fan_end) & (ax <= half_w_at_y)
    in_x_plate = (xx >= pad) & (xx <= pad + cfg.plate_w_mm)
    in_land = (yy > y_fan_end) & (yy <= y_edge) & in_x_plate
    in_plate = (yy > y_edge) & (yy <= y_top) & in_x_plate
    mask = in_half_circle | in_trapezoid | in_land | in_plate

    # --- thickness ---
    thk = np.zeros_like(xx, dtype=float)

    # fan block (half-circle + trapezoid): uniform or linear taper axis → land end
    if cfg.fan_thk_well_mm is None:
        fan_thk = np.full_like(xx, cfg.fan_thk_mm, dtype=float)
    else:
        fan_thk = cfg.fan_thk_well_mm + (cfg.fan_thk_mm - cfg.fan_thk_well_mm) * t_fan
    in_fan = in_half_circle | in_trapezoid
    thk[in_fan] = fan_thk[in_fan]

    # well pocket and cold slug (deeper than the fan where they overlap)
    in_well = r2_axis <= r_well**2
    thk[in_well] = np.maximum(thk[in_well], cfg.well_depth_mm)
    in_slug = r2_axis <= (cfg.slug_d_mm / 2.0) ** 2
    thk[in_slug] = cfg.well_depth_mm + cfg.slug_depth_mm

    # land band: ramp land_end_thk (fan end) → land_flat_thk (flat start), then flat
    ramp_len = cfg.land_len_mm - cfg.land_flat_len_mm
    if ramp_len > 1e-12:
        t_land = np.clip((yy - y_fan_end) / ramp_len, 0.0, 1.0)
    else:
        t_land = np.ones_like(yy)
    land_thk = cfg.land_end_thk_mm + (cfg.land_flat_thk_mm - cfg.land_end_thk_mm) * t_land
    thk[in_land] = land_thk[in_land]
    thk[in_land & (yy > y_flat_start)] = cfg.land_flat_thk_mm

    # plate: frame border vs inner body
    in_inner = (
        in_plate
        & (xx > pad + cfg.frame_w_mm)
        & (xx < pad + cfg.plate_w_mm - cfg.frame_w_mm)
        & (yy > y_edge + cfg.frame_w_mm)
        & (yy < y_top - cfg.frame_w_mm)
    )
    thk[in_plate] = cfg.frame_thk_mm
    thk[in_inner] = cfg.inner_thk_mm

    thk[~mask] = 0.0

    geom = Geometry(
        mask=mask,
        thickness_mm=thk,
        cell_size_mm=dx,
        label="fan_gate_plate",
        compression_mask=(in_plate | in_land) & mask,
        product_mask=in_plate & mask,
        valve_axis_x_mm=cx,
    )

    # --- injection point: sprue foot disc at the axis ---
    in_sprue = r2_axis <= (cfg.sprue_bottom_d_mm / 2.0) ** 2
    gate_iys, gate_ixs = np.where(in_sprue & mask)
    if gate_iys.size == 0:
        ic_y = int(np.argmin(np.abs(yy[:, 0] - y_axis)))
        ic_x = int(np.argmin(np.abs(xx[0, :] - cx)))
        if mask[ic_y, ic_x]:
            geom.gates.append((ic_y, ic_x))
    else:
        for iy, ix in zip(gate_iys, gate_ixs, strict=True):
            geom.gates.append((int(iy), int(ix)))
    return geom
