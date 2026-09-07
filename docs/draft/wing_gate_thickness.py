"""Regenerate ``docs/wing_gate_thickness.png``: the wing gate's thickness map
(full plate + gate close-up) with the 2026-09-07 drawing defaults (well φ23).

Run from the repo root: ``MPLBACKEND=Agg .venv/bin/python docs/draft/wing_gate_thickness.py``
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from core.fan_gate import FanGatePlateConfig, build_fan_gate_plate_geometry

OUT = Path(__file__).resolve().parents[1] / "wing_gate_thickness.png"


def main() -> None:
    cfg = FanGatePlateConfig(gate_type="wing", well_d_mm=23.0)
    g = build_fan_gate_plate_geometry(cfg)

    thk = np.where(g.mask, g.thickness_mm, np.nan)
    ny, nx = g.mask.shape
    extent = (0.0, nx * g.cell_size_mm, 0.0, ny * g.cell_size_mm)

    fig, axes = plt.subplots(1, 2, figsize=(15, 7))
    for axp, title, vmax in zip(
        axes, ["full plate", "gate close-up (0-4 mm scale)"], [8.0, 4.0], strict=True
    ):
        im = axp.imshow(
            thk,
            origin="lower",
            extent=extent,
            cmap="viridis",
            interpolation="nearest",
            vmin=0.0,
            vmax=vmax,
        )
        axp.set_title(f"wing gate — {title}")
        axp.set_aspect("equal")
        fig.colorbar(im, ax=axp, shrink=0.8, label="thickness [mm]")

    y_gate_end = cfg.y_gate_end_mm
    axes[1].set_xlim(cfg.axis_x_mm - 125, cfg.axis_x_mm + 125)
    axes[1].set_ylim(0, y_gate_end + 25)
    for y, ls in [
        (y_gate_end, "-"),  # ゲート端（ランド線）
        (y_gate_end - cfg.wing_taper_len_mm, ":"),  # コアのテーパー終端
        (y_gate_end - cfg.wing_depth_mm, "--"),  # 翼下端 = 三角形上辺
        (cfg.y_axis_mm, "-."),  # スプルー軸線
    ]:
        axes[1].axhline(y, color="w", lw=0.6, ls=ls, alpha=0.7)

    fig.tight_layout()
    fig.savefig(OUT, dpi=130)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
