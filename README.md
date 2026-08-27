# mold-flow-fangate

額縁肉厚プレート（外周 t=1 / 内側 t=4）＋ファンゲート＋スプルー直結の射出成形流動解析。
[mold-flow-sim](https://github.com/shostako/mold-flow-sim) aa96e6c (v0.37.0) を起点に別リポとして立ち上げ。

- 形状仕様: `docs/spec.md`、ドラフト図: `docs/draft/geometry_draft.png`（`docs/draft/geometry_draft.py` で再生成）
- `core/`: sim から移植した Hele-Shaw ソルバ／多層熱／二相ショートショット／可視化、ファンゲート用 builder `core/fan_gate.py`
- `app.py`: Streamlit UI

## 使い方

```
streamlit run app.py
```

左のサイドバーで形状（既定値は spec の実機）・材料・射出条件・圧縮条件を設定して「解析実行」。

## 開発

```
uv venv --python 3.12 .venv && uv pip install -e ".[dev]"
ruff check . && ruff format --check . && MPLBACKEND=Agg .venv/bin/pytest
```
