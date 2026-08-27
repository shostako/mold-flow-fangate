"""Tests for the fan-gate plate builder (``core/fan_gate.py``)."""

from __future__ import annotations

import numpy as np
import pytest

from core import (
    FanGatePlateConfig,
    HeleShawSolver,
    MaterialDB,
    build_fan_gate_plate_geometry,
)


def _cfg(**overrides) -> FanGatePlateConfig:
    return FanGatePlateConfig(**overrides)


def _grid_mm(g):
    iy, ix = np.indices(g.mask.shape)
    return (iy + 0.5) * g.cell_size_mm, (ix + 0.5) * g.cell_size_mm


# ---------------------------------------------------------------- basics


@pytest.mark.parametrize("cell", [1.0, 2.0, 5.0, 18.0])
def test_every_resolution_yields_an_injection_gate_near_the_axis(cell) -> None:
    """A mesh coarser than the sprue foot must still get a gate (Codex P2 on
    PR #3): the fallback snaps to the cavity cell nearest the axis."""
    cfg = _cfg(cell_size_mm=cell)
    g = build_fan_gate_plate_geometry(cfg)
    assert g.gates
    yy, xx = _grid_mm(g)
    for iy, ix in g.gates:
        assert g.mask[iy, ix]
        r = np.hypot(xx[iy, ix] - cfg.axis_x_mm, yy[iy, ix] - cfg.y_axis_mm)
        # fine mesh: inside the sprue-foot disc; coarse mesh: the snapped cell
        assert r <= max(cfg.sprue_bottom_d_mm / 2.0, cell * 1.5) + 1e-9
    HeleShawSolver(geometry=g, material=MaterialDB()["PP"], injection_volume_flow_cm3s=50.0).solve(
        num_frames=2
    )


def test_builds_with_spec_defaults() -> None:
    g = build_fan_gate_plate_geometry(_cfg())
    assert g.label == "fan_gate_plate"
    assert g.mask.any()
    assert g.gates
    assert g.volume_cm3() > 0


def test_gate_cells_are_inside_mask_and_centred_on_the_axis() -> None:
    cfg = _cfg()
    g = build_fan_gate_plate_geometry(cfg)
    yy, xx = _grid_mm(g)
    for iy, ix in g.gates:
        assert g.mask[iy, ix]
        r = np.hypot(xx[iy, ix] - cfg.axis_x_mm, yy[iy, ix] - cfg.y_axis_mm)
        assert r <= cfg.sprue_bottom_d_mm / 2.0 + 1e-9


def test_thickness_is_zero_outside_mask() -> None:
    g = build_fan_gate_plate_geometry(_cfg())
    assert np.all(g.thickness_mm[~g.mask] == 0.0)


def test_product_volume_matches_the_analytic_frame_plate() -> None:
    cfg = _cfg()
    g = build_fan_gate_plate_geometry(cfg)
    inner_w = cfg.plate_w_mm - 2 * cfg.frame_w_mm
    inner_h = cfg.plate_h_mm - 2 * cfg.frame_w_mm
    frame_area = cfg.plate_w_mm * cfg.plate_h_mm - inner_w * inner_h
    expected = (frame_area * cfg.frame_thk_mm + inner_w * inner_h * cfg.inner_thk_mm) / 1000.0
    got = float(g.thickness_mm[g.product_mask].sum()) * g.cell_size_mm**2 / 1000.0
    assert got == pytest.approx(expected, rel=1e-6)


# ------------------------------------------------------------- thickness


def test_plate_has_frame_and_inner_thickness() -> None:
    cfg = _cfg()
    g = build_fan_gate_plate_geometry(cfg)
    yy, xx = _grid_mm(g)
    pad = cfg.pad_mm
    # frame: a point on the gate-side border strip, mid-width
    frame_pt = (
        (yy > cfg.y_edge_mm + 2)
        & (yy < cfg.y_edge_mm + cfg.frame_w_mm - 2)
        & (np.abs(xx - cfg.axis_x_mm) < 1)
    )
    inner_pt = (np.abs(yy - (cfg.y_edge_mm + cfg.plate_h_mm / 2)) < 1) & (
        np.abs(xx - cfg.axis_x_mm) < 1
    )
    side_pt = (
        (np.abs(yy - (cfg.y_edge_mm + cfg.plate_h_mm / 2)) < 1)
        & (xx > pad + 2)
        & (xx < pad + cfg.frame_w_mm - 2)
    )
    assert np.all(g.thickness_mm[frame_pt] == cfg.frame_thk_mm)
    assert np.all(g.thickness_mm[side_pt] == cfg.frame_thk_mm)
    assert np.all(g.thickness_mm[inner_pt] == cfg.inner_thk_mm)


