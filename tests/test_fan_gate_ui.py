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


def test_a_second_run_removes_the_previous_output_directory():
    """Codex P2 on PR #5: every run makes a fresh temp dir; the superseded one
    must go when the new results replace it."""
    from pathlib import Path

    at = _app()
    at.checkbox(key="two_phase_on").set_value(False).run()
    at.button[0].click().run()
    assert not at.exception
    first = Path(at.session_state["mfs_tmp_dir"])
    assert first.is_dir()
    at.button[0].click().run()
    assert not at.exception
    second = Path(at.session_state["mfs_tmp_dir"])
    assert second != first
    assert second.is_dir() and not first.exists()
    assert Path(at.session_state["mfs_gif_path"]).parent == second


def test_changing_an_input_after_a_run_marks_the_result_stale_until_rerun():
    """Codex P1 on PR #5: the result pane must say when the sidebar no longer
    matches the run it shows, and the cached result must stay (no silent
    re-solve)."""
    at = _app()
    at.checkbox(key="two_phase_on").set_value(False).run()
    at.button[0].click().run()
    assert not at.exception
    result = at.session_state["mfs_result"]
    assert "入力が前回の解析から変更されています" not in _texts(at)
    at.number_input(key="fg_inner_thk_mm").set_value(3.0).run()
    assert not at.exception
    assert "入力が前回の解析から変更されています" in _texts(at)
    assert at.session_state["mfs_result"] is result
    # the weld threshold is re-thresholded live, so it must not count as stale
    at.number_input(key="fg_inner_thk_mm").set_value(4.0).run()
    assert "入力が前回の解析から変更されています" not in _texts(at)
    at.slider(key="weld_min_angle").set_value(20).run()
    assert "入力が前回の解析から変更されています" not in _texts(at)
    at.number_input(key="fg_inner_thk_mm").set_value(3.0).run()
    at.button[0].click().run()
    assert not at.exception
    assert "入力が前回の解析から変更されています" not in _texts(at)
    assert at.session_state["mfs_result"] is not result


def test_the_gate_radio_and_tab_toggle_reach_the_builder():
    at = _app()
    assert at.radio(key="fg_gate_label").value == "ファンゲート"
    assert at.checkbox(key="fg_tab_on").value is True
    v_fan_tab = at.session_state["mfs_shot_volume_auto"]
    # old gate: the fan widgets go away, the old-gate widgets appear
    at.radio(key="fg_gate_label").set_value("旧ゲート（タブゲート）").run()
    assert not at.exception
    assert "fg_old_gate_w_mm" in at.session_state
    keys = {n.key for n in at.number_input}
    assert "fg_old_gate_w_mm" in keys and "fg_fan_w_mm" not in keys
    v_old_tab = at.session_state["mfs_shot_volume_auto"]
    assert v_old_tab < v_fan_tab
    # tab off: the tab expander goes away, the cavity shrinks again
    at.checkbox(key="fg_tab_on").set_value(False).run()
    assert not at.exception
    keys = {n.key for n in at.number_input}
    assert "fg_tab_len_mm" not in keys
    assert at.session_state["mfs_shot_volume_auto"] < v_old_tab
    at.button[0].click().run()
    assert not at.exception
    cfg = at.session_state["mfs_settings"]["geometry"]["config"]
    assert cfg["gate_type"] == "old" and cfg["tab_on"] is False
    assert cfg["old_gate_w_mm"] == FanGatePlateConfig().old_gate_w_mm
    assert at.session_state["mfs_geom"].label == "old_gate_plate"


def test_a_narrow_plate_builds_under_the_old_gate_where_the_fan_width_is_hidden():
    """Codex P1 on PR #7: the hidden fan_w_mm default (250) must not veto an
    old-gate plate narrower than that."""
    at = _app()
    at.radio(key="fg_gate_label").set_value("旧ゲート（タブゲート）").run()
    at.number_input(key="fg_plate_w_mm").set_value(120.0).run()
    assert not at.exception
    assert "形状パラメータが不正" not in _texts(at)
    at.checkbox(key="two_phase_on").set_value(False).run()
    at.button[0].click().run()
    assert not at.exception
    assert at.session_state["mfs_settings"]["geometry"]["config"]["plate_w_mm"] == 120.0
