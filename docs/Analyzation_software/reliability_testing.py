#this code allows for the user to test how reliable the system is between scans.
#procedure: Scan the same module two times using the same settings, than attach the path of the csv file for the respectives scans
#expected output: The RMS should be about 10x the point noise (how much the measurement system varies at a certain point).



import numpy as np
import pandas as pd
from pathlib import Path

# ====== SET YOUR FILE PATHS HERE ======
SCAN0 = Path(r"C:\Users\jayde\Downloads\test1\t1\_GD_1.csv")
SCAN1 = Path(r"C:\Users\jayde\Downloads\test1\t2\_GD_0.csv")
MM_TO_UM = 1000.0

def find_xyz_cols(df):
    lower = {c.lower(): c for c in df.columns}
    for prefix in ["front ", "back ", ""]:
        x = lower.get((prefix + "x").strip())
        y = lower.get((prefix + "y").strip())
        z = lower.get((prefix + "z").strip())
        if x and y and z:
            return x, y, z
    raise ValueError(f"Could not find x/y/z columns. Columns are: {list(df.columns)}")

def clean_xyz(df, xc, yc, zc):
    x = df[xc].to_numpy(float)
    y = df[yc].to_numpy(float)
    z = df[zc].to_numpy(float)
    m = np.isfinite(x) & np.isfinite(y) & np.isfinite(z)
    return x[m], y[m], z[m]

def surface_metrics(z_mm):
    z_um = z_mm * MM_TO_UM
    zc = z_um - np.mean(z_um)
    return {
        "Rq_RMS_um": float(np.sqrt(np.mean(zc**2))),
        "Ra_um": float(np.mean(np.abs(zc))),
        "PkPk_um": float(np.max(z_um) - np.min(z_um)),
        "mean_um": float(np.mean(z_um)),
        "N_points": int(len(z_um)),
    }

def fit_plane(x_mm, y_mm, z_mm):
    A = np.c_[x_mm, y_mm, np.ones_like(x_mm)]
    coeff, *_ = np.linalg.lstsq(A, z_mm, rcond=None)  # z in mm
    a, b, c = coeff
    resid = z_mm - (A @ coeff)
    return float(a), float(b), float(c), resid

def tilt_removed_metrics(x_mm, y_mm, z_mm):
    a, b, c, resid = fit_plane(x_mm, y_mm, z_mm)
    resid_um = resid * MM_TO_UM
    return {
        "a_mm_per_mm": a,
        "b_mm_per_mm": b,
        "c_mm": c,
        "tilt_x_deg": float(np.degrees(np.arctan(a))),
        "tilt_y_deg": float(np.degrees(np.arctan(b))),
        "tilt_mag_deg": float(np.degrees(np.arctan(np.sqrt(a*a + b*b)))),
        "Rq_RMS_tilt_removed_um": float(np.sqrt(np.mean(resid_um**2))),
        "Ra_tilt_removed_um": float(np.mean(np.abs(resid_um))),
        "PkPk_tilt_removed_um": float(np.max(resid_um) - np.min(resid_um)),
        "N_points": int(len(resid_um)),
    }, resid

def repeatability_metrics(z0_mm, z1_mm, label="raw"):
    dz_um = (z0_mm - z1_mm) * MM_TO_UM
    return {
        f"Repeat_RMS_{label}_um": float(np.sqrt(np.mean(dz_um**2))),
        f"Repeat_PkPk_{label}_um": float(np.max(dz_um) - np.min(dz_um)),
        f"Mean_offset_{label}_um": float(np.mean(dz_um)),
        f"Std_{label}_um": float(np.std(dz_um)),
        f"N_points_{label}": int(len(dz_um)),
    }

def _fmt(v, units=""):
    if isinstance(v, (int, np.integer)):
        return f"{v}"
    if isinstance(v, (float, np.floating)):
        # angles / slopes keep more precision, µm keep 3 decimals
        if units == "deg":
            return f"{v:.4f}"
        if units == "mm/mm":
            return f"{v:.6f}"
        return f"{v:.3f}"
    return str(v)

def print_summary_table(title, rows):
    # rows: list of (metric, value, units)
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)
    max_m = max(len(m) for m, _, _ in rows)
    for m, v, u in rows:
        print(f"{m:<{max_m}} : {_fmt(v, u)} {u}".rstrip())
    print("=" * 70)

