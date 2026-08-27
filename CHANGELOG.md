# 変更履歴

[Keep a Changelog](https://keepachangelog.com/ja/1.1.0/) 準拠、[セマンティック バージョニング](https://semver.org/lang/ja/) に従う。
`0.x` 系のため、マイナー版の更新に後方非互換の変更を含むことがある。

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
