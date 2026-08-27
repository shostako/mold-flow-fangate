"""Frame-thickness plate fed by a fan gate or the old tab gate + sprue
(``docs/spec.md``).

Top-down layout, grid frame (mm, y up, x right; the gate block sits below
the product like sim's film gate)::

    y_plate_top   = y_edge + plate_h
    y_edge        = y_gate_end + tab_len (0 if no tab)   product long edge (display y = 0)
    y_flat_start  = y_edge - tab_flat_len               tab: flat 1.0 next to the edge
    y_gate_end    = y_axis + gate_len                   gate end = compression-zone boundary
    y_axis        = pad + well_d / 2                    sprue axis = well center
    y = pad                                             half-circle bottom

Two gate shapes (``gate_type``), same axis position and ``gate_len``:

- ``"fan"``: half-circle (well) ∪ trapezoid whose short edge is ``well_d``
  on the axis line and whose long edge is ``fan_w`` at ``y_gate_end``.
  ``fan_thk`` uniform, or a linear taper ``fan_thk_well → fan_thk`` from the
  axis line to the long edge when ``fan_thk_well`` is set.
- ``"old"`` (the original tab gate): full well disc ∪ rectangle ``old_gate_w``
  wide from the axis line to ``y_gate_end``. ``old_gate_thk`` (4.0) from the
  well up to ``old_gate_ramp_len`` before the gate end, then a linear ramp
  down to ``old_gate_end_thk`` (2.0) at the gate end.

Tab (``tab_on``): the ``tab_len`` band between the gate end and the product
edge, spanning the **full product width** (the mold calls it the tab gate
land). ``tab_flat_thk`` on ``[y_flat_start, y_edge]``, linear
``tab_end_thk → tab_flat_thk`` on ``[y_gate_end, y_flat_start]``. Without
the tab the product edge sits directly on the gate end (the gate keeps its
shape; the product moves toward the sprue).

Balancer (``balancer_on``, sim's ▽ 肉盗み): an inverted isosceles triangle
carved into the gate body, centred on the axis. Its base (``balancer_w``
wide) lies on the gate end line so it touches the tab / product edge; its
apex points at the sprue, ``balancer_h`` below the gate end. Inside it the
thickness is ``balancer_thk`` (painted after the gate thickness, before the
well / slug). Clipped to the gate body, so a base wider than the gate at
that row simply loses its corners. Not part of the compression zone.

Plate: ``frame_thk`` on the ``frame_w`` border, ``inner_thk`` inside.
Well: disc ``well_d`` at the axis, thickness ``max(well_depth, gate)``.
Cold slug: disc ``slug_d`` under the axis, ``well_depth + slug_depth``.
Sprue: the Hele-Shaw model has no vertical channel; the sprue foot
(``sprue_bottom_d`` disc) is the Dirichlet τ=0 injection point.
``sprue_len`` / ``sprue_top_d`` are carried for a future nozzle
pressure-loss term only.

Compression (ICM): **product + tab** inflate together (``compression_mask``);
everything below the gate end (fan / old gate / well / slug) is the fixed
gate block. ``product_mask`` is the plate alone so the display origin stays
on the product edge.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .geometry import Geometry

GATE_TYPES = ("fan", "old")


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
    # gate: "fan" (fan gate) or "old" (the original tab gate). Both end at
    # gate_len from the sprue axis; that end is the compression-zone boundary
    gate_type: str = "fan"
    gate_len_mm: float = 40.0  # axis line → gate end
    # tab (gate end → product edge), full product width; the compressed land
    tab_on: bool = True
    tab_len_mm: float = 10.0
    tab_flat_len_mm: float = 2.0
    tab_flat_thk_mm: float = 1.0
    tab_end_thk_mm: float = 2.0
    # fan gate: trapezoid long edge (tab side) → short edge = well_d (axis line)
    fan_w_mm: float = 250.0
    fan_thk_mm: float = 2.0  # at the gate end (uniform when fan_thk_well_mm is None)
    fan_thk_well_mm: float | None = None  # at the axis line; enables a linear taper
    # old tab gate: rectangle old_gate_w wide, old_gate_thk from the well up to
    # old_gate_ramp_len before the gate end, then a ramp down to old_gate_end_thk
    old_gate_w_mm: float = 30.0
    old_gate_thk_mm: float = 4.0
    old_gate_ramp_len_mm: float = 15.0
    old_gate_end_thk_mm: float = 2.0
    # balancer: inverted triangle thinning, base on the gate end line, apex toward the sprue
    balancer_on: bool = False
    balancer_w_mm: float = 100.0  # base width on the gate end line
    balancer_h_mm: float = 20.0  # gate end → apex
    balancer_thk_mm: float = 1.0  # thickness inside the triangle
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
            ("gate_len_mm", self.gate_len_mm),
            ("tab_len_mm", self.tab_len_mm),
            ("tab_flat_thk_mm", self.tab_flat_thk_mm),
            ("tab_end_thk_mm", self.tab_end_thk_mm),
            ("fan_w_mm", self.fan_w_mm),
            ("fan_thk_mm", self.fan_thk_mm),
            ("old_gate_w_mm", self.old_gate_w_mm),
            ("old_gate_thk_mm", self.old_gate_thk_mm),
            ("old_gate_end_thk_mm", self.old_gate_end_thk_mm),
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
            ("tab_flat_len_mm", self.tab_flat_len_mm),
            ("old_gate_ramp_len_mm", self.old_gate_ramp_len_mm),
            ("slug_depth_mm", self.slug_depth_mm),
            ("pad_mm", self.pad_mm),
        ):
            if val < 0:
                raise ValueError(f"{name} must be ≥ 0 (got {val})")
        if self.gate_type not in GATE_TYPES:
            raise ValueError(f"gate_type must be one of {GATE_TYPES} (got {self.gate_type!r})")
        if self.fan_thk_well_mm is not None and self.fan_thk_well_mm <= 0:
            raise ValueError(
                f"fan_thk_well_mm must be positive when set (got {self.fan_thk_well_mm})"
            )
        if 2 * self.frame_w_mm >= min(self.plate_w_mm, self.plate_h_mm) - eps:
            raise ValueError(
                f"frame_w_mm ({self.frame_w_mm}) must be < half of the smaller plate side"
            )
        if self.tab_flat_len_mm > self.tab_len_mm + eps:
            raise ValueError(
                f"tab_flat_len_mm ({self.tab_flat_len_mm}) must be ≤ tab_len_mm ({self.tab_len_mm})"
            )
        if self.gate_type == "fan":
            if self.fan_w_mm > self.plate_w_mm + eps:
                raise ValueError(
                    f"fan_w_mm ({self.fan_w_mm}) must be ≤ plate_w_mm ({self.plate_w_mm})"
                )
            if self.fan_w_mm < self.well_d_mm - eps:
                raise ValueError(
                    f"fan_w_mm ({self.fan_w_mm}) must be ≥ well_d_mm ({self.well_d_mm}); "
                    f"inverted trapezoid is not supported"
                )
        else:
            # the full well disc sits inside the constant-thickness part of the
            # gate: the ramp starts at or above the disc top, and the disc top is
            # at or below the gate end (else it would leak into the tab/product)
            if self.old_gate_ramp_len_mm + self.well_d_mm / 2.0 > self.gate_len_mm + eps:
                raise ValueError(
                    f"old gate: gate_len_mm ({self.gate_len_mm}) must be ≥ "
                    f"old_gate_ramp_len_mm ({self.old_gate_ramp_len_mm}) + well_d_mm / 2 "
                    f"({self.well_d_mm / 2.0}) so the well stays in the constant-thickness part"
                )
            if self.old_gate_w_mm > self.plate_w_mm + eps:
                raise ValueError(
                    f"old_gate_w_mm ({self.old_gate_w_mm}) must be ≤ plate_w_mm ({self.plate_w_mm})"
                )
            if self.cell_size_mm > self.old_gate_w_mm + eps:
                raise ValueError(
                    f"cell_size_mm ({self.cell_size_mm}) must be ≤ old_gate_w_mm ({self.old_gate_w_mm}); "
                    f"a mesh coarser than the gate body leaves the well disconnected"
                )
        if self.balancer_on:
            for name, val in (
                ("balancer_w_mm", self.balancer_w_mm),
                ("balancer_h_mm", self.balancer_h_mm),
                ("balancer_thk_mm", self.balancer_thk_mm),
            ):
                if val <= 0:
                    raise ValueError(f"{name} must be positive when balancer_on (got {val})")
            gate_w = self.fan_w_mm if self.gate_type == "fan" else self.old_gate_w_mm
            if self.balancer_w_mm > gate_w + eps:
                raise ValueError(
                    f"balancer_w_mm ({self.balancer_w_mm}) must be ≤ the gate width at the "
                    f"gate end ({gate_w})"
                )
            # the apex must stay clear of the well disc (sim: clear of the valve disk)
            h_max = self.gate_len_mm - self.well_d_mm / 2.0
            if self.balancer_h_mm > h_max + eps:
                raise ValueError(
                    f"balancer_h_mm ({self.balancer_h_mm}) must be ≤ gate_len_mm − well_d_mm / 2 "
                    f"({h_max}) so the apex stays outside the well"
                )
        if self.slug_d_mm > self.well_d_mm + eps:
            raise ValueError(f"slug_d_mm ({self.slug_d_mm}) must be ≤ well_d_mm ({self.well_d_mm})")
        if self.sprue_bottom_d_mm > self.well_d_mm + eps:
            raise ValueError(
                f"sprue_bottom_d_mm ({self.sprue_bottom_d_mm}) must be ≤ well_d_mm ({self.well_d_mm})"
            )
        if self.cell_size_mm > self.well_d_mm + eps:
            raise ValueError(
                f"cell_size_mm ({self.cell_size_mm}) must be ≤ well_d_mm ({self.well_d_mm}); "
                f"a mesh coarser than the well cannot resolve the gate block"
            )

    # ----- derived y-levels (grid frame, mm) -----
    @property
    def y_axis_mm(self) -> float:
        return self.pad_mm + self.well_d_mm / 2.0

    @property
    def y_gate_end_mm(self) -> float:
        """Gate end = compression-zone boundary (tab start, or the product edge)."""
        return self.y_axis_mm + self.gate_len_mm

    @property
    def tab_len_eff_mm(self) -> float:
        return self.tab_len_mm if self.tab_on else 0.0

    @property
    def y_edge_mm(self) -> float:
        """Product long edge (display ``y = 0``)."""
        return self.y_gate_end_mm + self.tab_len_eff_mm

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
    y_gate_end = cfg.y_gate_end_mm
    y_edge = cfg.y_edge_mm
    y_top = cfg.y_plate_top_mm
    y_flat_start = y_edge - cfg.tab_flat_len_mm
    r_well = cfg.well_d_mm / 2.0

    total_w = 2 * pad + cfg.plate_w_mm
    total_h = pad + r_well + cfg.gate_len_mm + cfg.tab_len_eff_mm + cfg.plate_h_mm + pad
    nx = int(round(total_w / dx))
    ny = int(round(total_h / dx))

    iy_idx, ix_idx = np.meshgrid(np.arange(ny), np.arange(nx), indexing="ij")
    yy = (iy_idx + 0.5) * dx
    xx = (ix_idx + 0.5) * dx
    ax = np.abs(xx - cx)
    r2_axis = (xx - cx) ** 2 + (yy - y_axis) ** 2

    # --- silhouette ---
    in_well = r2_axis <= r_well**2
    t_gate = np.clip((yy - y_axis) / max(cfg.gate_len_mm, 1e-12), 0.0, 1.0)
    if cfg.gate_type == "fan":
        half_w_at_y = 0.5 * (cfg.well_d_mm + (cfg.fan_w_mm - cfg.well_d_mm) * t_gate)
        in_gate_body = (yy >= y_axis) & (yy <= y_gate_end) & (ax <= half_w_at_y)
        in_gate = in_gate_body | (in_well & (yy <= y_axis))
    else:
        in_gate_body = (yy >= y_axis) & (yy <= y_gate_end) & (ax <= cfg.old_gate_w_mm / 2.0)
        in_gate = in_gate_body | in_well
    in_x_plate = (xx >= pad) & (xx <= pad + cfg.plate_w_mm)
    in_tab = (
        (yy > y_gate_end) & (yy <= y_edge) & in_x_plate if cfg.tab_on else np.zeros_like(in_gate)
    )
    in_plate = (yy > y_edge) & (yy <= y_top) & in_x_plate
    mask = in_gate | in_tab | in_plate
    if not mask.any():
        raise ValueError(
            f"cell_size_mm ({dx}) rasterises the whole cavity away ({ny}x{nx} grid, no cavity cell)"
        )

    # --- thickness ---
    thk = np.zeros_like(xx, dtype=float)

    if cfg.gate_type == "fan":
        # uniform, or linear taper axis line → gate end
        if cfg.fan_thk_well_mm is None:
            gate_thk = np.full_like(xx, cfg.fan_thk_mm, dtype=float)
        else:
            gate_thk = cfg.fan_thk_well_mm + (cfg.fan_thk_mm - cfg.fan_thk_well_mm) * t_gate
    else:
        # old_gate_thk up to the ramp start, then linear down to old_gate_end_thk
        y_ramp_start = y_gate_end - cfg.old_gate_ramp_len_mm
        if cfg.old_gate_ramp_len_mm > 1e-12:
            t_ramp = np.clip((yy - y_ramp_start) / cfg.old_gate_ramp_len_mm, 0.0, 1.0)
        else:
            t_ramp = np.zeros_like(yy)
        gate_thk = cfg.old_gate_thk_mm + (cfg.old_gate_end_thk_mm - cfg.old_gate_thk_mm) * t_ramp
    thk[in_gate] = gate_thk[in_gate]

    # balancer: base on the gate end line (touches the tab / product edge),
    # apex balancer_h toward the sprue; half-width grows linearly apex → base
    if cfg.balancer_on:
        y_apex = y_gate_end - cfg.balancer_h_mm
        t_bal = np.clip((yy - y_apex) / max(cfg.balancer_h_mm, 1e-12), 0.0, 1.0)
        in_balancer = (
            in_gate_body
            & (yy >= y_apex)
            & (yy <= y_gate_end)
            & (ax <= 0.5 * cfg.balancer_w_mm * t_bal)
        )
        thk[in_balancer] = cfg.balancer_thk_mm

    # well pocket and cold slug (deeper than the gate where they overlap)
    thk[in_well] = np.maximum(thk[in_well], cfg.well_depth_mm)
    in_slug = r2_axis <= (cfg.slug_d_mm / 2.0) ** 2
    thk[in_slug] = cfg.well_depth_mm + cfg.slug_depth_mm

    # tab: ramp tab_end_thk (gate end) → tab_flat_thk (flat start), then flat
    if cfg.tab_on:
        ramp_len = cfg.tab_len_mm - cfg.tab_flat_len_mm
        if ramp_len > 1e-12:
            t_tab = np.clip((yy - y_gate_end) / ramp_len, 0.0, 1.0)
        else:
            t_tab = np.ones_like(yy)
        tab_thk = cfg.tab_end_thk_mm + (cfg.tab_flat_thk_mm - cfg.tab_end_thk_mm) * t_tab
        thk[in_tab] = tab_thk[in_tab]
        thk[in_tab & (yy > y_flat_start)] = cfg.tab_flat_thk_mm

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
        label="fan_gate_plate" if cfg.gate_type == "fan" else "old_gate_plate",
        compression_mask=(in_plate | in_tab) & mask,
        product_mask=in_plate & mask,
        valve_axis_x_mm=cx,
    )

    # --- injection point: sprue foot disc at the axis ---
    in_sprue = r2_axis <= (cfg.sprue_bottom_d_mm / 2.0) ** 2
    gate_iys, gate_ixs = np.where(in_sprue & mask)
    if gate_iys.size == 0:
        # Mesh coarser than the sprue foot: no cell centre lands inside the
        # disc. Snap to the cavity cell nearest the axis so every built
        # geometry has an injection boundary (a coarse mesh must not
        # silently produce a gate-less cavity).
        d2 = np.where(mask, r2_axis, np.inf)
        ic_y, ic_x = np.unravel_index(int(np.argmin(d2)), d2.shape)
        geom.gates.append((int(ic_y), int(ic_x)))
    else:
        for iy, ix in zip(gate_iys, gate_ixs, strict=True):
            geom.gates.append((int(iy), int(ix)))
    return geom