def test_land_band_is_flat_next_to_the_edge_and_ramps_toward_the_fan() -> None:
    cfg = _cfg()
    g = build_fan_gate_plate_geometry(cfg)
    yy, xx = _grid_mm(g)
    on_axis = np.abs(xx - cfg.axis_x_mm) < 1
    flat = on_axis & (yy > cfg.y_edge_mm - cfg.tab_flat_len_mm) & (yy < cfg.y_edge_mm)
    ramp = on_axis & (yy > cfg.y_gate_end_mm) & (yy < cfg.y_edge_mm - cfg.tab_flat_len_mm)
    assert flat.any() and ramp.any()
    assert np.all(g.thickness_mm[flat] == cfg.tab_flat_thk_mm)
    h_ramp = g.thickness_mm[ramp]
    assert h_ramp.min() > cfg.tab_flat_thk_mm
    assert h_ramp.max() < cfg.tab_end_thk_mm + 1e-9
    # monotone: thicker toward the fan (lower y)
    ys = yy[ramp]
    order = np.argsort(ys)
    assert np.all(np.diff(h_ramp[order]) <= 1e-9)


def test_land_band_spans_the_full_product_width() -> None:
    cfg = _cfg()
    g = build_fan_gate_plate_geometry(cfg)
    yy, xx = _grid_mm(g)
    land_row = (yy > cfg.y_edge_mm - 1) & (yy < cfg.y_edge_mm)
    x_land = xx[land_row & g.mask]
    assert x_land.min() == pytest.approx(cfg.pad_mm + g.cell_size_mm / 2)
    assert x_land.max() == pytest.approx(cfg.pad_mm + cfg.plate_w_mm - g.cell_size_mm / 2)
    # the last fan row (just below the land) is the trapezoid's analytic
    # width at that row, not the land width
    fan_row = (yy > cfg.y_gate_end_mm - g.cell_size_mm) & (yy < cfg.y_gate_end_mm)
    y_row = float(yy[fan_row][0])
    t = (y_row - cfg.y_axis_mm) / cfg.gate_len_mm
    w_expected = cfg.well_d_mm + (cfg.fan_w_mm - cfg.well_d_mm) * t
    x_fan = xx[fan_row & g.mask]
    w_got = x_fan.max() - x_fan.min() + g.cell_size_mm
    assert abs(w_got - w_expected) <= 2 * g.cell_size_mm
    assert w_got < cfg.plate_w_mm - 10


def test_fan_is_uniform_by_default_and_tapers_when_asked() -> None:
    cfg = _cfg()
    g = build_fan_gate_plate_geometry(cfg)
    yy, xx = _grid_mm(g)
    fan = (
        g.mask
        & (yy > cfg.y_axis_mm + cfg.well_d_mm)
        & (yy < cfg.y_gate_end_mm)
        & (np.abs(xx - cfg.axis_x_mm) < 3)
    )
    assert np.all(g.thickness_mm[fan] == cfg.fan_thk_mm)

    cfg_t = _cfg(fan_thk_well_mm=4.0)
    gt = build_fan_gate_plate_geometry(cfg_t)
    h = gt.thickness_mm[fan]
    ys = yy[fan]
    assert h.max() <= 4.0 + 1e-9 and h.min() >= cfg_t.fan_thk_mm - 1e-9
    order = np.argsort(ys)
    assert np.all(np.diff(h[order]) <= 1e-9)  # thinner toward the land
    assert gt.volume_cm3() > g.volume_cm3()


