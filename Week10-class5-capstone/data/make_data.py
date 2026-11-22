import pandas as pd
from datetime import datetime, timedelta

wells = ["WELL-A", "WELL-B", "WELL-C"]
rows = []
start = datetime(2026, 11, 1, 0, 0)

# 3 wells x 4 days x 4 slots (6h) = 48 base rows
for well in wells:
    for i in range(16):
        ts = start + timedelta(hours=6*i)
        rows.append({
            "well_id": well,
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "oil_bbl": 100 + i*2,
            "water_bbl": 50 + i,
            "gas_mscf": 200 + i*3,
            "pressure_psi": 1500 - i*5,
            "status": "PRODUCING",
            "ingested_at": "2026-11-05 08:00:00"
        })

df = pd.DataFrame(rows)

# Remove 4 gaps (missing slots)
df = df.drop([5, 20, 33, 44]).reset_index(drop=True)

# Add 1 duplicate: same well+timestamp as row 0, but later ingested_at, oil=999 (should win)
dup = df.iloc[0].copy()
dup["oil_bbl"] = 999
dup["ingested_at"] = "2026-11-05 09:00:00"
df = pd.concat([df, pd.DataFrame([dup])], ignore_index=True)

# Add 1 invalid timestamp row (should be rejected)
bad = df.iloc[0].copy()
bad["timestamp"] = "not-a-date"
bad["well_id"] = "WELL-A"
df = pd.concat([df, pd.DataFrame([bad])], ignore_index=True)

df.to_csv("data/historical_production_capstone.csv", index=False)
print(f"Created {len(df)} rows")
print(df.head())