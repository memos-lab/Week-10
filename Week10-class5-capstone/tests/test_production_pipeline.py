from pathlib import Path
import pandas as pd
from src.production_pipeline import ingest_and_validate, repair_and_align, summarize_daily, run_pipeline

CSV = "data/historical_production_capstone.csv"

def test_ingest_splits_valid_and_rejected():
    valid, rejected = ingest_and_validate(CSV)
    assert len(valid) == 45
    assert len(rejected) == 1
    assert "rejection_reason" in rejected.columns

def test_repair_dedup_and_gaps():
    valid, _ = ingest_and_validate(CSV)
    cleaned, quality = repair_and_align(valid)
    assert len(cleaned) == 48
    assert quality.attrs["total_gaps_created"] == 4
    # duplicate kept last: oil should be 999 for first slot of WELL-A
    first = cleaned[(cleaned.well_id=="WELL-A")].sort_values("timestamp").iloc[0]
    assert first["oil_bbl"] == 999

def test_daily_summary():
    valid, _ = ingest_and_validate(CSV)
    cleaned, _ = repair_and_align(valid)
    daily = summarize_daily(cleaned)
    assert len(daily) == 12  # 3 wells x 4 days
    assert set(daily.columns) >= {"well_id","date","oil_bbl","completeness_oil"}

def test_run_pipeline_creates_outputs(tmp_path):
    run_pipeline(CSV, tmp_path)
    for f in ["cleaned_production.csv","data_quality_report.csv","daily_production_summary.csv","rejected_source_records.csv"]:
        assert (tmp_path / f).exists()