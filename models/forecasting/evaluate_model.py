import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from xgboost import XGBRegressor


# --------------------------------------------------
# File paths
# --------------------------------------------------

INPUT_FILE = Path("data/processed/AEP_features.csv")
MODEL_FILE = Path("models/saved/energy_forecast_model.json")


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
# Same 80/20 time-based split
# --------------------------------------------------

split_index = int(len(df) * 0.8)

X_test = df[features].iloc[split_index:]
y_test = df[target].iloc[split_index:]
dates_test = df["Datetime"].iloc[split_index:]


# --------------------------------------------------
# Load trained model
# --------------------------------------------------

model = XGBRegressor()
model.load_model(MODEL_FILE)


# --------------------------------------------------
# Generate predictions
# --------------------------------------------------

predictions = model.predict(X_test)


# --------------------------------------------------
# Plot actual vs predicted
# --------------------------------------------------

plt.figure(figsize=(14, 6))

plt.plot(
    dates_test,
    y_test,
    label="Actual Demand"
)

plt.plot(
    dates_test,
    predictions,
    label="Predicted Demand"
)

plt.xlabel("Date")
plt.ylabel("Demand (MW)")
plt.title("Actual vs Predicted Energy Demand")
plt.legend()
plt.tight_layout()

plt.show()