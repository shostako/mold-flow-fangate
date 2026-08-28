"""Thickness maps of the four gate/tab variants with the ▽ balancer on
(``docs/balancer_thickness.png``). Run from the repo root."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from core import FanGatePlateConfig, build_fan_gate_plate_geometry

fig, axes = plt.subplots(2, 2, figsize=(14, 7), constrained_layout=True)
cases = [("fan", True), ("fan", False), ("old", True), ("old", False)]
for ax, (gt, tab) in zip(axes.flat, cases, strict=True):
    cfg = FanGatePlateConfig(
        gate_type=gt, tab_on=tab, balancer_on=True, balancer_w_mm=100.0 if gt == "fan" else 30.0
    )
    g = build_fan_gate_plate_geometry(cfg)
    x0, y0 = g.display_origin_mm()
    ny, nx = g.mask.shape
    dx = g.cell_size_mm
    ext = [-x0, nx * dx - x0, -y0, ny * dx - y0]
    im = ax.imshow(
        np.where(g.mask, g.thickness_mm, np.nan),
        origin="lower",
        extent=ext,
        cmap="viridis",
        vmin=0,
        vmax=8,
    )
    ax.set_xlim(-160, 160)
    ax.set_ylim(-60, 40)
    ax.set_aspect("equal")
    ax.axhline(0, color="w", lw=0.5, ls="--")
    ax.set_title(
        f"{gt} / tab {'on' if tab else 'off'} / balancer w={cfg.balancer_w_mm:g} "
        f"h={cfg.balancer_h_mm:g} t={cfg.balancer_thk_mm:g}   V={g.volume_cm3():.1f} cm³",
        fontsize=10,
    )
fig.colorbar(im, ax=axes, label="thickness [mm]", shrink=0.8)
fig.savefig("docs/balancer_thickness.png", dpi=110)