def test_well_and_cold_slug_are_deeper_than_the_fan() -> None:
    cfg = _cfg()
    g = build_fan_gate_plate_geometry(cfg)
    yy, xx = _grid_mm(g)
    r = np.hypot(xx - cfg.axis_x_mm, yy - cfg.y_axis_mm)
    slug = g.mask & (r <= cfg.slug_d_mm / 2 - 0.5)
    well_ring = g.mask & (r >= cfg.slug_d_mm / 2 + 0.5) & (r <= cfg.well_d_mm / 2 - 0.5)
    assert slug.any() and well_ring.any()
    assert np.all(g.thickness_mm[slug] == cfg.well_depth_mm + cfg.slug_depth_mm)
    assert np.all(g.thickness_mm[well_ring] == cfg.well_depth_mm)


# --------------------------------------------------------------- masks


def test_compression_zone_is_product_plus_land_and_excludes_the_gate_block() -> None:
    cfg = _cfg()
    g = build_fan_gate_plate_geometry(cfg)
    yy, xx = _grid_mm(g)
    cm = g.compression_mask
    assert cm is not None and g.product_mask is not None
    assert np.all(cm[g.product_mask])
    land = g.mask & (yy > cfg.y_gate_end_mm) & (yy < cfg.y_edge_mm)
    assert land.any() and np.all(cm[land])
    gate_block = g.mask & (yy < cfg.y_gate_end_mm)
    assert gate_block.any() and not cm[gate_block].any()
    # product is strictly the plate: no land, no gate block
    assert not g.product_mask[land].any()
    assert not g.product_mask[gate_block].any()
    assert cm.sum() == g.product_mask.sum() + land.sum()


def test_display_origin_sits_on_the_product_edge_not_the_land() -> None:
    cfg = _cfg()
    g = build_fan_gate_plate_geometry(cfg)
    x0, y0 = g.display_origin_mm()
    assert x0 == pytest.approx(cfg.axis_x_mm)
    assert y0 == pytest.approx(cfg.y_edge_mm)
    # without product_mask the compression zone (incl. land) would win
    g.product_mask = None
    _, y0_cm = g.display_origin_mm()
    assert y0_cm == pytest.approx(cfg.y_gate_end_mm)


def test_stroke_compression_inflates_land_together_with_the_plate() -> None:
    cfg = _cfg(cell_size_mm=2.0)
    g = build_fan_gate_plate_geometry(cfg)
    yy, xx = _grid_mm(g)
    s = HeleShawSolver(
        geometry=g,
        material=MaterialDB()["PP"],
        injection_volume_flow_cm3s=50.0,
        compression_molding=True,
        compression_stroke_mm=0.5,
    )
    h_open = s._open_thickness_field()
    land = g.mask & (yy > cfg.y_gate_end_mm) & (yy < cfg.y_edge_mm)
    gate_block = g.mask & (yy < cfg.y_gate_end_mm)
    assert np.allclose(h_open[land] - g.thickness_mm[land], 0.5)
    assert np.allclose(h_open[g.product_mask] - g.thickness_mm[g.product_mask], 0.5)
    assert np.allclose(h_open[gate_block], g.thickness_mm[gate_block])


# -------------------------------------------------------------- solver


def test_solver_runs_and_fills_from_the_sprue_outward() -> None:
    cfg = _cfg(cell_size_mm=2.0)
    g = build_fan_gate_plate_geometry(cfg)
    r = HeleShawSolver(
        geometry=g, material=MaterialDB()["PP"], injection_volume_flow_cm3s=50.0
    ).solve(num_frames=4)
    ft = r.fill_time_s
    assert np.isfinite(ft[g.mask]).all()
    yy, xx = _grid_mm(g)
    far_corner = g.mask & (yy > cfg.y_plate_top_mm - 3) & (xx < cfg.pad_mm + 3)
    near_gate = g.mask & (np.abs(yy - cfg.y_axis_mm) < 2) & (np.abs(xx - cfg.axis_x_mm) < 2)
    assert ft[far_corner].mean() > ft[near_gate].mean()


# ---------------------------------------------------------- validation


