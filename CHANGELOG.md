# 変更履歴

[Keep a Changelog](https://keepachangelog.com/ja/1.1.0/) 準拠、[セマンティック バージョニング](https://semver.org/lang/ja/) に従う。
`0.x` 系のため、マイナー版の更新に後方非互換の変更を含むことがある。

## [0.1.0] — 2026-08-27

mold-flow-sim aa96e6c (v0.37.0) から形状非依存モジュールを移植した初期版。

### 追加

- `core/`: `solver`, `materials`, `visualizer`, `visualizer_3d`, `multilayer_solver`, `multilayer_thermal`,
  `two_phase`, `fill_player`, `settings_record`, `version` を sim からそのまま移植。
  `geometry` は `Geometry` dataclass と `build_demo_geometry` のみ
- `core/data/materials.json`（sim は `data/` 直下だったが、wheel に同梱されないのでパッケージ内へ移動）
- 形状非依存テスト一式（sim の `FilmGateConfig` フィクスチャは `build_demo_geometry` に置換）
