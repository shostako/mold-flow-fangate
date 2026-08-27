# mold-flow-fangate

額縁肉厚プレート（外周 t=1 / 内側 t=4）＋ファンゲート＋スプルー直結の射出成形流動解析。
[mold-flow-sim](https://github.com/shostako/mold-flow-sim) aa96e6c (v0.37.0) を起点に別リポとして立ち上げ。

- 形状仕様: `docs/spec.md`、ドラフト図: `docs/draft/geometry_draft.png`（`docs/draft/geometry_draft.py` で再生成）
- `core/`: sim から移植した Hele-Shaw ソルバ／多層熱／二相ショートショット／可視化。ファンゲート用の形状 builder は作業中

## 開発

```
uv venv --python 3.12 .venv && uv pip install -e ".[dev]"
ruff check . && ruff format --check . && MPLBACKEND=Agg .venv/bin/pytest
```