@pytest.mark.parametrize(
    "overrides",
    [
        dict(fan_w_mm=400.0),  # wider than the plate
        dict(fan_w_mm=10.0),  # inverted trapezoid
        dict(tab_flat_len_mm=12.0),  # longer than the land
        dict(frame_w_mm=100.0),  # frames overlap
        dict(slug_d_mm=30.0),  # slug wider than the well
        dict(sprue_bottom_d_mm=30.0),
        dict(fan_thk_well_mm=0.0),
        dict(inner_thk_mm=-1.0),
        dict(cell_size_mm=25.0),  # coarser than the well
        dict(cell_size_mm=520.0),  # whole cavity rasterised away
    ],
)
def test_validation_rejects_bad_configs(overrides) -> None:
    with pytest.raises(ValueError):
        build_fan_gate_plate_geometry(_cfg(**overrides))


# ------------------------------------------------- gate type × tab toggle


@pytest.mark.parametrize("gate_type", ["fan", "old"])
@pytest.mark.parametrize("tab_on", [True, False])
def test_every_gate_tab_combination_builds_with_the_same_axis_and_gate_end(
    gate_type, tab_on
) -> None:
    cfg = _cfg(gate_type=gate_type, tab_on=tab_on)
    g = build_fan_gate_plate_geometry(cfg)
    assert g.gates and g.volume_cm3() > 0
    # the gate keeps its shape: axis → gate end is gate_len regardless of the tab
    assert cfg.y_gate_end_mm - cfg.y_axis_mm == pytest.approx(cfg.gate_len_mm)
    # the product edge is at gate end + tab (tab off: the product sits on the gate end)
    x0, y0 = g.display_origin_mm()
    assert y0 == pytest.approx(cfg.y_gate_end_mm + (cfg.tab_len_mm if tab_on else 0.0))
    yy, xx = _grid_mm(g)
    # the compression zone is exactly what lies above the gate end
    cm = g.compression_mask
    above = g.mask & (yy > cfg.y_gate_end_mm)
    assert np.array_equal(cm, above)
    below = g.mask & (yy < cfg.y_gate_end_mm)
    assert below.any() and not cm[below].any()
    # product volume is independent of the gate/tab choice
    inner_w = cfg.plate_w_mm - 2 * cfg.frame_w_mm
    inner_h = cfg.plate_h_mm - 2 * cfg.frame_w_mm
    frame_area = cfg.plate_w_mm * cfg.plate_h_mm - inner_w * inner_h
    expected = (frame_area * cfg.frame_thk_mm + inner_w * inner_h * cfg.inner_thk_mm) / 1000.0
    got = float(g.thickness_mm[g.product_mask].sum()) * g.cell_size_mm**2 / 1000.0
    assert got == pytest.approx(expected, rel=1e-6)


def test_without_the_tab_the_product_edge_sits_on_the_gate_end() -> None:
    cfg = _cfg(tab_on=False)
    g = build_fan_gate_plate_geometry(cfg)
    yy, xx = _grid_mm(g)
    assert cfg.y_edge_mm == pytest.approx(cfg.y_gate_end_mm)
    # no tab cells: the compression mask equals the product mask
    assert np.array_equal(g.compression_mask, g.product_mask)
    # the fan's last row meets the frame directly (2.0 → 1.0 step, no ramp)
    on_axis = np.abs(xx - cfg.axis_x_mm) < 1
    last_fan = on_axis & (yy > cfg.y_gate_end_mm - 1) & (yy < cfg.y_gate_end_mm)
    first_plate = on_axis & (yy > cfg.y_edge_mm) & (yy < cfg.y_edge_mm + 1)
    assert np.all(g.thickness_mm[last_fan] == cfg.fan_thk_mm)
    assert np.all(g.thickness_mm[first_plate] == cfg.frame_thk_mm)
    # the grid is shorter by the tab length
    g_tab = build_fan_gate_plate_geometry(_cfg(tab_on=True))
    assert g_tab.mask.shape[0] - g.mask.shape[0] == round(cfg.tab_len_mm / cfg.cell_size_mm)
    assert g_tab.volume_cm3() > g.volume_cm3()


