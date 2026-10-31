import pandas as pd
import numpy as np
from pathlib import Path
from xgboost import XGBRegressor


# --------------------------------------------------
# File paths
# --------------------------------------------------

INPUT_FILE = Path("data/processed/AEP_features.csv")
MODEL_FILE = Path("models/saved/energy_forecast_model.json")
OUTPUT_FILE = Path("data/processed/AEP_opportunities.csv")


# --------------------------------------------------
# Load data
# --------------------------------------------------

df = pd.read_csv(INPUT_FILE)

df["Datetime"] = pd.to_datetime(df["Datetime"])
df = df.sort_values("Datetime").reset_index(drop=True)


# --------------------------------------------------
# Forecasting features
# --------------------------------------------------

features = [
    "year",
    "month",
    "day",
    "hour",
    "day_of_week",
    "is_weekend",
    "lag_1h",
    "lag_24h",
    "lag_168h",
    "rolling_24h",
    "rolling_7d",
]

target = "AEP_MW"


# --------------------------------------------------
# Use the same test period as model evaluation
# --------------------------------------------------

split_index = int(len(df) * 0.8)

test_df = df.iloc[split_index:].copy()

X_test = test_df[features]


# --------------------------------------------------
# Load forecasting model
# --------------------------------------------------

model = XGBRegressor()
model.load_model(MODEL_FILE)


# --------------------------------------------------
# Predict expected demand
# --------------------------------------------------

test_df["expected_MW"] = model.predict(X_test)


# --------------------------------------------------
# Calculate deviation
# --------------------------------------------------

test_df["deviation_MW"] = (
    test_df["AEP_MW"] - test_df["expected_MW"]
)

test_df["deviation_percent"] = (
    test_df["deviation_MW"]
    / test_df["expected_MW"]
) * 100


# --------------------------------------------------
# Detect potential opportunities
# --------------------------------------------------

# More than 5% above expected demand
test_df["potential_opportunity"] = (
    test_df["deviation_percent"] > 5
)


# --------------------------------------------------
# Assign severity
# --------------------------------------------------

def get_severity(deviation):
    if deviation > 15:
        return "High"
    elif deviation > 10:
        return "Medium"
    elif deviation > 5:
        return "Low"
    else:
        return "Normal"


test_df["severity"] = test_df["deviation_percent"].apply(
    get_severity
)


# --------------------------------------------------
# Save results
# --------------------------------------------------

result_columns = [
    "Datetime",
    "AEP_MW",
    "expected_MW",
    "deviation_MW",
    "deviation_percent",
    "potential_opportunity",
    "severity",
]

result = test_df[result_columns]

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
result.to_csv(OUTPUT_FILE, index=False)


# --------------------------------------------------
# Summary
# --------------------------------------------------

opportunities = result[
    result["potential_opportunity"]
]

print("Opportunity detection completed successfully.")
print()
print(f"Total test records: {len(result)}")
print(f"Potential opportunities: {len(opportunities)}")
print(
    f"Opportunity rate: "
    f"{len(opportunities) / len(result) * 100:.2f}%"
)

print()
print("Severity breakdown:")
print(result["severity"].value_counts())

print()
print("Top 10 potential opportunities:")
print(
    opportunities
    .sort_values("deviation_percent", ascending=False)
    .head(10)
    .to_string(index=False)
)

print()
print(f"Output saved to: {OUTPUT_FILE}")