#This code will generate a singular curvature value from the full dataset for each point. Additionally, it will include several other metrics for comparison. Feel free to ignore the other ones as the single curvature value and RMS are the most important generally.
#Change the CSV_paths to include the files you want to compare


import numpy as np
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt

# ============================================================
# USER INPUT
# ============================================================
CSV_PATHS = [
    r"C:\Users\jayde\Downloads\test1\Finished TandemPV batch\A12F92147\3-24-26\_GD_0.csv",
    r"C:\Users\jayde\Downloads\test1\Finished TandemPV batch\A12F92150\3-24-26\_GD_0.csv",
    r"C:\Users\jayde\Downloads\test1\Finished TandemPV batch\A12F92205\3-24-26\_GD_0.csv",
    r"C:\Users\jayde\Downloads\test1\Finished TandemPV batch\A12F92206\3-24-26\_GD_0.csv",
    r"C:\Users\jayde\Downloads\test1\Finished TandemPV batch\A12F92207\3-24-26\_GD_0.csv",
    r"C:\Users\jayde\Downloads\test1\Finished TandemPV batch\A15F52525\3-24-26\_GD_0.csv",
    r"C:\Users\jayde\Downloads\test1\Finished TandemPV batch\A15F52525\4-2-26\_GD_0.csv",
    r"C:\Users\jayde\Downloads\test1\Finished TandemPV batch\A12F92147\4-2-26\_GD_0.csv",
    r"C:\Users\jayde\Downloads\test1\Finished TandemPV batch\A12F92150\4-7-26\_GD_0.csv",
    r"C:\Users\jayde\Downloads\test1\Finished TandemPV batch\A12F92205\4-7-26\_GD_0.csv",
    r"C:\Users\jayde\Downloads\test1\Finished TandemPV batch\A12F92206\4-7-26\_GD_0.csv",
    r"C:\Users\jayde\Downloads\test1\Finished TandemPV batch\A12F92207\4-7-26\_GD_0.csv",
]

OUTPUT_DIR = Path(r"C:\Users\jayde\Downloads\curvature_outputs")
OUTPUT_MAIN = OUTPUT_DIR / "curvature_clean.csv"
OUTPUT_BATCH = OUTPUT_DIR / "curvature_batch_summary.csv"
OUTPUT_FAIL = OUTPUT_DIR / "curvature_failures.csv"
BAR_CHART_PATH = OUTPUT_DIR / "curvature_bar_chart.png"

HEATMAP_DIR = OUTPUT_DIR / "heatmaps_magnitude"
SIGNED_HEATMAP_DIR = OUTPUT_DIR / "heatmaps_signed"

MM_TO_UM = 1000.0
MIN_GRID_SIZE = 3

# ------------------------------------------------------------
# SIGN CONVENTION NOTE
# ------------------------------------------------------------
# You must verify which sign means inward vs outward for YOUR setup.
# Start with these labels, then flip SIGN_POSITIVE_LABEL / SIGN_NEGATIVE_LABEL
# if needed after checking one known sample.
SIGN_POSITIVE_LABEL = "Outward"
SIGN_NEGATIVE_LABEL = "Inward"

# tolerance for deciding "flat / mixed" from signed mean curvature
SIGNED_DIRECTION_TOL = 1e-5

# ------------------------------------------------------------
# IMPACT SCORE SETTINGS
# ------------------------------------------------------------
# This controls how strongly asymmetry affects ranking.
# 1.0 is a good starting point.
ASYMMETRY_WEIGHT = 1.0


# ============================================================
# HELPERS
# ============================================================
def ensure_dirs():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    HEATMAP_DIR.mkdir(parents=True, exist_ok=True)
    SIGNED_HEATMAP_DIR.mkdir(parents=True, exist_ok=True)


def find_orientation_columns(df, orientation):
    cols = {c.lower().strip(): c for c in df.columns}
    x = cols.get(f"{orientation} x")
    y = cols.get(f"{orientation} y")
    z = cols.get(f"{orientation} z")
    if x and y and z:
        return x, y, z
    return None


