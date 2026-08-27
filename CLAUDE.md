# mold-flow-fangate

額縁肉厚プレート（外周 t=1 / 内側 t=4）＋ファンゲート＋スプルー直結の射出成形流動解析。
[mold-flow-sim](../mold-flow-sim) aa96e6c (v0.37.0) を起点に、**別リポ**として立ち上げた（sim 側は触らない）。

## 現状（2026-08-27）
- 形状仕様は `docs/spec.md`、図は `docs/draft/geometry_draft.png`
- sim の形状非依存モジュールは `core/` に移植済み（v0.1.0）。`geometry.py` は `Geometry` dataclass と
  `build_demo_geometry` のみで、**ファンゲート用 builder はまだ無い**。次の作業はその builder
- 環境: `uv venv --python 3.12 .venv && uv pip install -e ".[dev]"`。テストは `MPLBACKEND=Agg .venv/bin/pytest`

## sim から持ち込まなかったもの
LGP 専用の builder（FilmGate/FilmGate2/DirectGate）、`profile_gate.py`, `spec_source.py`, `app.py`, `run_demo.py`,
`data/gate_profiles/`。テストでは `FilmGateConfig` 依存のもの（`test_two_phase`, `test_compression_stroke`,
`test_settings_record`, `test_geometry_*`, `test_*_ui`）を見送り、`test_multilayer_solver` / `test_visualizer_layer` は
フィクスチャを `build_demo_geometry` に置換、`test_visualizer_3d` は DirectGate の段付きプレート1本を削った。
これらは新 builder ができたら書き直す。

新 builder（仮称 `FanGatePlateConfig` / `build_fan_gate_plate_geometry`）は sim の `FilmGateConfig`（半円＋台形＋ランド）と
`profile_gate` の深さプロファイル（平面→傾斜、多段テーパー）を合成して書く。
**圧縮マスクは製品＋ランド帯 10mm**（sim は製品のみ）。表示原点 y=0 は製品エッジのままにする（`display_origin_mm` の扱いに注意、`docs/spec.md` 参照）。

## 運用
- feature branch + PR + CI green + マージ前レビュー。マージは明示確認を取る
- push 前に `ruff check . && ruff format --check . && pytest`
- 作業ログは `logs/yyyy-MM.md`
