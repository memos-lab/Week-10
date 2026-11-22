from pathlib import Path
import pandas as pd
import numpy as np

EXPECTED_COLUMNS = ["well_id", "timestamp", "oil_bbl", "water_bbl", "gas_mscf", "pressure_psi", "status", "ingested_at"]

def ingest_and_validate(path: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.read_csv(path)
    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    df = df.copy()
    df["_timestamp_raw"] = df["timestamp"].astype(str)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["ingested_at"] = pd.to_datetime(df["ingested_at"], errors="coerce")
    rejected = df[df["timestamp"].isna()].copy()
    valid = df[df["timestamp"].notna()].copy()
    if len(rejected) > 0:
        rejected["rejection_reason"] = "invalid_timestamp: unparseable timestamp value"
        rejected["timestamp"] = rejected["_timestamp_raw"]
    valid = valid.drop(columns=["_timestamp_raw"])
    rejected = rejected.drop(columns=["_timestamp_raw"], errors="ignore")
    return valid, rejected

def repair_and_align(valid_rows: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = valid_rows.copy()
    df = df.sort_values(["well_id", "timestamp", "ingested_at"])
    before = len(df)
    df = df.drop_duplicates(subset=["well_id", "timestamp"], keep="last")
    duplicates_removed = before - len(df)
    numeric_cols = ["oil_bbl", "water_bbl", "gas_mscf", "pressure_psi"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        df.loc[df[col] < 0, col] = np.nan
    aligned = []
    gap_count = 0
    for well, group in df.groupby("well_id"):
        group = group.sort_values("timestamp").set_index("timestamp")
        start = group.index.min().floor("6h")
        end = group.index.max().ceil("6h")
        full_index = pd.date_range(start=start, end=end, freq="6h")
        gap_count += len(full_index) - len(group)
        reindexed = group.reindex(full_index)
        reindexed["well_id"] = well
        reindexed["pressure_psi"] = reindexed["pressure_psi"].interpolate(method="linear", limit=1, limit_area="inside")
        reindexed = reindexed.reset_index().rename(columns={"index": "timestamp"})
        aligned.append(reindexed)
    cleaned = pd.concat(aligned, ignore_index=True)
    cleaned = cleaned.sort_values(["well_id", "timestamp"]).reset_index(drop=True)
    cols = ["well_id", "timestamp", "oil_bbl", "water_bbl", "gas_mscf", "pressure_psi", "status", "ingested_at"]
    cleaned = cleaned[[c for c in cols if c in cleaned.columns]]
    rows = []
    for well, g in cleaned.groupby("well_id"):
        rows.append({
            "well_id": well,
            "cleaned_rows": len(g),
            "duplicates_removed_total": duplicates_removed,
            "missing_oil": int(g["oil_bbl"].isna().sum()),
            "missing_water": int(g["water_bbl"].isna().sum()),
            "missing_gas": int(g["gas_mscf"].isna().sum()),
            "missing_pressure": int(g["pressure_psi"].isna().sum()),
        })
    quality = pd.DataFrame(rows)
    quality.attrs["total_gaps_created"] = gap_count
    return cleaned, quality

def summarize_daily(cleaned_rows: pd.DataFrame) -> pd.DataFrame:
    df = cleaned_rows.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["date"] = df["timestamp"].dt.date
    daily = df.groupby(["well_id", "date"]).agg(
        oil_bbl=("oil_bbl", lambda x: x.sum(min_count=1)),
        water_bbl=("water_bbl", lambda x: x.sum(min_count=1)),
        gas_mscf=("gas_mscf", lambda x: x.sum(min_count=1)),
        pressure_psi_mean=("pressure_psi", "mean"),
        expected_slots=("oil_bbl", "size"),
        observed_oil_slots=("oil_bbl", "count"),
        observed_water_slots=("water_bbl", "count"),
        observed_gas_slots=("gas_mscf", "count"),
    ).reset_index()
    daily["completeness_oil"] = daily["observed_oil_slots"] / daily["expected_slots"]
    return daily

def run_pipeline(input_csv: str | Path, output_dir: str | Path) -> None:
    input_path = Path(input_csv)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    valid, rejected = ingest_and_validate(input_path)
    cleaned, quality = repair_and_align(valid)
    daily = summarize_daily(cleaned)
    total_gaps = quality.attrs.get("total_gaps_created", 0)
    cleaned.to_csv(out_dir / "cleaned_production.csv", index=False)
    quality_out = quality.copy()
    quality_out["total_gap_count"] = total_gaps
    quality_out.to_csv(out_dir / "data_quality_report.csv", index=False)
    daily.to_csv(out_dir / "daily_production_summary.csv", index=False)
    rejected.to_csv(out_dir / "rejected_source_records.csv", index=False)
    print(f"Valid: {len(valid)} Rejected: {len(rejected)} Cleaned: {len(cleaned)} Daily: {len(daily)} Gaps: {total_gaps}")