"""Regenerate ``docs/gate_variants_thickness.png``: thickness maps of every
gate type × tab combination the builder makes, at the current defaults
(well φ23 since the 2026-09 rework).

Run from the repo root:
``MPLBACKEND=Agg .venv/bin/python docs/draft/gate_variants_thickness.py``
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from core.fan_gate import GATE_TYPES, FanGatePlateConfig, build_fan_gate_plate_geometry

OUT = Path(__file__).resolve().parents[1] / "gate_variants_thickness.png"


def main() -> None:
    fig, axes = plt.subplots(2, len(GATE_TYPES), figsize=(6 * len(GATE_TYPES), 10))
    for row, tab_on in enumerate([True, False]):
        for col, gate_type in enumerate(GATE_TYPES):
            cfg = FanGatePlateConfig(gate_type=gate_type, tab_on=tab_on)
            g = build_fan_gate_plate_geometry(cfg)
            thk = np.where(g.mask, g.thickness_mm, np.nan)
            ny, nx = g.mask.shape
            extent = (0.0, nx * cfg.cell_size_mm, 0.0, ny * cfg.cell_size_mm)
            axp = axes[row, col]
            im = axp.imshow(
                thk,
                origin="lower",
                extent=extent,
                cmap="viridis",
                interpolation="nearest",
                vmin=0.0,
                vmax=8.0,
            )
            axp.set_title(
                f"{gate_type} gate, tab {'on' if tab_on else 'off'}  "
                f"({g.volume_cm3():.1f} cm$^3$)"
            )
            axp.set_aspect("equal")
            fig.colorbar(im, ax=axp, shrink=0.75, label="thickness [mm]")
    fig.tight_layout()
    fig.savefig(OUT, dpi=110)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
