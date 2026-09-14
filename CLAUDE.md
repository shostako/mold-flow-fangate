# mold-flow-fangate

額縁肉厚プレート（外周 t=1 / 内側 t=4）＋ファンゲート＋スプルー直結の射出成形流動解析。
[mold-flow-sim](../mold-flow-sim) aa96e6c (v0.37.0) を起点に、**別リポ**として立ち上げた（sim 側は触らない）。

## 現状（2026-09-08）
- 形状仕様は `docs/spec.md`、図は `docs/draft/geometry_draft.png`
- sim の形状非依存モジュールは `core/` に移植済み（v0.1.0）。`geometry.py` は `Geometry` dataclass と
  `build_demo_geometry` のみ
- builder は `core/fan_gate.py`（`FanGatePlateConfig` / `build_fan_gate_plate_geometry`）。既定値が spec の実機。
  `gate_type`（fan/old/wing）× `tab_on`（v0.4.0、wing は v0.6.0）。圧縮マスク＝製品＋タブ（＝ゲート端より製品側）、
  `Geometry.product_mask`（製品のみ）が表示原点を決める。肉盗み `balancer_*`（v0.5.0）はゲート端に底辺を置く逆三角、
  ゲート本体でクリップして圧縮部には入らない。ウイングゲート `wing_*`（v0.6.0、旧ゲート発展版）は中央コア＋t0.6 両翼
  ランド 220＋t2.0 三角形で、肉盗みとは併用不可（validate が拒否）。旧ゲートは v0.7.0 で井戸へ絞る台形に改修、
  井戸の既定は φ23。`grid_shift_mm` が下側パッドを 1 セル未満伸ばして製品エッジをセルエッジに揃えるので、
  mm 倍数寸法なら既定 1 mm 格子で解析値と厳密一致する（テストの probe バンドは境界に触るとき閉区間＋ `.any()` ガード）
- sim の `FilmGateConfig` 依存テスト（two_phase / compression_stroke / settings_record）は新 builder で書き直し済み（v0.2.1）
- Streamlit UI `app.py`（v0.3.0）: sim の app.py からソルバ設定とメインパネルを持ち込み、形状入力だけ差し替え。
  形状ウィジェットは `fg_<field>` キー。UI テストは `tests/ui_helpers.py` の `app(fast=True)`（4 mm セル）で回す
- 射出条件は**実機のスクリュー設定から**（v0.8.0、sim #88/#89/#90 の横展開）。`core/injection_profile.py` の
  `InjectionProfile` がスクリュー径・計量位置・各段の速度切替位置と速度から体積 → 時刻の区分線形写像を作り、
  `HeleShawSolver.injection_profile` に渡すと体積 CDF 写像がそこを通る（`injection_volume_flow_cm3s` に優先。
  無指定なら従来の定率で既存結果と bit 一致）。段の注入体積は速度によらずストロークだけで決まるので、
  折れ点の体積は固定で傾きだけが段ごとに変わる。**既定は機械の設定（φ50 / V/P 18 / 3 段・全段 200 mm/s）だが、
  計量位置だけ本リポ固有の 140 mm** — 既定形状が 204.7 cm³ あって sim の 30 mm（理論射出量 23.6 cm³）では
  全然足りず、既定画面が常に外挿警告を出すため。キャビティを覆う最小ストロークに 15% の余裕を足して 10 mm 丸めた
  **逆算値**で、実機の設定値ではない。切替位置も sim の 28/22 は別案件のものなので持ち込まずストロークを等分割。
  V/P を越える体積は最終段の射出率で外挿し、理論射出量がキャビティ体積や計量体積を下回るときは警告を出す。
  スキン層の時計の UI 既定も `constant_rate`（速度制御）に変えた（ライブラリ既定は `constant_pressure` のまま）
- `tests/test_injection_ui.py` の期待既定値は先頭の定数ブロック（`DEF_METER` / `DEF_SWITCHES` 等）1 箇所に集約してある。
  sim と共有するファイルなので、値を変えるときは `app.py` の定数と両方を直す
- 次の候補: ゲート形状（＋肉盗み／ウイング）の充填順比較（実機不具合の仮説検証）、肉盗みの多段化（sim は 5 段）、ファンの多段テーパー（profile_gate 流用）、Issue #2
- 環境: `uv venv --python 3.12 .venv && uv pip install -e ".[dev]"`。テストは `MPLBACKEND=Agg .venv/bin/pytest`
- Streamlit Community Cloud: <https://mold-flow-fangate.streamlit.app>（main を自動デプロイ）。`requirements.txt` は pyproject の deps のミラー、
  `runtime.txt` は `python-3.12`。deps を変えたら requirements.txt も同期

## sim から持ち込まなかったもの
LGP 専用の builder（FilmGate/FilmGate2/DirectGate）、`profile_gate.py`, `spec_source.py`, `app.py`, `run_demo.py`,
`data/gate_profiles/`。テストでは sim 固有の `test_geometry_*` と `test_*_ui` を持ち込まず、`test_multilayer_solver` /
`test_visualizer_layer` はフィクスチャを `build_demo_geometry` に置換、`test_visualizer_3d` は DirectGate の段付きプレート1本を
削った。`test_two_phase` / `test_compression_stroke` / `test_settings_record` は `FanGatePlateConfig` で書き直した。

## builder の設計メモ
- 座標は sim と同じ格子系（ゲートブロックが下、製品が上、y は上向き）。表示は `display_origin_mm()` で製品エッジ y=0 に変換
- Hele-Shaw に縦チャネルは無いので、スプルーは足の φ6 ディスクを Dirichlet 射出点として表す。`sprue_len_mm` / `sprue_top_d_mm` は
  将来のノズル圧損用に config に持つだけ
- 井戸 φ23（既定、v0.7.0 で φ20 から変更）は深さ 3 のポケット（ゲート厚と max なので旧ゲート t4.0 ではポケットにならない）、コールドスラッグ φ6 は井戸底からさらに 5（厚み 8）
- スプルー軸→ゲート端 `gate_len_mm`=40 が圧縮部境界。タブ（全幅ランド 10）はその先で `tab_on` で消せる。ゲート形状はタブ有無で不変
- ファンは長辺 250 でゲート端に接続、タブは製品全幅なのでタブ外側はタブを横に流れる。旧ゲートはゲート端幅 30 → 井戸へ絞る台形＋井戸全円（v0.7.0）

## 運用
- feature branch + PR + CI green + マージ前レビュー。マージは明示確認を取る
- push 前に `ruff check . && ruff format --check . && pytest`
- 作業ログは `logs/yyyy-MM.md`
