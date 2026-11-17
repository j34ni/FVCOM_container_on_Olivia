#!/usr/bin/env python3
# FVCOM news visuals v0.2 — time-aware (multi-frame run output).
# Mesh truth from FVCOM .grd; scalars on nodes, u,v on cells (this build).
# Usage: python fvcom_plots.py IN.nc GRD.dat OUTDIR
import os
import sys
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.tri import Triangulation
from netCDF4 import Dataset
from PIL import Image
from scipy.interpolate import LinearNDInterpolator

NC, GRD, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(OUT, exist_ok=True)

# ---- grid from .grd -------------------------------------------------------
with open(GRD) as fh:
    lines = fh.read().split("\n")
i = 0
while not lines[i].startswith("Node Number"):
    i += 1
nodes_n = int(lines[i].split("=")[1])
cells_n = int(lines[i + 1].split("=")[1])
rows = [r.split() for r in lines[i + 2:] if r.strip()]
tri = np.array([[int(r[1]) - 1, int(r[2]) - 1, int(r[3]) - 1]
                for r in rows[:cells_n]])
print(f"grd: {nodes_n} nodes, {cells_n} cells")

# ---- fields (time-aware, surface slices only until needed) -----------------
n = Dataset(NC)
nt = len(n.variables["time"][:])
lat = np.asarray(n.variables["lat"][:], float)
lon = np.asarray(n.variables["lon"][:], float)
latc = np.asarray(n.variables["latc"][:], float)
lonc = np.asarray(n.variables["lonc"][:], float)
h = np.asarray(n.variables["h"][:], float)
sig = np.asarray(n.variables["siglay"][:], float)          # (sig, node)
US = np.asarray(n.variables["u"][:, 0], float)             # (t, cell) surface
VS = np.asarray(n.variables["v"][:, 0], float)
times = ["".join(s.astype(str)).strip() for s in n.variables["Times"][:]]
BEST = nt - 1                                              # peak tide (02:00)
print(f"frames: {nt}  {times[0]} -> {times[-1]}")

clat = np.cos(np.deg2rad(np.median(lat)))
x = np.deg2rad(lon) * clat * 6371.0                        # km
y = np.deg2rad(lat) * 6371.0
xc = np.deg2rad(lonc) * clat * 6371.0
yc = np.deg2rad(latc) * 6371.0
z = sig * h[None, :]                                       # (sig, node)
T = Triangulation(x, y, tri)


def cell_to_node(f):
    acc = np.zeros(nodes_n)
    cnt = np.zeros(nodes_n)
    for c in range(3):
        np.add.at(acc, tri[:, c], f)
        np.add.at(cnt, tri[:, c], 1.0)
    return acc / np.maximum(cnt, 1)


sp = np.hypot(US[BEST], VS[BEST])                          # (cell,)
spn = cell_to_node(sp)

# outline = edges of the true triangulation used once
ec = Counter()
for a, b in ((0, 1), (1, 2), (2, 0)):
    ec.update(map(tuple, np.sort(tri[:, [a, b]], axis=1)))
segs = np.array([[[x[a], y[a]], [x[b], y[b]]]
                 for (a, b), k in ec.items() if k == 1])


def frame_axes(ax):
    ax.set_xlim(x.min(), x.max()); ax.set_ylim(y.min(), y.max())
    ax.set_aspect("equal"); ax.set_axis_off()


RUN = "FVCOM (Container on Olivia) — "
# ---- 1. surface speed at peak ----------------------------------------------
fig, ax = plt.subplots(figsize=(11, 9), facecolor="0.08")
ax.set_facecolor("0.08")
tc = ax.tripcolor(T, spn, cmap="magma", vmin=0,
                  vmax=np.percentile(spn, 99.5))
ax.add_collection(LineCollection(segs, colors="0.9", linewidths=0.5,
                                 alpha=0.9))
frame_axes(ax)
cb = fig.colorbar(tc, ax=ax, shrink=0.75)
cb.set_label("surface current speed (m s$^{-1}$)", color="w")
cb.ax.yaxis.set_tick_params(color="w")
plt.setp(cb.ax.get_yticklabels(), color="w")
ax.set_title(RUN + "peak surface currents, Favne domain "
             "(Mohns Ridge, 72.7N)", color="w")
fig.savefig(f"{OUT}/01_speed_map.png", dpi=160, bbox_inches="tight",
            facecolor="0.08")
plt.close(fig)

# ---- 2. relative vorticity at peak ------------------------------------------
un, vn = cell_to_node(US[BEST]), cell_to_node(VS[BEST])
px, py = x[tri], y[tri]
A = 0.5 * ((px[:, 1] - px[:, 0]) * (py[:, 2] - py[:, 0])
           - (px[:, 2] - px[:, 0]) * (py[:, 1] - py[:, 0]))
b = np.column_stack([py[:, 1] - py[:, 2], py[:, 2] - py[:, 0],
                     py[:, 0] - py[:, 1]])
vortn = cell_to_node(((vn[tri] * b).sum(axis=1)
                      - (un[tri] * b).sum(axis=1)) / (2 * A) * 1e-3)
lim = np.percentile(np.abs(vortn), 98)
fig, ax = plt.subplots(figsize=(11, 9))
tc = ax.tripcolor(T, vortn, cmap="bwr", vmin=-lim, vmax=lim)
ax.add_collection(LineCollection(segs, colors="0.15", linewidths=0.5,
                                 alpha=0.9))
frame_axes(ax)
cb = fig.colorbar(tc, ax=ax, shrink=0.7)
cb.set_label(r"vorticity (s$^{-1}$)")
ax.set_title(RUN + "vorticity at peak tide, Favne domain (2 h run)")
fig.savefig(f"{OUT}/02_vorticity.png", dpi=160, bbox_inches="tight")
plt.close(fig)