def main():
    # --- Load ---
    df0 = pd.read_csv(SCAN0)
    df1 = pd.read_csv(SCAN1)

    x0c, y0c, z0c = find_xyz_cols(df0)
    x1c, y1c, z1c = find_xyz_cols(df1)

    x0, y0, z0 = clean_xyz(df0, x0c, y0c, z0c)
    x1, y1, z1 = clean_xyz(df1, x1c, y1c, z1c)

    # --- Match by (x,y) robustly ---
    def to_keyed(x, y, z):
        keys = np.round(np.c_[x, y], 3)  # 0.001 mm snapping
        return {tuple(k): float(v) for k, v in zip(keys, z)}

    d0 = to_keyed(x0, y0, z0)
    d1 = to_keyed(x1, y1, z1)
    keys = sorted(set(d0) & set(d1))
    if not keys:
        raise ValueError("No matching (x,y) points found between scans.")

    X = np.array([k[0] for k in keys], float)
    Y = np.array([k[1] for k in keys], float)
    Z0 = np.array([d0[k] for k in keys], float)  # mm
    Z1 = np.array([d1[k] for k in keys], float)  # mm

    # --- Compute metrics ---
    surf0 = surface_metrics(Z0)
    surf1 = surface_metrics(Z1)
    tilt0, r0 = tilt_removed_metrics(X, Y, Z0)
    tilt1, r1 = tilt_removed_metrics(X, Y, Z1)

    rep_raw = repeatability_metrics(Z0, Z1, "raw")
    rep_tr  = repeatability_metrics(r0, r1, "tilt_removed")

    # --- Nice end summary ---
    # Quick averages for headline
    surf_rms_avg = (surf0["Rq_RMS_um"] + surf1["Rq_RMS_um"]) / 2
    surf_pk_avg  = (surf0["PkPk_um"] + surf1["PkPk_um"]) / 2
    tilt_rms_avg = (tilt0["Rq_RMS_tilt_removed_um"] + tilt1["Rq_RMS_tilt_removed_um"]) / 2

    print_summary_table(
        "FILES + DETECTED COLUMNS",
        [
            ("Scan 0 path", str(SCAN0), ""),
            ("Scan 1 path", str(SCAN1), ""),
            ("Scan 0 cols", f"{x0c}, {y0c}, {z0c}", ""),
            ("Scan 1 cols", f"{x1c}, {y1c}, {z1c}", ""),
            ("Matched points", len(keys), ""),
        ],
    )

    print_summary_table(
        "SURFACE METRICS (µm)",
        [
            ("Rq/RMS Scan0", surf0["Rq_RMS_um"], "µm"),
            ("Rq/RMS Scan1", surf1["Rq_RMS_um"], "µm"),
            ("Rq/RMS Avg",   surf_rms_avg,       "µm"),
            ("Ra Scan0",     surf0["Ra_um"],     "µm"),
            ("Ra Scan1",     surf1["Ra_um"],     "µm"),
            ("Pk–Pk Scan0",  surf0["PkPk_um"],   "µm"),
            ("Pk–Pk Scan1",  surf1["PkPk_um"],   "µm"),
            ("Pk–Pk Avg",    surf_pk_avg,        "µm"),
            ("Mean height Scan0", surf0["mean_um"], "µm"),
            ("Mean height Scan1", surf1["mean_um"], "µm"),
        ],
    )

    print_summary_table(
        "TILT (BEST-FIT PLANE) + TILT-REMOVED SURFACE (µm)",
        [
            ("a slope Scan0", tilt0["a_mm_per_mm"], "mm/mm"),
            ("b slope Scan0", tilt0["b_mm_per_mm"], "mm/mm"),
            ("Tilt X Scan0",  tilt0["tilt_x_deg"],  "deg"),
            ("Tilt Y Scan0",  tilt0["tilt_y_deg"],  "deg"),
            ("Tilt mag Scan0",tilt0["tilt_mag_deg"],"deg"),
            ("Tilt-removed RMS Scan0", tilt0["Rq_RMS_tilt_removed_um"], "µm"),
            ("Tilt-removed RMS Scan1", tilt1["Rq_RMS_tilt_removed_um"], "µm"),
            ("Tilt-removed RMS Avg",   tilt_rms_avg, "µm"),
            ("Tilt-removed Pk–Pk Scan0", tilt0["PkPk_tilt_removed_um"], "µm"),
            ("Tilt-removed Pk–Pk Scan1", tilt1["PkPk_tilt_removed_um"], "µm"),
        ],
    )

    print_summary_table(
        "REPEATABILITY (Scan0 − Scan1) (µm)",
        [
            ("Repeat RMS (raw)",         rep_raw["Repeat_RMS_raw_um"], "µm"),
            ("Repeat Pk–Pk (raw)",       rep_raw["Repeat_PkPk_raw_um"], "µm"),
            ("Mean offset (raw)",        rep_raw["Mean_offset_raw_um"], "µm"),
            ("Std (raw)",                rep_raw["Std_raw_um"], "µm"),
            ("Repeat RMS (tilt-removed)", rep_tr["Repeat_RMS_tilt_removed_um"], "µm"),
            ("Repeat Pk–Pk (tilt-removed)", rep_tr["Repeat_PkPk_tilt_removed_um"], "µm"),
            ("Mean offset (tilt-removed)", rep_tr["Mean_offset_tilt_removed_um"], "µm"),
            ("Std (tilt-removed)",         rep_tr["Std_tilt_removed_um"], "µm"),
        ],
    )

    # --- Save a CSV report next to the script ---
    report_rows = []
    def add(group, metric, value, units=""):
        report_rows.append({"Group": group, "Metric": metric, "Value": value, "Units": units})

    for k,v in surf0.items():
        if k == "N_points": continue
        add("Surface Scan0", k, v, "µm")
    for k,v in surf1.items():
        if k == "N_points": continue
        add("Surface Scan1", k, v, "µm")

    for k,v in tilt0.items():
        units = "deg" if k.endswith("_deg") else ("mm/mm" if k.endswith("_mm_per_mm") else ("µm" if k.endswith("_um") else "mm"))
        add("Tilt/TiltRemoved Scan0", k, v, units)
    for k,v in tilt1.items():
        units = "deg" if k.endswith("_deg") else ("mm/mm" if k.endswith("_mm_per_mm") else ("µm" if k.endswith("_um") else "mm"))
        add("Tilt/TiltRemoved Scan1", k, v, units)

    for k,v in rep_raw.items():
        add("Repeatability Raw", k, v, "µm" if k.endswith("_um") else "")
    for k,v in rep_tr.items():
        add("Repeatability TiltRemoved", k, v, "µm" if k.endswith("_um") else "")

    report = pd.DataFrame(report_rows)
    out_path = Path(__file__).with_name("metrics_summary_report.csv")
    report.to_csv(out_path, index=False)
    print(f"\nSaved CSV report to: {out_path}")

if __name__ == "__main__":
    main()
