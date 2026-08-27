# 変更履歴

[Keep a Changelog](https://keepachangelog.com/ja/1.1.0/) 準拠、[セマンティック バージョニング](https://semver.org/lang/ja/) に従う。
`0.x` 系のため、マイナー版の更新に後方非互換の変更を含むことがある。

## [0.4.0] — 2026-08-27

**ゲート形状（ファン／旧ゲート）× タブ有無 の 4 通り。** 実機ヒアリングの再訂正: スプルー軸→ゲート端は 40（圧縮部の境界）、
タブ 10 を足して製品エッジまで 50。以前の「ランド端起点 50／製品エッジから 60」は聞き違い。

### 追加

- `FanGatePlateConfig.gate_type`（`"fan"` / `"old"`）と `tab_on`。旧ゲートは幅 30 の矩形＋井戸全円、井戸側 t=4.0、
  ゲート端手前 15 mm で 4.0→2.0 の傾斜（`old_gate_*_mm`）。タブなしは製品エッジがゲート端に来る（ゲート形状は不変）。
  `label` は `fan_gate_plate` / `old_gate_plate`
- `app.py`: ゲート形状のラジオ、タブありチェック。選ばれていない側のウィジェットは出さず既定値を記録に残す
- `docs/gate_variants_thickness.png`（4 通りの厚みマップ）。`docs/fan_gate_thickness.png` は削除
- Streamlit Community Cloud にデプロイ: <https://mold-flow-fangate.streamlit.app>（`requirements.txt` / `runtime.txt`、#8）
- テスト: 4 通りの圧縮マスク＝ゲート端より上、製品体積不変、タブなしの直付け、旧ゲートの輪郭と傾斜、旧ゲートのバリデーション、
  UI のラジオ／チェックの疎通
- バリデーションは選んだゲート形状の分だけ効く（Codex P1: 旧ゲートで製品幅 < 250 が隠れた `fan_w_mm` に弾かれていた）。
  旧ゲートは `gate_len_mm ≥ old_gate_ramp_len_mm + well_d_mm / 2`（Codex P2: 傾斜が井戸円に食い込む／円がゲート端を越える）、
  `cell_size_mm ≤ old_gate_w_mm`（Codex P2: メッシュより細い矩形が消えて井戸が孤立）

### 変更（後方非互換）

- 命名を実機に合わせて `land_*` → `tab_*`、`fan_len_mm` → `gate_len_mm`（既定 50 → 40）、`y_fan_end_mm` → `y_gate_end_mm`。
  `tab_len_eff_mm` を追加

## [0.3.1] — 2026-08-27

### 修正

- 実機ヒアリングの訂正: ランド帯の平面部は t=1.0（額縁と同厚）、傾斜は 1.0→2.0、ファンゲートは t=2.0 均一。
  `FanGatePlateConfig` の既定値（`land_flat_thk_mm` / `land_end_thk_mm` / `fan_thk_mm`）、`docs/spec.md`、
  `docs/draft/geometry_draft.png`、`docs/fan_gate_thickness.png` を更新

## [0.3.0] — 2026-08-27

**Streamlit UI。** sim の `app.py` からソルバ設定・メインパネル（プレビュー／解析実行／充填プレーヤー／圧力／
ウェルド／壁面冷却／層別／二相ショートショット／3D／ZIP）をそのまま持ち込み、形状入力だけ
`FanGatePlateConfig` のサイドバー（製品／ランド帯／ファンゲート／井戸・スラッグ・スプルー／メッシュ）に置き換えた。

### 追加

- `app.py`: `streamlit run app.py`。既定値は spec の実機、1 mm セルで解析一周 約 60 秒
- プレビューにキャビティ体積と製品体積（`product_mask`）を併記
- 数式説明の圧縮成形の項を「製品＋ランド帯が膨張、ゲートブロックは不変」に更新
- UI テスト: `test_fan_gate_ui`（既定値の記録、製品体積表示、テーパー切替、形状エラー）、sim から `test_two_phase_ui` /
  `test_weld_ui` を移植。`tests/ui_helpers.py` の `app(fast=True)` で 4 mm セル・12 フレームに落として高速化
- 入力が前回の解析から変わると結果ペイン先頭に警告（結果は比較用に残す）。解析実行ごとに前回の出力ディレクトリを削除

### 変更

- Streamlit の下限を 1.36 に（`st.columns(vertical_alignment=)`）

## [0.2.1] — 2026-08-27

### テスト

- sim で `FilmGateConfig` に依存していた `test_two_phase` / `test_compression_stroke` / `test_settings_record` を
  `FanGatePlateConfig` で書き直して移植（62 本）。段付きプレートは額縁 0.35／内側 0.50 で代替、
  圧縮ゾーン均一のケースは額縁＝内側＝ランド＝0.5 で作る

## [0.2.0] — 2026-08-27

**ファンゲート付き額縁プレートの形状 builder。**

### 追加

- `core/fan_gate.py`: `FanGatePlateConfig`（既定値＝`docs/spec.md` の実機）と `build_fan_gate_plate_geometry`。
  額縁プレート（外周 t=1／内側 t=4）＋全幅ランド帯（平面 0.6 → 傾斜 2.5）＋ファン台形（2.5 均一、
  `fan_thk_well_mm` で井戸側→ランド側の直線テーパー）＋井戸 φ20×3 ＋コールドスラッグ φ6×5。
  射出点はスプルー足 φ6 のディスク（Hele-Shaw に縦チャネルは無い）。
- `Geometry.product_mask`: 圧縮ゾーンと製品が一致しない builder 用。`display_origin_mm()` はこれがあれば
  こちらの下端を y=0 に取る。**圧縮マスクは製品＋ランド帯**（sim の FilmGate は製品のみ）
- `tests/test_geometry_fan_gate.py`: 製品体積の解析値一致、ランド平面/傾斜、井戸・スラッグ深さ、
  圧縮マスク＝製品＋ランド、表示原点＝製品エッジ、ストローク圧縮でランドも膨らむ、ソルバ疎通、バリデーション

## [0.1.0] — 2026-08-27

mold-flow-sim aa96e6c (v0.37.0) から形状非依存モジュールを移植した初期版。

### 追加

- `core/`: `solver`, `materials`, `visualizer`, `visualizer_3d`, `multilayer_solver`, `multilayer_thermal`,
  `two_phase`, `fill_player`, `settings_record`, `version` を sim からそのまま移植。
  `geometry` は `Geometry` dataclass と `build_demo_geometry` のみ
- `core/data/materials.json`（sim は `data/` 直下だったが、wheel に同梱されないのでパッケージ内へ移動）
- 形状非依存テスト一式（sim の `FilmGateConfig` フィクスチャは `build_demo_geometry` に置換）