def test_old_gate_is_a_rectangle_with_a_full_well_disc_and_a_ramp_at_the_end() -> None:
    cfg = _cfg(gate_type="old")
    g = build_fan_gate_plate_geometry(cfg)
    assert g.label == "old_gate_plate"
    yy, xx = _grid_mm(g)
    ax = np.abs(xx - cfg.axis_x_mm)
    # silhouette: rectangle old_gate_w wide from the axis line to the gate end
    body_rows = (yy > cfg.y_axis_mm + cfg.well_d_mm / 2 + 1) & (yy < cfg.y_gate_end_mm - 1)
    for y_row in np.unique(yy[body_rows])[::5]:
        xs = xx[(yy == y_row) & g.mask]
        assert xs.max() - xs.min() + g.cell_size_mm == pytest.approx(
            cfg.old_gate_w_mm, abs=2 * g.cell_size_mm
        )
    # nothing outside the rectangle below the gate end except the well disc
    r = np.hypot(xx - cfg.axis_x_mm, yy - cfg.y_axis_mm)
    stray = (
        g.mask
        & (yy < cfg.y_gate_end_mm)
        & (ax > cfg.old_gate_w_mm / 2 + 1)
        & (r > cfg.well_d_mm / 2)
    )
    assert not stray.any()
    # the well disc is complete (its upper half is inside the body anyway)
    assert np.all(g.mask[r <= cfg.well_d_mm / 2 - 1])
    # thickness: old_gate_thk from the well up to the ramp start, then linear to old_gate_end_thk
    on_axis = ax < 1
    y_ramp_start = cfg.y_gate_end_mm - cfg.old_gate_ramp_len_mm
    flat = on_axis & (yy > cfg.y_axis_mm + cfg.well_d_mm / 2 + 1) & (yy < y_ramp_start - 1)
    ramp = on_axis & (yy > y_ramp_start + 1) & (yy < cfg.y_gate_end_mm)
    assert flat.any() and ramp.any()
    assert np.all(g.thickness_mm[flat] == cfg.old_gate_thk_mm)
    h = g.thickness_mm[ramp]
    assert h.max() < cfg.old_gate_thk_mm and h.min() > cfg.old_gate_end_thk_mm - 1e-9
    order = np.argsort(yy[ramp])
    assert np.all(np.diff(h[order]) <= 1e-9)  # thinner toward the tab
    # the well is not a pocket here (4.0 > well_depth 3.0): the ring stays at gate thickness
    well_ring = g.mask & (r >= cfg.slug_d_mm / 2 + 0.5) & (r <= cfg.well_d_mm / 2 - 0.5)
    assert np.all(g.thickness_mm[well_ring] == cfg.old_gate_thk_mm)
    slug = g.mask & (r <= cfg.slug_d_mm / 2 - 0.5)
    assert np.all(g.thickness_mm[slug] == cfg.well_depth_mm + cfg.slug_depth_mm)
    # the tab connects at old_gate_end_thk (= tab_end_thk by default): continuous
    first_tab = on_axis & (yy > cfg.y_gate_end_mm) & (yy < cfg.y_gate_end_mm + 1)
    assert np.all(np.abs(g.thickness_mm[first_tab] - cfg.tab_end_thk_mm) < 0.2)


def test_old_gate_shallow_well_becomes_a_pocket_when_deeper_than_the_gate() -> None:
    cfg = _cfg(gate_type="old", old_gate_thk_mm=2.0, well_depth_mm=3.0)
    g = build_fan_gate_plate_geometry(cfg)
    yy, xx = _grid_mm(g)
    r = np.hypot(xx - cfg.axis_x_mm, yy - cfg.y_axis_mm)
    well_ring = g.mask & (r >= cfg.slug_d_mm / 2 + 0.5) & (r <= cfg.well_d_mm / 2 - 0.5)
    assert np.all(g.thickness_mm[well_ring] == cfg.well_depth_mm)