# ---- 3. drifter GIF: advection in time-varying field ------------------------
N, dt = 2000, 60.0                       # 2 h / 60 s = 120 steps
DT_FR = 600.0                            # output cadence = data cadence
STEPS = int((nt - 1) * DT_FR / dt)       # 120
rng = np.random.default_rng(42)
pidx = rng.choice(len(xc), N, replace=False)
pos = np.column_stack([xc[pidx], yc[pidx]]).copy()
csp = sp[pidx]
Q = np.column_stack([xc, yc])
IU = [LinearNDInterpolator(Q, US[t]) for t in range(nt)]
IV = [LinearNDInterpolator(Q, VS[t]) for t in range(nt)]


def vel(q, t):
    """time-linear interpolation between the 10-min frames; NaN -> 0."""
    f0 = int(t // DT_FR)
    w = (t - f0 * DT_FR) / DT_FR
    f1 = min(f0 + 1, nt - 1)
    uu = (1 - w) * IU[f0](q) + w * IU[f1](q)
    vv = (1 - w) * IV[f0](q) + w * IV[f1](q)
    uu = np.nan_to_num(uu); vv = np.nan_to_num(vv)
    return uu, vv


trails = np.empty((STEPS + 1, N, 2))
trails[0] = pos
for k in range(STEPS):
    k1u, k1v = vel(pos, k * dt)
    k2u, k2v = vel(pos + 0.5 * dt * np.column_stack([k1u, k1v]) * 1e-3,
                   (k + 0.5) * dt)
    pos = pos + dt * np.column_stack([k2u, k2v]) * 1e-3
    trails[k + 1] = pos
fig, ax = plt.subplots(figsize=(11, 9), facecolor="0.08")
ax.set_facecolor("0.08")
base = ax.tripcolor(T, spn, cmap="magma", vmin=0,
                    vmax=np.percentile(spn, 99.5))
base.set_alpha(0.45)
ax.add_collection(LineCollection(segs, colors="0.85", linewidths=0.5,
                                 alpha=0.9))
frame_axes(ax)
cb = fig.colorbar(plt.cm.ScalarMappable(
    plt.Normalize(0, float(csp.max())), cmap="hot"), ax=ax, shrink=0.75)
cb.set_label("drifter speed (m s$^{-1}$)", color="w")
cb.ax.yaxis.set_tick_params(color="w")
plt.setp(cb.ax.get_yticklabels(), color="w")
sc = None
for k in range(0, STEPS + 1, 10):        # one GIF frame per 10 min
    if sc is not None:
        sc.remove()
    ok = np.isfinite(trails[k, :, 0])
    sc = ax.scatter(trails[k, ok, 0], trails[k, ok, 1], c=csp[ok],
                    cmap="hot", norm=plt.Normalize(0, float(csp.max())),
                    s=5, zorder=3)
    hh = k * dt / 3600.0
    ax.set_title(RUN + f"virtual drifters — 2025-07-23 "
                 f"{int(hh):02d}:{int(round((hh % 1) * 60)):02d}", color="w")
    fig.savefig(f"{OUT}/_f{k:03d}.png", dpi=160, bbox_inches="tight",
                facecolor="0.08")
imgs = [Image.open(f"{OUT}/_f{k:03d}.png") for k in range(0, STEPS + 1, 10)]
imgs[0].save(f"{OUT}/03_drifters.gif", save_all=True,
             append_images=imgs[1:], duration=400, loop=0)
for k in range(0, STEPS + 1, 10):
    os.remove(f"{OUT}/_f{k:03d}.png")
plt.close(fig)

# ---- 4. T/S section at end frame ---------------------------------------------
temp = np.asarray(n.variables["temp"][BEST], float)        # (sig, node)
salt = np.asarray(n.variables["salinity"][BEST], float)
sel = np.where(np.abs(y - np.median(y)) < 8.0)[0]
nb = 140
xb = np.linspace(x[sel].min(), x[sel].max(), nb + 1)
binid = np.clip(np.digitize(x[sel], xb) - 1, 0, nb - 1)
cnt = np.bincount(binid, minlength=nb).astype(float)
D = np.zeros((sig.shape[0], nb))
Zm = np.zeros((sig.shape[0], nb))


def binned(f):
    return np.stack([np.bincount(binid, weights=f[L, sel], minlength=nb)
                     / np.maximum(cnt, 1) for L in range(sig.shape[0])])


Zm = binned(-z * 0 - (sig * h[None, :]))                   # depth (m)
D = np.tile(np.bincount(binid, weights=x[sel] - x[sel].min(),
                        minlength=nb) / np.maximum(cnt, 1),
            (sig.shape[0], 1))
fig, axs = plt.subplots(2, 1, figsize=(11, 9), sharex=True)
for ax, fld, cmap, lab in ((axs[0], binned(temp), "YlOrRd_r",
                            "temperature (C)"),
                           (axs[1], binned(salt), "Paired",
                            "salinity (PSU)")):
    m = np.ma.masked_where((Zm < 0.5) | (cnt == 0), fld)
    pc = ax.pcolormesh(D, -Zm, m, cmap=cmap, shading="nearest")
    ax.set_ylabel("depth (m)")
    cb = fig.colorbar(pc, ax=ax); cb.set_label(lab)
axs[0].set_title(RUN + "section across the Favne domain, 100 sigma "
                 "layers, t=02:00")
axs[1].set_xlabel("distance along section (km)")
fig.savefig(f"{OUT}/04_section_ts.png", dpi=160, bbox_inches="tight")
plt.close(fig)
print("OK ->", OUT)
