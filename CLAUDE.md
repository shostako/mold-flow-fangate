# mold-flow-fangate

額縁肉厚プレート（外周 t=1 / 内側 t=4）＋ファンゲート＋スプルー直結の射出成形流動解析。
[mold-flow-sim](../mold-flow-sim) aa96e6c (v0.37.0) を起点に、**別リポ**として立ち上げた（sim 側は触らない）。

## 現状（2026-08-27）
- 形状仕様は `docs/spec.md`、図は `docs/draft/geometry_draft.png`
- コードはまだ無い。次の作業は sim からの形状非依存モジュール移植

## 移植計画
sim の `core/` から **そのままコピー**: `solver.py`, `materials.py`, `visualizer.py`, `visualizer_3d.py`,
`multilayer_solver.py`, `multilayer_thermal.py`, `two_phase.py`, `fill_player.py`, `settings_record.py`, `version.py`
＋ `data/`。設定類（`pyproject.toml`, `.github/workflows/ci.yml`, `.streamlit/config.toml`）は名前を変えてコピー。

`geometry.py` は **`Geometry` dataclass と `build_demo_geometry` だけ残す**（テストが使う）。
LGP 専用の builder（FilmGate/FilmGate2/DirectGate）と `profile_gate.py`, `spec_source.py`, `app.py`, `run_demo.py` は持ち込まない。
`core/__init__.py` の再エクスポートもそれに合わせて削る。

テストは sim の `tests/` から形状非依存のものを選んで移植: `test_smoke`, `test_solver_1d`, `test_multilayer_*`,
`test_skin_layer`, `test_fill_player`, `test_fill_render`, `test_short_shot_timeline`, `test_weld_detection`,
`test_visualizer_*`, `test_version`。`FilmGateConfig` に依存するもの（`test_two_phase`, `test_compression_stroke`,
`test_settings_record`）は新 builder ができてから書き直す。

新 builder（仮称 `FanGatePlateConfig` / `build_fan_gate_plate_geometry`）は sim の `FilmGateConfig`（半円＋台形＋ランド）と
`profile_gate` の深さプロファイル（平面→傾斜、多段テーパー）を合成して書く。

## 運用
- feature branch + PR + CI green + マージ前レビュー。マージは明示確認を取る
- push 前に `ruff check . && ruff format --check . && pytest`
- 作業ログは `logs/yyyy-MM.md`