def test_old_gate_fills_from_the_sprue_outward_too() -> None:
    cfg = _cfg(gate_type="old", cell_size_mm=2.0)
    g = build_fan_gate_plate_geometry(cfg)
    r = HeleShawSolver(
        geometry=g, material=MaterialDB()["PP"], injection_volume_flow_cm3s=50.0
    ).solve(num_frames=4)
    ft = r.fill_time_s
    assert np.isfinite(ft[g.mask]).all()
    yy, xx = _grid_mm(g)
    far_corner = g.mask & (yy > cfg.y_plate_top_mm - 3) & (xx < cfg.pad_mm + 3)
    near_gate = g.mask & (np.abs(yy - cfg.y_axis_mm) < 2) & (np.abs(xx - cfg.axis_x_mm) < 2)
    assert ft[far_corner].mean() > ft[near_gate].mean()


@pytest.mark.parametrize(
    "overrides",
    [
        dict(gate_type="film"),
        dict(gate_type="old", old_gate_ramp_len_mm=50.0),  # ramp longer than the gate
        dict(
            gate_type="old", old_gate_ramp_len_mm=31.0
        ),  # ramp starts inside the well disc (40 - 31 < 10)
        dict(
            gate_type="old", gate_len_mm=8.0, old_gate_ramp_len_mm=0.0
        ),  # disc top beyond the gate end
        dict(gate_type="old", old_gate_w_mm=400.0),  # wider than the plate
        dict(gate_type="old", old_gate_thk_mm=0.0),
        dict(gate_type="old", old_gate_ramp_len_mm=-1.0),
    ],
)
def test_validation_rejects_bad_gate_configs(overrides) -> None:
    with pytest.raises(ValueError):
        build_fan_gate_plate_geometry(_cfg(**overrides))


def test_old_gate_limits_are_not_enforced_on_the_fan_gate() -> None:
    # the fan-gate defaults with a tiny gate_len (shorter than the old-gate ramp) must build
    g = build_fan_gate_plate_geometry(_cfg(gate_type="fan", gate_len_mm=8.0))
    assert g.mask.any()


def test_fan_limits_are_not_enforced_on_the_old_gate() -> None:
    """Codex P1 on PR #7: the UI hides fan_w_mm (250) under the old gate, so a
    plate narrower than the fan must still build there."""
    cfg = _cfg(gate_type="old", plate_w_mm=120.0, plate_h_mm=80.0)
    assert cfg.fan_w_mm > cfg.plate_w_mm
    g = build_fan_gate_plate_geometry(cfg)
    assert g.mask.any() and g.gates
    with pytest.raises(ValueError):
        build_fan_gate_plate_geometry(_cfg(gate_type="fan", plate_w_mm=120.0, plate_h_mm=80.0))


def test_old_gate_ramp_may_start_exactly_at_the_well_top() -> None:
    """Codex P2 on PR #7: the boundary case gate_len = ramp + well radius is legal
    and keeps the whole well at old_gate_thk."""
    cfg = _cfg(gate_type="old", gate_len_mm=25.0, old_gate_ramp_len_mm=15.0)
    g = build_fan_gate_plate_geometry(cfg)
    yy, xx = _grid_mm(g)
    r = np.hypot(xx - cfg.axis_x_mm, yy - cfg.y_axis_mm)
    well_ring = g.mask & (r >= cfg.slug_d_mm / 2 + 0.5) & (r <= cfg.well_d_mm / 2 - 0.5)
    assert np.all(g.thickness_mm[well_ring] == cfg.old_gate_thk_mm)
    assert not g.compression_mask[r <= cfg.well_d_mm / 2 - 0.5].any()


# ------------------------------------------------------------ balancer


def _balancer_cells(cfg, g):
    """Analytic ▽ membership on the cell centres: base on the gate end line,
    apex ``balancer_h`` toward the sprue, half-width linear apex → base."""
    yy, xx = _grid_mm(g)
    y_apex = cfg.y_gate_end_mm - cfg.balancer_h_mm
    t = np.clip((yy - y_apex) / cfg.balancer_h_mm, 0.0, 1.0)
    inside = (
        (yy >= y_apex)
        & (yy <= cfg.y_gate_end_mm)
        & (np.abs(xx - cfg.axis_x_mm) <= 0.5 * cfg.balancer_w_mm * t)
    )
    return inside & g.mask


