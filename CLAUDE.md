# mold-flow-fangate

額縁肉厚プレート（外周 t=1 / 内側 t=4）＋ファンゲート＋スプルー直結の射出成形流動解析。
[mold-flow-sim](../mold-flow-sim) aa96e6c (v0.37.0) を起点に、**別リポ**として立ち上げた（sim 側は触らない）。

## 現状（2026-08-27）
- 形状仕様は `docs/spec.md`、図は `docs/draft/geometry_draft.png`
- sim の形状非依存モジュールは `core/` に移植済み（v0.1.0）。`geometry.py` は `Geometry` dataclass と
  `build_demo_geometry` のみ
- ファンゲート builder は `core/fan_gate.py`（`FanGatePlateConfig` / `build_fan_gate_plate_geometry`、v0.2.0）。
  既定値が spec の実機。圧縮マスク＝製品＋ランド帯、`Geometry.product_mask`（製品のみ）が表示原点を決める
- sim の `FilmGateConfig` 依存テスト（two_phase / compression_stroke / settings_record）は新 builder で書き直し済み（v0.2.1）
- Streamlit UI `app.py`（v0.3.0）: sim の app.py からソルバ設定とメインパネルを持ち込み、形状入力だけ差し替え。
  形状ウィジェットは `fg_<field>` キー。UI テストは `tests/ui_helpers.py` の `app(fast=True)`（4 mm セル）で回す
- 次の候補: Streamlit Cloud デプロイ、ファンの多段テーパー（profile_gate 流用）、Issue #2
- 環境: `uv venv --python 3.12 .venv && uv pip install -e ".[dev]"`。テストは `MPLBACKEND=Agg .venv/bin/pytest`

## sim から持ち込まなかったもの
LGP 専用の builder（FilmGate/FilmGate2/DirectGate）、`profile_gate.py`, `spec_source.py`, `app.py`, `run_demo.py`,
`data/gate_profiles/`。テストでは sim 固有の `test_geometry_*` と `test_*_ui` を持ち込まず、`test_multilayer_solver` /
`test_visualizer_layer` はフィクスチャを `build_demo_geometry` に置換、`test_visualizer_3d` は DirectGate の段付きプレート1本を
削った。`test_two_phase` / `test_compression_stroke` / `test_settings_record` は `FanGatePlateConfig` で書き直した。

## builder の設計メモ
- 座標は sim と同じ格子系（ゲートブロックが下、製品が上、y は上向き）。表示は `display_origin_mm()` で製品エッジ y=0 に変換
- Hele-Shaw に縦チャネルは無いので、スプルーは足の φ6 ディスクを Dirichlet 射出点として表す。`sprue_len_mm` / `sprue_top_d_mm` は
  将来のノズル圧損用に config に持つだけ
- 井戸 φ20 は深さ 3 のポケット（ファン 2.0 と重なる所は max）、コールドスラッグ φ6 は井戸底からさらに 5（厚み 8）
- ランド帯は製品全幅、ファンは長辺 250 でランドの 2.0 端に接続。ランド帯外側はランドを横に流れる

## 運用
- feature branch + PR + CI green + マージ前レビュー。マージは明示確認を取る
- push 前に `ruff check . && ruff format --check . && pytest`
- 作業ログは `logs/yyyy-MM.md`
