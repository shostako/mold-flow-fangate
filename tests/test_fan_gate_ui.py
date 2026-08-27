"""AppTest wiring for the fan-gate geometry sidebar in ``app.py``."""

from __future__ import annotations

import dataclasses

from core import FanGatePlateConfig
from tests.ui_helpers import app as _app
from tests.ui_helpers import texts as _texts


def test_the_defaults_are_the_spec_mold_and_are_recorded_in_full():
    at = _app(fast=False)
    assert not at.exception
    at.checkbox(key="two_phase_on").set_value(False)
    at.slider(key="fg_cell_size_mm").set_value(4.0).run()
    at.button[0].click().run()
    assert not at.exception
    rec = at.session_state["mfs_settings"]["geometry"]
    assert rec["input"] == "Fan gate plate (parametric)"
    expected = dataclasses.asdict(FanGatePlateConfig(cell_size_mm=4.0))
    assert rec["config"] == expected
    geom = at.session_state["mfs_geom"]
    assert geom.label == "fan_gate_plate"
    assert geom.product_mask is not None and geom.compression_mask is not None


def test_the_preview_reports_the_product_volume_separately():
    at = _app()
    assert "うち製品" in _texts(at) or any("うち製品" in str(m.value) for m in at.markdown)


def test_the_taper_toggle_adds_the_well_side_thickness_and_changes_the_volume():
    at = _app()
    # the auto shot-volume bookkeeping only runs while two-phase is on, so
    # keep the default (on) and read the tracked cavity volume from it
    v_uniform = at.session_state["mfs_shot_volume_auto"]
    assert at.checkbox(key="fg_taper_on").value is False
    at.checkbox(key="fg_taper_on").set_value(True).run()
    at.number_input(key="fg_fan_thk_well_mm").set_value(4.0).run()
    assert at.session_state["mfs_shot_volume_auto"] > v_uniform
    at.button[0].click().run()
    assert not at.exception
    assert at.session_state["mfs_settings"]["geometry"]["config"]["fan_thk_well_mm"] == 4.0


def test_a_bad_parameter_is_an_error_message_not_a_crash():
    at = _app()
    # frames overlap: 2 * frame_w >= plate_h
    at.number_input(key="fg_frame_w_mm").set_value(95.0).run()
    assert not at.exception
    assert "形状パラメータが不正" in _texts(at)
    assert "mfs_geom" not in at.session_state