def test_balancer_is_off_by_default_and_leaves_the_geometry_unchanged() -> None:
    base = build_fan_gate_plate_geometry(_cfg())
    off = build_fan_gate_plate_geometry(_cfg(balancer_on=False, balancer_thk_mm=0.1))
    assert np.array_equal(base.thickness_mm, off.thickness_mm)
    assert np.array_equal(base.mask, off.mask)


@pytest.mark.parametrize("gate_type,w", [("fan", 100.0), ("old", 30.0)])
def test_balancer_is_an_inverted_triangle_with_its_base_on_the_gate_end(gate_type, w) -> None:
    cfg = _cfg(gate_type=gate_type, balancer_on=True, balancer_w_mm=w, balancer_h_mm=20.0)
    g = build_fan_gate_plate_geometry(cfg)
    g0 = build_fan_gate_plate_geometry(_cfg(gate_type=gate_type))
    yy, xx = _grid_mm(g)
    ax = np.abs(xx - cfg.axis_x_mm)
    inside = _balancer_cells(cfg, g)
    assert inside.any()
    assert np.all(g.thickness_mm[inside] == cfg.balancer_thk_mm)
    # everything else is untouched (mask included)
    assert np.array_equal(g.mask, g0.mask)
    assert np.array_equal(g.thickness_mm[~inside], g0.thickness_mm[~inside])
    # base row: the last gate row is thinned over the full base width and
    # the first tab row above it is not (the triangle touches the land)
    dx = g.cell_size_mm
    last_gate = g.mask & (yy > cfg.y_gate_end_mm - dx) & (yy < cfg.y_gate_end_mm)
    first_tab = g.mask & (yy > cfg.y_gate_end_mm) & (yy < cfg.y_gate_end_mm + dx)
    assert np.all(g.thickness_mm[last_gate & (ax < w / 2 - dx)] == cfg.balancer_thk_mm)
    assert np.all(g.thickness_mm[last_gate & (ax > w / 2 + dx)] != cfg.balancer_thk_mm)
    assert np.all(g.thickness_mm[first_tab] == g0.thickness_mm[first_tab])
    # apex: on the axis the thinning stops at gate end − h; below it the gate is intact
    y_apex = cfg.y_gate_end_mm - cfg.balancer_h_mm
    on_axis = ax < dx
    assert np.all(
        g.thickness_mm[g.mask & on_axis & (yy > y_apex + dx) & (yy < cfg.y_gate_end_mm)]
        == cfg.balancer_thk_mm
    )
    below = g.mask & on_axis & (yy < y_apex - dx) & (yy > cfg.y_axis_mm + cfg.well_d_mm / 2 + dx)
    assert below.any() and np.all(g.thickness_mm[below] == g0.thickness_mm[below])
    # centred: the thinned cells' x-offsets from the axis are a set closed under negation
    off = np.sort(xx[inside] - cfg.axis_x_mm)
    assert np.allclose(off, -off[::-1])
    # volume drops by (area × Δt); area ≈ w·h/2
    removed = (g0.volume_cm3() - g.volume_cm3()) * 1000.0
    d_thk = g0.thickness_mm[inside] - cfg.balancer_thk_mm
    assert removed == pytest.approx(float(d_thk.sum()) * dx**2, rel=1e-9)
    assert removed == pytest.approx(0.5 * w * cfg.balancer_h_mm * d_thk.mean(), rel=0.05)


def test_balancer_is_not_compressed_and_does_not_reach_the_well() -> None:
    cfg = _cfg(balancer_on=True, balancer_h_mm=30.0)
    assert cfg.balancer_h_mm == cfg.gate_len_mm - cfg.well_d_mm / 2  # the legal maximum
    g = build_fan_gate_plate_geometry(cfg)
    inside = _balancer_cells(cfg, g)
    assert not g.compression_mask[inside].any()
    yy, xx = _grid_mm(g)
    r = np.hypot(xx - cfg.axis_x_mm, yy - cfg.y_axis_mm)
    well = g.mask & (r <= cfg.well_d_mm / 2 - 0.5)
    assert not inside[well].any()
    assert np.all(g.thickness_mm[well] >= cfg.well_depth_mm)


