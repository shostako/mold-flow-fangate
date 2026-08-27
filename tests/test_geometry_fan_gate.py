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
    flat = on_axis & (yy > cfg.y_edge_mm - cfg.land_flat_len_mm) & (yy < cfg.y_edge_mm)
    ramp = on_axis & (yy > cfg.y_fan_end_mm) & (yy < cfg.y_edge_mm - cfg.land_flat_len_mm)
    assert flat.any() and ramp.any()
    assert np.all(g.thickness_mm[flat] == cfg.land_flat_thk_mm)
    h_ramp = g.thickness_mm[ramp]
    assert h_ramp.min() > cfg.land_flat_thk_mm
    assert h_ramp.max() < cfg.land_end_thk_mm + 1e-9
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
    fan_row = (yy > cfg.y_fan_end_mm - g.cell_size_mm) & (yy < cfg.y_fan_end_mm)
    y_row = float(yy[fan_row][0])
    t = (y_row - cfg.y_axis_mm) / cfg.fan_len_mm
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
        & (yy < cfg.y_fan_end_mm)
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
    land = g.mask & (yy > cfg.y_fan_end_mm) & (yy < cfg.y_edge_mm)
    assert land.any() and np.all(cm[land])
    gate_block = g.mask & (yy < cfg.y_fan_end_mm)
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
    assert y0_cm == pytest.approx(cfg.y_fan_end_mm)


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
    land = g.mask & (yy > cfg.y_fan_end_mm) & (yy < cfg.y_edge_mm)
    gate_block = g.mask & (yy < cfg.y_fan_end_mm)
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
        dict(land_flat_len_mm=12.0),  # longer than the land
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
