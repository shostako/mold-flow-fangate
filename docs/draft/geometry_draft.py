"""Draft sketch of the fan-gate plate geometry (parameters from 2026-08-27 spec)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, Circle, Wedge
from matplotlib.font_manager import FontProperties

JP = FontProperties(fname="/mnt/c/Windows/Fonts/meiryo.ttc")

# ---- parameters (mm) ----
PW, PH = 315.0, 183.0        # product
FRAME, T_FRAME, T_INNER = 15.0, 1.0, 4.0
GATE_OFF = 50.0              # sprue axis distance from product long edge
D_EXIT = 3.0                 # gate exit dia (?)
WELL_D, WELL_DEPTH = 20.0, 3.0
LAND_W = 250.0               # fan gate width at product edge
SPRUE_L, SPRUE_TOP, SPRUE_BOT = 15.0, 4.0, 6.0
SLUG_DEPTH = 5.0
T_FAN = 1.0                  # fan gate thickness — NOT SPECIFIED (placeholder)

cx = PW / 2
fig, (ax, az) = plt.subplots(2, 1, figsize=(11, 12), gridspec_kw={"height_ratios": [3, 1.6]})

# ================= plan view =================
ax.add_patch(Rectangle((0, 0), PW, PH, fc="#ffe0b2", ec="k", lw=1.5))
ax.add_patch(Rectangle((FRAME, FRAME), PW - 2 * FRAME, PH - 2 * FRAME, fc="#ffb74d", ec="k", lw=1))
fan = [(cx - LAND_W / 2, 0), (cx + LAND_W / 2, 0), (cx + WELL_D / 2, -GATE_OFF), (cx - WELL_D / 2, -GATE_OFF)]
ax.add_patch(Polygon(fan, closed=True, fc="#bbdefb", ec="k", lw=1.2))
ax.add_patch(Wedge((cx, -GATE_OFF), WELL_D / 2, 180, 360, fc="#90caf9", ec="k", lw=1.2))
ax.add_patch(Circle((cx, -GATE_OFF), WELL_D / 2, fill=False, ec="k", ls="--", lw=0.8))
ax.add_patch(Circle((cx, -GATE_OFF), SPRUE_BOT / 2, fc="#ef9a9a", ec="k", lw=1))
ax.add_patch(Circle((cx, -GATE_OFF), D_EXIT / 2, fc="#c62828", ec="k", lw=0.8))

def dim(a, p0, p1, txt, off=0, **kw):
    a.annotate("", p0, p1, arrowprops=dict(arrowstyle="<->", lw=0.8))
    mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
    a.text(mx, my + off, txt, ha="center", va="bottom", fontsize=9, fontproperties=JP, **kw)

dim(ax, (0, PH + 10), (PW, PH + 10), f"{PW:g}")
ax.annotate("", (PW + 10, 0), (PW + 10, PH), arrowprops=dict(arrowstyle="<->", lw=0.8))
ax.text(PW + 14, PH / 2, f"{PH:g}", va="center", fontsize=9, rotation=90)
dim(ax, (cx - LAND_W / 2, 6), (cx + LAND_W / 2, 6), f"ランド幅 {LAND_W:g}")
ax.annotate("", (cx + 40, 0), (cx + 40, -GATE_OFF), arrowprops=dict(arrowstyle="<->", lw=0.8))
ax.text(cx + 43, -GATE_OFF / 2, f"{GATE_OFF:g}", va="center", fontsize=9)
dim(ax, (cx - WELL_D / 2, -GATE_OFF - 16), (cx + WELL_D / 2, -GATE_OFF - 16), f"井戸 φ{WELL_D:g} 深さ{WELL_DEPTH:g}", off=-9)
ax.text(cx + 12, -GATE_OFF + 2, f"スプルー下端 φ{SPRUE_BOT:g}\nゲート出口 φ{D_EXIT:g} (?)", fontsize=8, fontproperties=JP)
ax.text(PW / 2, PH / 2, f"内側 t={T_INNER:g}", ha="center", fontsize=11, fontproperties=JP)
ax.text(PW / 2, PH - FRAME / 2, f"額縁 幅{FRAME:g} t={T_FRAME:g}", ha="center", va="center", fontsize=9, fontproperties=JP)
ax.text(cx - 100, -20, f"ファンゲート t=? (仮 {T_FAN:g})", fontsize=9, fontproperties=JP, color="#1565c0")
ax.text(cx + 3, PH + 3, "A", fontsize=10, fontweight="bold"); ax.text(cx + 3, -75, "A'", fontsize=10, fontweight="bold")
ax.plot([cx, cx], [-75, PH + 8], "k-.", lw=0.6)
ax.set_xlim(-25, PW + 30); ax.set_ylim(-80, PH + 25); ax.set_aspect("equal")
ax.set_title("平面図（可動側から見る、単位 mm）", fontproperties=JP)
ax.set_xlabel("x"); ax.set_ylabel("y")

# ================= section along gate axis (y–z) =================
# z=0 parting line; product/gate cut into moving side (z<0) for the sketch
az.add_patch(Rectangle((0, -T_FRAME), FRAME, T_FRAME, fc="#ffe0b2", ec="k"))
az.add_patch(Rectangle((FRAME, -T_INNER), PH - 2 * FRAME, T_INNER, fc="#ffb74d", ec="k"))
az.add_patch(Rectangle((PH - FRAME, -T_FRAME), FRAME, T_FRAME, fc="#ffe0b2", ec="k"))
az.add_patch(Rectangle((-GATE_OFF, -T_FAN), GATE_OFF, T_FAN, fc="#bbdefb", ec="k"))
az.add_patch(Rectangle((-GATE_OFF - WELL_D / 2, -WELL_DEPTH), WELL_D, WELL_DEPTH, fc="#90caf9", ec="k"))
az.add_patch(Rectangle((-GATE_OFF - SPRUE_BOT / 2, -WELL_DEPTH - SLUG_DEPTH), SPRUE_BOT, SLUG_DEPTH, fc="#e0e0e0", ec="k", hatch="//"))
sprue = [(-GATE_OFF - SPRUE_BOT / 2, 0), (-GATE_OFF + SPRUE_BOT / 2, 0), (-GATE_OFF + SPRUE_TOP / 2, SPRUE_L), (-GATE_OFF - SPRUE_TOP / 2, SPRUE_L)]
az.add_patch(Polygon(sprue, closed=True, fc="#ef9a9a", ec="k"))
az.axhline(0, color="k", lw=0.8, ls="--")
az.text(PH + 2, 0.5, "PL", fontsize=9)
az.text(-GATE_OFF, SPRUE_L + 1.5, f"φ{SPRUE_TOP:g}", ha="center", fontsize=8)
az.text(-GATE_OFF + 5, 1, f"φ{SPRUE_BOT:g}", fontsize=8)
az.text(-GATE_OFF - 25, SPRUE_L / 2, f"スプルーブッシュ L={SPRUE_L:g}", fontsize=8, fontproperties=JP, ha="right")
az.text(-GATE_OFF - 25, -WELL_DEPTH - SLUG_DEPTH / 2, f"コールドスラッグ 深さ{SLUG_DEPTH:g} (?)", fontsize=8, fontproperties=JP, ha="right")
az.text(-GATE_OFF + 12, -WELL_DEPTH - 1.5, f"井戸 深さ{WELL_DEPTH:g}", fontsize=8, fontproperties=JP)
az.text(-25, -T_FAN - 1.5, "ファン t=?", fontsize=8, fontproperties=JP, color="#1565c0")
az.text(FRAME + 3, -T_INNER - 1.5, f"t={T_INNER:g}", fontsize=8)
az.text(2, -T_FRAME - 1.5, f"t={T_FRAME:g}", fontsize=8)
az.set_xlim(-GATE_OFF - 75, PH + 12); az.set_ylim(-12, SPRUE_L + 5)
az.set_aspect(2.0)
az.set_title("A–A' 断面（ゲート軸に沿う y–z、z を2倍に拡大）", fontproperties=JP)
az.set_xlabel("y  (0 = 製品長辺エッジ)", fontproperties=JP); az.set_ylabel("z")

fig.tight_layout()
fig.savefig("docs/draft/geometry_draft.png", dpi=130)
print("ok")