def test_balancer_wider_than_the_fan_row_is_clipped_to_the_gate_body() -> None:
    # a tall triangle whose base equals the fan width: near the apex the fan
    # is narrower than the trapezoid rows would need, so the ▽ loses corners
    cfg = _cfg(balancer_on=True, balancer_w_mm=250.0, balancer_h_mm=30.0)
    g = build_fan_gate_plate_geometry(cfg)
    g0 = build_fan_gate_plate_geometry(_cfg())
    assert np.array_equal(g.mask, g0.mask)
    thin = g.thickness_mm == cfg.balancer_thk_mm
    assert thin.any() and np.all(g.mask[thin])


def test_balancer_solves() -> None:
    cfg = _cfg(balancer_on=True, cell_size_mm=2.0)
    g = build_fan_gate_plate_geometry(cfg)
    r = HeleShawSolver(
        geometry=g, material=MaterialDB()["PP"], injection_volume_flow_cm3s=50.0
    ).solve(num_frames=4)
    assert np.isfinite(r.fill_time_s[g.mask]).all()


@pytest.mark.parametrize(
    "overrides",
    [
        dict(balancer_on=True, balancer_w_mm=260.0),  # wider than the fan
        dict(balancer_on=True, gate_type="old", balancer_w_mm=31.0),  # wider than the old gate
        dict(balancer_on=True, balancer_h_mm=31.0),  # apex inside the well (40 − 10 = 30)
        dict(balancer_on=True, balancer_thk_mm=0.0),
        dict(balancer_on=True, balancer_thk_mm=2.0),  # = fan thickness: no cut anywhere
        dict(balancer_on=True, balancer_thk_mm=10.0),  # thicker than the fan (Codex P1 on PR #9)
        dict(gate_type="old", balancer_on=True, balancer_w_mm=30.0, old_gate_end_thk_mm=0.5),
        dict(balancer_on=True, balancer_w_mm=0.0),
        dict(balancer_on=True, balancer_h_mm=-1.0),
    ],
)
def test_validation_rejects_bad_balancer_configs(overrides) -> None:
    with pytest.raises(ValueError):
        build_fan_gate_plate_geometry(_cfg(**overrides))


def test_balancer_only_needs_to_cut_at_its_base() -> None:
    # a taper thinner than the balancer upstream is fine: the base still cuts
    g = build_fan_gate_plate_geometry(_cfg(balancer_on=True, fan_thk_well_mm=0.8))
    assert g.mask.any()


def test_balancer_limits_are_ignored_while_it_is_off() -> None:
    g = build_fan_gate_plate_geometry(
        _cfg(balancer_on=False, balancer_w_mm=999.0, balancer_h_mm=999.0)
    )
    assert g.mask.any()


def test_balancer_never_adds_material_where_the_gate_is_already_thinner() -> None:
    """Codex P1 on PR #9: the balancer is a cut. Where the tapered fan is
    already below ``balancer_thk`` the gate thickness must stay, not grow."""
    cfg = _cfg(
        balancer_on=True,
        balancer_thk_mm=1.5,
        balancer_h_mm=30.0,
        fan_thk_well_mm=1.0,
        fan_thk_mm=2.0,
    )
    assert cfg.gate_end_thk_mm == 2.0
    g = build_fan_gate_plate_geometry(cfg)
    g0 = build_fan_gate_plate_geometry(_cfg(fan_thk_well_mm=1.0, fan_thk_mm=2.0))
    inside = _balancer_cells(cfg, g)
    assert inside.any()
    assert np.all(g.thickness_mm[inside] <= g0.thickness_mm[inside] + 1e-12)
    assert np.all(g.thickness_mm[inside] <= cfg.balancer_thk_mm + 1e-12)
    # near the base (fan at 2.0) it cuts to 1.5; near the apex the taper is
    # below 1.5 already and is left alone
    assert (g.thickness_mm[inside] == cfg.balancer_thk_mm).any()
    assert (g.thickness_mm[inside] < cfg.balancer_thk_mm).any()
    assert g.volume_cm3() < g0.volume_cm3()