def find_plain_xyz_columns(df):
    cols = {c.lower().strip(): c for c in df.columns}
    x = cols.get("x")
    y = cols.get("y")
    z = cols.get("z")
    if x and y and z:
        return x, y, z
    return None


def clean_xyz(df, xcol, ycol, zcol):
    x = pd.to_numeric(df[xcol], errors="coerce").to_numpy(dtype=float)
    y = pd.to_numeric(df[ycol], errors="coerce").to_numpy(dtype=float)
    z = pd.to_numeric(df[zcol], errors="coerce").to_numpy(dtype=float)
    m = np.isfinite(x) & np.isfinite(y) & np.isfinite(z)
    return x[m], y[m], z[m]


def fit_plane(x_mm, y_mm, z_mm):
    A = np.c_[x_mm, y_mm, np.ones_like(x_mm)]
    coeff, *_ = np.linalg.lstsq(A, z_mm, rcond=None)
    a, b, c = coeff
    resid = z_mm - (A @ coeff)
    return float(a), float(b), float(c), resid


def robust_grid_from_xyz(x, y, z, grid_n=None):
    """
    Build a regular grid from noisy stage coordinates by assigning each point
    to the nearest nominal grid location.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    z = np.asarray(z, dtype=float)

    if len(x) != len(y) or len(x) != len(z):
        raise ValueError("x, y, z must have same length")

    npts = len(x)
    if grid_n is None:
        grid_n = int(round(np.sqrt(npts)))

    if grid_n < MIN_GRID_SIZE:
        raise ValueError(f"Grid size too small: {grid_n}")

    x_nom = np.linspace(np.min(x), np.max(x), grid_n)
    y_nom = np.linspace(np.min(y), np.max(y), grid_n)

    ix = np.abs(x[:, None] - x_nom[None, :]).argmin(axis=1)
    iy = np.abs(y[:, None] - y_nom[None, :]).argmin(axis=1)

    z_sum = np.zeros((grid_n, grid_n), dtype=float)
    z_count = np.zeros((grid_n, grid_n), dtype=int)

    for i in range(npts):
        z_sum[iy[i], ix[i]] += z[i]
        z_count[iy[i], ix[i]] += 1

    Z = np.full((grid_n, grid_n), np.nan, dtype=float)
    mask = z_count > 0
    Z[mask] = z_sum[mask] / z_count[mask]

    # fill missing cells by neighbor averaging
    if np.isnan(Z).any():
        for _ in range(20):
            missing_before = int(np.isnan(Z).sum())
            if missing_before == 0:
                break

            Z_new = Z.copy()
            for r, c in zip(*np.where(np.isnan(Z))):
                neighbors = []
                for rr, cc in [
                    (r - 1, c), (r + 1, c),
                    (r, c - 1), (r, c + 1),
                    (r - 1, c - 1), (r - 1, c + 1),
                    (r + 1, c - 1), (r + 1, c + 1),
                ]:
                    if 0 <= rr < grid_n and 0 <= cc < grid_n and np.isfinite(Z[rr, cc]):
                        neighbors.append(Z[rr, cc])

                if neighbors:
                    Z_new[r, c] = float(np.mean(neighbors))

            Z = Z_new
            missing_after = int(np.isnan(Z).sum())
            if missing_after == missing_before:
                break

    if np.isnan(Z).any():
        n_left = int(np.isnan(Z).sum())
        raise ValueError(f"Could not fill {n_left} missing grid cells after binning.")

    return x_nom, y_nom, Z


def surface_height_metrics(z_mm):
    z_um = z_mm * MM_TO_UM
    zc = z_um - np.mean(z_um)
    return {
        "height_rms_um": float(np.sqrt(np.mean(zc**2))),
        "height_pkpk_um": float(np.max(z_um) - np.min(z_um)),
        "n_points": int(len(z_um)),
    }


def signed_direction_label(val, tol=SIGNED_DIRECTION_TOL):
    if not np.isfinite(val):
        return "Unknown"
    if abs(val) < tol:
        return "Mixed/Flat"
    if val > 0:
        return SIGN_POSITIVE_LABEL
    return SIGN_NEGATIVE_LABEL


def curvature_metrics_from_grid(x_unique, y_unique, Z_mm):
    dZ_dy, dZ_dx = np.gradient(Z_mm, y_unique, x_unique, edge_order=2)

    d2Z_dx2 = np.gradient(dZ_dx, x_unique, axis=1, edge_order=2)
    d2Z_dy2 = np.gradient(dZ_dy, y_unique, axis=0, edge_order=2)

    # unsigned magnitude
    curv_mag = np.sqrt(d2Z_dx2**2 + d2Z_dy2**2)

    # signed curvature proxy
    signed_curv = 0.5 * (d2Z_dx2 + d2Z_dy2)

    return {
        "curvature_rms_1_per_mm": float(np.sqrt(np.mean(curv_mag**2))),
        "curvature_meanabs_1_per_mm": float(np.mean(np.abs(curv_mag))),
        "curvature_max_1_per_mm": float(np.max(np.abs(curv_mag))),
        "signed_curvature_mean_1_per_mm": float(np.mean(signed_curv)),
        "signed_curvature_rms_1_per_mm": float(np.sqrt(np.mean(signed_curv**2))),
        "curvature_map": curv_mag,
        "signed_curvature_map": signed_curv,
    }


def process_one_surface(x, y, z, label="surface"):
    out = {}

    out.update({f"{label}_{k}": v for k, v in surface_height_metrics(z).items()})

    a, b, c, resid = fit_plane(x, y, z)
    out[f"{label}_tilt_x_deg"] = float(np.degrees(np.arctan(a)))
    out[f"{label}_tilt_y_deg"] = float(np.degrees(np.arctan(b)))
    out[f"{label}_tilt_mag_deg"] = float(np.degrees(np.arctan(np.sqrt(a * a + b * b))))

    out.update({
        f"{label}_tilt_removed_{k}": v
        for k, v in surface_height_metrics(resid).items()
        if k != "n_points"
    })

    grid_n = int(round(np.sqrt(len(resid))))
    xg, yg, Zg = robust_grid_from_xyz(x, y, resid, grid_n=grid_n)

    curv = curvature_metrics_from_grid(xg, yg, Zg)
    out[f"{label}_curvature_rms_1_per_mm"] = curv["curvature_rms_1_per_mm"]
    out[f"{label}_curvature_meanabs_1_per_mm"] = curv["curvature_meanabs_1_per_mm"]
    out[f"{label}_curvature_max_1_per_mm"] = curv["curvature_max_1_per_mm"]
    out[f"{label}_signed_curvature_mean_1_per_mm"] = curv["signed_curvature_mean_1_per_mm"]
    out[f"{label}_signed_curvature_rms_1_per_mm"] = curv["signed_curvature_rms_1_per_mm"]
    out[f"{label}_direction_label"] = signed_direction_label(curv["signed_curvature_mean_1_per_mm"])

    # raw grid objects for plotting / later use
    out[f"_{label}_xg"] = xg
    out[f"_{label}_yg"] = yg
    out[f"_{label}_Zg"] = Zg
    out[f"_{label}_curv_map"] = curv["curvature_map"]
    out[f"_{label}_signed_curv_map"] = curv["signed_curvature_map"]

    return out


def match_two_grids(xf, yf, zf, xb, yb, zb):
    kf = pd.DataFrame({
        "x": np.round(xf, 3),
        "y": np.round(yf, 3),
        "zf": zf,
    }).groupby(["x", "y"], as_index=False)["zf"].mean()

    kb = pd.DataFrame({
        "x": np.round(xb, 3),
        "y": np.round(yb, 3),
        "zb": zb,
    }).groupby(["x", "y"], as_index=False)["zb"].mean()

    merged = pd.merge(kf, kb, on=["x", "y"], how="inner")
    if merged.empty:
        raise ValueError("No matched front/back (x,y) points found.")

    return (
        merged["x"].to_numpy(dtype=float),
        merged["y"].to_numpy(dtype=float),
        merged["zf"].to_numpy(dtype=float),
        merged["zb"].to_numpy(dtype=float),
    )


def safe_ratio(a, b):
    if not np.isfinite(a) or not np.isfinite(b) or b == 0:
        return np.nan
    return float(a / b)


def sanitize_name(s):
    keep = []
    for ch in str(s):
        if ch.isalnum() or ch in ("-", "_"):
            keep.append(ch)
        else:
            keep.append("_")
    return "".join(keep)


# ============================================================
# PLOTTING
# ============================================================
def save_heatmap(xg, yg, data, title, out_path):
    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(
        data,
        origin="lower",
        aspect="auto",
        extent=[float(np.min(xg)), float(np.max(xg)), float(np.min(yg)), float(np.max(yg))]
    )
    ax.set_title(title)
    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Y (mm)")
    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def save_signed_heatmap(xg, yg, data, title, out_path):
    vmax = np.nanmax(np.abs(data))
    if not np.isfinite(vmax) or vmax == 0:
        vmax = 1.0

    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(
        data,
        origin="lower",
        aspect="auto",
        cmap="coolwarm",
        vmin=-vmax,
        vmax=vmax,
        extent=[float(np.min(xg)), float(np.max(xg)), float(np.min(yg)), float(np.max(yg))]
    )
    ax.set_title(title)
    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Y (mm)")
    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def save_bar_chart(summary_df, out_path):
    if summary_df.empty:
        return

    label_col = "sample"
    y_col = "impact_score" if "impact_score" in summary_df.columns else "combined_curvature"

    if y_col not in summary_df.columns:
        if "front_curvature" in summary_df.columns:
            y_col = "front_curvature"
        else:
            return

    labels = summary_df[label_col].astype(str).tolist()
    vals = pd.to_numeric(summary_df[y_col], errors="coerce").to_numpy(dtype=float)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(labels, vals)
    ax.set_title(f"{y_col.replace('_', ' ').title()} by Sample")
    ax.set_xlabel("Sample")
    ax.set_ylabel(y_col.replace("_", " "))
    plt.xticks(rotation=45, ha="right")
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


# ============================================================
# PROCESS ONE FILE
# ============================================================
def process_csv_file(path):
    df = pd.read_csv(path)

    sample_name = path.parent.parent.name
    date_folder = path.parent.name

    row = {
        "parent_folder": path.parent.parent.parent.name if path.parent.parent.parent != path.parent.parent else "",
        "sample": sample_name,
        "date_folder": date_folder,
        "file_name": path.name,
        "full_path": str(path),
    }

    plot_payload = {
        "sample": sample_name,
        "date_folder": date_folder,
        "front": None,
        "back": None,
        "combined": None,
    }

    front_cols = find_orientation_columns(df, "front")
    back_cols = find_orientation_columns(df, "back")
    plain_cols = find_plain_xyz_columns(df)

    have_front = front_cols is not None
    have_back = back_cols is not None
    have_plain = plain_cols is not None

    if not any([have_front, have_back, have_plain]):
        raise ValueError(
            f"No usable columns found in {path.name}. Expected front x/y/z, back x/y/z, or plain x/y/z."
        )

    if have_front:
        x, y, z = clean_xyz(df, *front_cols)
        out = process_one_surface(x, y, z, label="front")
        row["front_curvature"] = out["front_curvature_rms_1_per_mm"]
        row["front_signed_curvature"] = out["front_signed_curvature_mean_1_per_mm"]
        row["front_direction"] = out["front_direction_label"]
        row["front_rms_um"] = out["front_tilt_removed_height_rms_um"]
        row["front_pkpk_um"] = out["front_tilt_removed_height_pkpk_um"]
        row["front_tilt_deg"] = out["front_tilt_mag_deg"]

        plot_payload["front"] = {
            "xg": out["_front_xg"],
            "yg": out["_front_yg"],
            "curv_map": out["_front_curv_map"],
            "signed_curv_map": out["_front_signed_curv_map"],
        }

    if have_back:
        x, y, z = clean_xyz(df, *back_cols)
        out = process_one_surface(x, y, z, label="back")
        row["back_curvature"] = out["back_curvature_rms_1_per_mm"]
        row["back_signed_curvature"] = out["back_signed_curvature_mean_1_per_mm"]
        row["back_direction"] = out["back_direction_label"]
        row["back_rms_um"] = out["back_tilt_removed_height_rms_um"]
        row["back_pkpk_um"] = out["back_tilt_removed_height_pkpk_um"]
        row["back_tilt_deg"] = out["back_tilt_mag_deg"]

        plot_payload["back"] = {
            "xg": out["_back_xg"],
            "yg": out["_back_yg"],
            "curv_map": out["_back_curv_map"],
            "signed_curv_map": out["_back_signed_curv_map"],
        }

    if have_plain and not have_front and not have_back:
        x, y, z = clean_xyz(df, *plain_cols)
        out = process_one_surface(x, y, z, label="surface")
        row["surface_curvature"] = out["surface_curvature_rms_1_per_mm"]
        row["surface_signed_curvature"] = out["surface_signed_curvature_mean_1_per_mm"]
        row["surface_direction"] = out["surface_direction_label"]
        row["surface_rms_um"] = out["surface_tilt_removed_height_rms_um"]
        row["surface_pkpk_um"] = out["surface_tilt_removed_height_pkpk_um"]
        row["surface_tilt_deg"] = out["surface_tilt_mag_deg"]

        plot_payload["front"] = {
            "xg": out["_surface_xg"],
            "yg": out["_surface_yg"],
            "curv_map": out["_surface_curv_map"],
            "signed_curv_map": out["_surface_signed_curv_map"],
        }

    if have_front and have_back:
        xf, yf, zf = clean_xyz(df, *front_cols)
        xb, yb, zb = clean_xyz(df, *back_cols)

        xm, ym, zfm, zbm = match_two_grids(xf, yf, zf, xb, yb, zb)

        _, _, _, zf_resid = fit_plane(xm, ym, zfm)
        _, _, _, zb_resid = fit_plane(xm, ym, zbm)

        z_comb = zf_resid - zb_resid
        out = process_one_surface(xm, ym, z_comb, label="combined")

        row["combined_curvature"] = out["combined_curvature_rms_1_per_mm"]
        row["combined_signed_curvature"] = out["combined_signed_curvature_mean_1_per_mm"]
        row["combined_direction"] = out["combined_direction_label"]
        row["combined_rms_um"] = out["combined_tilt_removed_height_rms_um"]
        row["combined_pkpk_um"] = out["combined_tilt_removed_height_pkpk_um"]

        fcurv = row.get("front_curvature", np.nan)
        bcurv = row.get("back_curvature", np.nan)
        frms = row.get("front_rms_um", np.nan)
        brms = row.get("back_rms_um", np.nan)

        row["asymmetry"] = float(abs(fcurv - bcurv)) if np.isfinite(fcurv) and np.isfinite(bcurv) else np.nan
        row["front_back_curvature_ratio"] = safe_ratio(fcurv, bcurv)
        row["front_back_rms_diff_um"] = float(abs(frms - brms)) if np.isfinite(frms) and np.isfinite(brms) else np.nan
        row["front_back_rms_ratio"] = safe_ratio(frms, brms)
        row["front_back_repeat_tilt_removed_rms_um"] = float(
            np.sqrt(np.mean(((zf_resid - zb_resid) * MM_TO_UM) ** 2))
        )

        plot_payload["combined"] = {
            "xg": out["_combined_xg"],
            "yg": out["_combined_yg"],
            "curv_map": out["_combined_curv_map"],
            "signed_curv_map": out["_combined_signed_curv_map"],
        }

    return row, plot_payload


# ============================================================
# BATCH SUMMARY
# ============================================================
def build_batch_summary(df):
    if df.empty:
        return pd.DataFrame()

    metric_col = "impact_score" if "impact_score" in df.columns else (
        "combined_curvature" if "combined_curvature" in df.columns else "front_curvature"
    )

    def worst_sample_name(group):
        idx = group[metric_col].idxmax()
        return group.loc[idx, "sample"]

    summary = (
        df.groupby("parent_folder", dropna=False)
        .agg(
            n_samples=("sample", "count"),
            avg_metric=(metric_col, "mean"),
            std_metric=(metric_col, "std"),
            min_metric=(metric_col, "min"),
            max_metric=(metric_col, "max"),
            outlier_count=("is_outlier", "sum"),
        )
        .reset_index()
    )

    worst_names = (
        df.groupby("parent_folder", dropna=False)
        .apply(worst_sample_name)
        .reset_index(name="worst_sample")
    )

    summary = summary.merge(worst_names, on="parent_folder", how="left")
    return summary


# ============================================================
# MAIN
# ============================================================
def main():
    ensure_dirs()

    results = []
    failures = []
    plot_payloads = []

    for p in CSV_PATHS:
        path = Path(p)
        try:
            if not path.exists():
                raise FileNotFoundError(f"File does not exist: {path}")

            print(f"Processing: {path}")
            row, payload = process_csv_file(path)
            results.append(row)
            plot_payloads.append(payload)

        except Exception as e:
            failures.append({
                "file_name": path.name,
                "full_path": str(path),
                "error": str(e),
            })
            print(f"FAILED: {path}")
            print(f"  {e}")

    if not results:
        print("\nNo files were processed successfully.")
        if failures:
            pd.DataFrame(failures).to_csv(OUTPUT_FAIL, index=False)
            print(f"Saved failure log to: {OUTPUT_FAIL}")
        return

    df = pd.DataFrame(results)

    primary_metric = "combined_curvature" if "combined_curvature" in df.columns else (
        "front_curvature" if "front_curvature" in df.columns else "surface_curvature"
    )

    vals = pd.to_numeric(df[primary_metric], errors="coerce")
    mean = vals.mean()
    std = vals.std()

    if np.isfinite(std) and std > 0:
        df["is_outlier"] = np.abs(vals - mean) > 2 * std
    else:
        df["is_outlier"] = False

    def label_curvature(v):
        if not np.isfinite(v):
            return "Unknown"
        if std > 0:
            z = (v - mean) / std
            if z < -0.75:
                return "Low"
            if z < 0.75:
                return "Moderate"
            return "High"
        return "Moderate"

    df["curvature_level"] = [label_curvature(v) for v in vals]

    # ============================================================
    # IMPACT SCORE (curvature + asymmetry)
    # ============================================================
    curv_vals = pd.to_numeric(df.get("combined_curvature"), errors="coerce").fillna(0)
    asym_vals = pd.to_numeric(df.get("asymmetry"), errors="coerce").fillna(0)

    # raw impact score
    df["impact_score"] = curv_vals * (1 + ASYMMETRY_WEIGHT * asym_vals)

    # normalized version
    if curv_vals.max() > 0:
        curv_norm = curv_vals / curv_vals.max()
    else:
        curv_norm = curv_vals

    if asym_vals.max() > 0:
        asym_norm = asym_vals / asym_vals.max()
    else:
        asym_norm = asym_vals

    df["impact_score_normalized"] = curv_norm + ASYMMETRY_WEIGHT * asym_norm

    preferred_cols = [
        "sample",
        "parent_folder",
        "date_folder",
        "file_name",
        "impact_score",
        "impact_score_normalized",
        "combined_curvature",
        "combined_signed_curvature",
        "combined_direction",
        "front_curvature",
        "front_signed_curvature",
        "front_direction",
        "back_curvature",
        "back_signed_curvature",
        "back_direction",
        "asymmetry",
        "front_back_curvature_ratio",
        "front_rms_um",
        "back_rms_um",
        "combined_rms_um",
        "front_back_repeat_tilt_removed_rms_um",
        "curvature_level",
        "is_outlier",
        "full_path",
    ]
    existing_cols = [c for c in preferred_cols if c in df.columns]
    remaining_cols = [c for c in df.columns if c not in existing_cols]

    # sort by impact score highest first
    df = df.sort_values("impact_score", ascending=False).reset_index(drop=True)
    df = df[existing_cols + remaining_cols]

    batch_summary = build_batch_summary(df)

    df.to_csv(OUTPUT_MAIN, index=False)
    batch_summary.to_csv(OUTPUT_BATCH, index=False)

    save_bar_chart(df, BAR_CHART_PATH)

    heatmap_count = 0
    signed_heatmap_count = 0

    for payload in plot_payloads:
        sample = sanitize_name(payload["sample"])
        date_folder = sanitize_name(payload["date_folder"])
        base = f"{sample}_{date_folder}"

        if payload["front"] is not None:
            save_heatmap(
                payload["front"]["xg"],
                payload["front"]["yg"],
                payload["front"]["curv_map"],
                f"{payload['sample']} - Front Curvature Magnitude",
                HEATMAP_DIR / f"{base}_front_curvature_heatmap.png",
            )
            heatmap_count += 1

            save_signed_heatmap(
                payload["front"]["xg"],
                payload["front"]["yg"],
                payload["front"]["signed_curv_map"],
                f"{payload['sample']} - Front Signed Curvature",
                SIGNED_HEATMAP_DIR / f"{base}_front_signed_curvature_heatmap.png",
            )
            signed_heatmap_count += 1

        if payload["back"] is not None:
            save_heatmap(
                payload["back"]["xg"],
                payload["back"]["yg"],
                payload["back"]["curv_map"],
                f"{payload['sample']} - Back Curvature Magnitude",
                HEATMAP_DIR / f"{base}_back_curvature_heatmap.png",
            )
            heatmap_count += 1

            save_signed_heatmap(
                payload["back"]["xg"],
                payload["back"]["yg"],
                payload["back"]["signed_curv_map"],
                f"{payload['sample']} - Back Signed Curvature",
                SIGNED_HEATMAP_DIR / f"{base}_back_signed_curvature_heatmap.png",
            )
            signed_heatmap_count += 1

        if payload["combined"] is not None:
            save_heatmap(
                payload["combined"]["xg"],
                payload["combined"]["yg"],
                payload["combined"]["curv_map"],
                f"{payload['sample']} - Combined Curvature Magnitude",
                HEATMAP_DIR / f"{base}_combined_curvature_heatmap.png",
            )
            heatmap_count += 1

            save_signed_heatmap(
                payload["combined"]["xg"],
                payload["combined"]["yg"],
                payload["combined"]["signed_curv_map"],
                f"{payload['sample']} - Combined Signed Curvature",
                SIGNED_HEATMAP_DIR / f"{base}_combined_signed_curvature_heatmap.png",
            )
            signed_heatmap_count += 1

    if failures:
        pd.DataFrame(failures).to_csv(OUTPUT_FAIL, index=False)

    print(f"\nSaved sample summary: {OUTPUT_MAIN}")
    print(f"Saved batch summary:  {OUTPUT_BATCH}")
    print(f"Saved bar chart:      {BAR_CHART_PATH}")
    print(f"Saved magnitude heatmaps in: {HEATMAP_DIR}")
    print(f"Saved signed heatmaps in:    {SIGNED_HEATMAP_DIR}")
    print(f"Magnitude heatmaps created:  {heatmap_count}")
    print(f"Signed heatmaps created:     {signed_heatmap_count}")

    if failures:
        print(f"Saved failures:       {OUTPUT_FAIL}")

    print("\nPreview:")
    preview_cols = [c for c in [
        "sample",
        "impact_score",
        "impact_score_normalized",
        "combined_curvature",
        "combined_signed_curvature",
        "combined_direction",
        "front_curvature",
        "front_signed_curvature",
        "front_direction",
        "back_curvature",
        "back_signed_curvature",
        "back_direction",
        "asymmetry",
        "front_rms_um",
        "back_rms_um",
        "curvature_level",
        "is_outlier",
    ] if c in df.columns]
    print(df[preview_cols].to_string(index=False))


if __name__ == "__main__":
    main()
