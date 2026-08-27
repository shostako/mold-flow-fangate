"""Draft sketch of the fan-gate plate geometry (spec as of 2026-08-27, after photo review)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, Circle, Wedge
from matplotlib.font_manager import FontProperties

JP = FontProperties(fname="/mnt/c/Windows/Fonts/meiryo.ttc")

# ---- parameters (mm) ----
PW, PH = 315.0, 183.0        # product
FRAME, T_FRAME, T_INNER = 15.0, 1.0, 4.0
LAND_L = 10.0                # land band length (product edge -> fan)
FAN_L = 50.0                 # sprue axis distance from the land band's 2.5 mm end (= trapezoid length)
GATE_OFF = LAND_L + FAN_L    # sprue axis distance from product long edge (derived)
WELL_D, WELL_DEPTH = 20.0, 3.0
FAN_W = 250.0                # fan width where it joins the land band
LAND_W = PW                  # land band spans the full product long edge (linked to PW)
LAND_FLAT_L, T_LAND_FLAT = 2.0, 0.6   # flat part next to product edge
T_LAND_END = 2.5             # land thickness at fan end (ramp 0.6 -> 2.5 over 2..10 mm)
T_FAN = 2.5                  # fan gate, uniform (toggle: taper / meat-steal like sim)
SPRUE_L, SPRUE_TOP, SPRUE_BOT = 15.0, 4.0, 6.0
SLUG_D, SLUG_DEPTH = 6.0, 5.0  # cold slug: cylinder under sprue axis, below well floor

cx = PW / 2
fig, (ax, az) = plt.subplots(2, 1, figsize=(11, 12), gridspec_kw={"height_ratios": [3, 1.6]})

# ================= plan view =================
ax.add_patch(Rectangle((0, 0), PW, PH, fc="#ffe0b2", ec="k", lw=1.5))
ax.add_patch(Rectangle((FRAME, FRAME), PW - 2 * FRAME, PH - 2 * FRAME, fc="#ffb74d", ec="k", lw=1))
ax.add_patch(Rectangle((cx - LAND_W / 2, -LAND_L), LAND_W, LAND_L, fc="#c8e6c9", ec="k", lw=1))
ax.add_patch(Rectangle((cx - LAND_W / 2, -LAND_FLAT_L), LAND_W, LAND_FLAT_L, fc="#a5d6a7", ec="k", lw=0.5))
fan = [(cx - FAN_W / 2, -LAND_L), (cx + FAN_W / 2, -LAND_L), (cx + WELL_D / 2, -GATE_OFF), (cx - WELL_D / 2, -GATE_OFF)]
ax.add_patch(Polygon(fan, closed=True, fc="#bbdefb", ec="k", lw=1.2))
ax.add_patch(Wedge((cx, -GATE_OFF), WELL_D / 2, 180, 360, fc="#90caf9", ec="k", lw=1.2))
ax.add_patch(Circle((cx, -GATE_OFF), WELL_D / 2, fill=False, ec="k", ls="--", lw=0.8))
ax.add_patch(Circle((cx, -GATE_OFF), SPRUE_BOT / 2, fc="#ef9a9a", ec="k", lw=1))

def dim(a, p0, p1, txt, off=0, **kw):
    a.annotate("", p0, p1, arrowprops=dict(arrowstyle="<->", lw=0.8))
    mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
    a.text(mx, my + off, txt, ha="center", va="bottom", fontsize=9, fontproperties=JP, **kw)

dim(ax, (0, PH + 10), (PW, PH + 10), f"{PW:g}")
ax.annotate("", (PW + 10, 0), (PW + 10, PH), arrowprops=dict(arrowstyle="<->", lw=0.8))
ax.text(PW + 14, PH / 2, f"{PH:g}", va="center", fontsize=9, rotation=90)
dim(ax, (cx - FAN_W / 2, -LAND_L - 1), (cx + FAN_W / 2, -LAND_L - 1), f"ファン接続幅 {FAN_W:g}", off=-7)
ax.text(4, -LAND_L - 3, f"ランド {LAND_L:g}（幅は製品長辺 {LAND_W:g} に連動）\n(0–{LAND_FLAT_L:g}: t={T_LAND_FLAT:g} 平面 / {LAND_FLAT_L:g}–{LAND_L:g}: 傾斜→t={T_LAND_END:g})",
        ha="left", va="top", fontsize=8, fontproperties=JP, color="#2e7d32")
ax.annotate("", (cx + 40, -LAND_L), (cx + 40, -GATE_OFF), arrowprops=dict(arrowstyle="<->", lw=0.8))
ax.text(cx + 43, -(LAND_L + GATE_OFF) / 2, f"{FAN_L:g}（ランド 2.5 端起点）", va="center", fontsize=9, fontproperties=JP)
dim(ax, (cx - WELL_D / 2, -GATE_OFF - 16), (cx + WELL_D / 2, -GATE_OFF - 16), f"井戸 φ{WELL_D:g} 深さ{WELL_DEPTH:g}", off=-9)
ax.text(cx + 12, -GATE_OFF + 2, f"スプルー φ{SPRUE_TOP:g}→φ{SPRUE_BOT:g} L={SPRUE_L:g}\nコールドスラッグ φ{SLUG_D:g}×{SLUG_DEPTH:g} 円筒（井戸底）",
        fontsize=8, fontproperties=JP)
ax.text(PW / 2, PH / 2, f"内側 t={T_INNER:g}", ha="center", fontsize=11, fontproperties=JP)
ax.text(PW / 2, PH - FRAME / 2, f"額縁 幅{FRAME:g} t={T_FRAME:g}", ha="center", va="center", fontsize=9, fontproperties=JP)
ax.text(cx - 100, -25, f"ファンゲート t={T_FAN:g} 均一\n（トグルで傾斜／肉盗み）", fontsize=9, fontproperties=JP, color="#1565c0")
ax.text(cx + 3, PH + 3, "A", fontsize=10, fontweight="bold"); ax.text(cx + 3, -85, "A'", fontsize=10, fontweight="bold")
ax.plot([cx, cx], [-85, PH + 8], "k-.", lw=0.6)
ax.set_xlim(-25, PW + 30); ax.set_ylim(-90, PH + 25); ax.set_aspect("equal")
ax.set_title("平面図（可動側から見る、単位 mm）", fontproperties=JP)
ax.set_xlabel("x"); ax.set_ylabel("y")

# ================= section along gate axis (y–z) =================
az.add_patch(Rectangle((0, -T_FRAME), FRAME, T_FRAME, fc="#ffe0b2", ec="k"))
az.add_patch(Rectangle((FRAME, -T_INNER), PH - 2 * FRAME, T_INNER, fc="#ffb74d", ec="k"))
az.add_patch(Rectangle((PH - FRAME, -T_FRAME), FRAME, T_FRAME, fc="#ffe0b2", ec="k"))
az.add_patch(Rectangle((-LAND_FLAT_L, -T_LAND_FLAT), LAND_FLAT_L, T_LAND_FLAT, fc="#a5d6a7", ec="k"))
ramp = [(-LAND_FLAT_L, 0), (-LAND_L, 0), (-LAND_L, -T_LAND_END), (-LAND_FLAT_L, -T_LAND_FLAT)]
az.add_patch(Polygon(ramp, closed=True, fc="#c8e6c9", ec="k"))
az.add_patch(Rectangle((-GATE_OFF, -T_FAN), GATE_OFF - LAND_L, T_FAN, fc="#bbdefb", ec="k"))
az.add_patch(Rectangle((-GATE_OFF - WELL_D / 2, -WELL_DEPTH), WELL_D, WELL_DEPTH, fc="#90caf9", ec="k"))
az.add_patch(Rectangle((-GATE_OFF - SLUG_D / 2, -WELL_DEPTH - SLUG_DEPTH), SLUG_D, SLUG_DEPTH, fc="#e0e0e0", ec="k", hatch="//"))
sprue = [(-GATE_OFF - SPRUE_BOT / 2, 0), (-GATE_OFF + SPRUE_BOT / 2, 0), (-GATE_OFF + SPRUE_TOP / 2, SPRUE_L), (-GATE_OFF - SPRUE_TOP / 2, SPRUE_L)]
az.add_patch(Polygon(sprue, closed=True, fc="#ef9a9a", ec="k"))
az.axhline(0, color="k", lw=0.8, ls="--")
az.text(PH + 2, 0.5, "PL", fontsize=9)
az.text(-GATE_OFF, SPRUE_L + 1.5, f"φ{SPRUE_TOP:g}（射出点）", ha="center", fontsize=8, fontproperties=JP)
az.text(-GATE_OFF + 5, 1, f"φ{SPRUE_BOT:g}", fontsize=8)
az.text(-GATE_OFF - 25, SPRUE_L / 2, f"スプルーブッシュ L={SPRUE_L:g}", fontsize=8, fontproperties=JP, ha="right")
az.text(-GATE_OFF - 25, -WELL_DEPTH - SLUG_DEPTH / 2, f"コールドスラッグ φ{SLUG_D:g} 深さ{SLUG_DEPTH:g}（円筒）", fontsize=8, fontproperties=JP, ha="right")
az.text(-GATE_OFF + 12, -WELL_DEPTH - 1.5, f"井戸 深さ{WELL_DEPTH:g}", fontsize=8, fontproperties=JP)
az.text(-32, -T_FAN - 1.5, f"ファン t={T_FAN:g}", fontsize=8, fontproperties=JP, color="#1565c0")
az.text(-LAND_L + 1, 1.0, f"ランド 傾斜 {T_LAND_END:g}→{T_LAND_FLAT:g}", fontsize=7, fontproperties=JP, color="#2e7d32")
az.text(-LAND_FLAT_L - 1, -T_LAND_END - 1.5, f"平面 {LAND_FLAT_L:g}mm t={T_LAND_FLAT:g}", fontsize=7, fontproperties=JP, color="#2e7d32", ha="center")
az.text(FRAME + 3, -T_INNER - 1.5, f"t={T_INNER:g}", fontsize=8)
az.text(2, -T_FRAME - 1.5, f"t={T_FRAME:g}", fontsize=8)
az.set_xlim(-GATE_OFF - 75, PH + 12); az.set_ylim(-12, SPRUE_L + 5)
az.set_aspect(2.0)
az.set_title("A–A' 断面（ゲート軸に沿う y–z、z を2倍に拡大）", fontproperties=JP)
az.set_xlabel("y  (0 = 製品長辺エッジ)", fontproperties=JP); az.set_ylabel("z")

fig.tight_layout()
fig.savefig("docs/draft/geometry_draft.png", dpi=130)
print("ok")
