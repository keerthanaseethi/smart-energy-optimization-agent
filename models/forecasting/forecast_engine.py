# ==================================================
# Energy Forecast Engine
# ==================================================

import pandas as pd
from pathlib import Path
from xgboost import XGBRegressor
from data.provenance import attach_provenance, make_provenance


MODEL_FILE = Path(
    "models/saved/energy_forecast_model.json"
)

FEATURE_FILE = Path(
    "data/processed/AEP_features.csv"
)


MODEL_FEATURES = [
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


class ForecastEngine:

    def __init__(
        self,
        model_file=MODEL_FILE,
        feature_file=FEATURE_FILE
    ):

        self.model_file = Path(
            model_file
        )

        self.feature_file = Path(
            feature_file
        )

        self.model = self.load_model()

        self.data = self.load_feature_data()

    # --------------------------------------------------
    # Load trained model
    # --------------------------------------------------

    def load_model(self):

        if not self.model_file.exists():

            raise FileNotFoundError(
                f"Forecast model not found: "
                f"{self.model_file}"
            )

        model = XGBRegressor()

        model.load_model(
            self.model_file
        )

        return model

    # --------------------------------------------------
    # Load feature data
    # --------------------------------------------------

    def load_feature_data(self):

        if not self.feature_file.exists():

            raise FileNotFoundError(
                f"Feature file not found: "
                f"{self.feature_file}"
            )

        df = pd.read_csv(
            self.feature_file
        )

        df["Datetime"] = pd.to_datetime(
            df["Datetime"]
        )

        df = (
            df
            .sort_values("Datetime")
            .reset_index(drop=True)
        )

        attach_provenance(
            df,
            make_provenance(
                "DERIVED",
                "AEP feature preparation",
                str(self.feature_file),
                data_timestamp_start=df["Datetime"].min().isoformat(),
                data_timestamp_end=df["Datetime"].max().isoformat(),
                units={
                    "AEP_MW": "MW",
                    "lag_1h": "MW",
                    "lag_24h": "MW",
                    "lag_168h": "MW",
                    "rolling_24h": "MW",
                    "rolling_7d": "MW",
                },
                geographic_scope="inherited regional/grid-level AEP scope; not campus telemetry",
                semantic_description="Derived forecasting features loaded from the AEP feature artifact.",
                transformation="feature artifact loaded without changing model feature definitions",
                lineage=[
                    {
                        "provenance_class": "REAL_HISTORICAL",
                        "source_provider": "AEP",
                        "source_identifier": "data/raw/AEP_hourly.csv",
                        "semantic_description": "Regional/grid-level demand; not campus telemetry",
                    }
                ],
            ),
        )

        return df

    # --------------------------------------------------
    # Find timestamp
    # --------------------------------------------------

    def find_timestamp(
        self,
        timestamp
    ):

        timestamp = pd.Timestamp(
            timestamp
        )

        matches = self.data[
            self.data["Datetime"]
            == timestamp
        ]

        if matches.empty:

            raise ValueError(
                f"Timestamp not found in "
                f"forecast feature data: "
                f"{timestamp}"
            )

        return matches.iloc[0]

    # --------------------------------------------------
    # Forecast one hour ahead
    # --------------------------------------------------

    def forecast_next_hour(
        self,
        current_timestamp
    ):

        current_timestamp = pd.Timestamp(
            current_timestamp
        )

        target_timestamp = (
            current_timestamp
            + pd.Timedelta(hours=1)
        )

        # --------------------------------------------------
        # Find the target row.
        #
        # Its feature columns contain lagged historical
        # information and rolling statistics, while the
        # target AEP_MW is NOT supplied to the model.
        # --------------------------------------------------

        target_rows = self.data[
            self.data["Datetime"]
            == target_timestamp
        ]

        if target_rows.empty:

            raise ValueError(
                f"Next-hour timestamp not found: "
                f"{target_timestamp}"
            )

        target_row = (
            target_rows.iloc[0]
        )

        X = pd.DataFrame(
            [target_row[
                MODEL_FEATURES
            ].values],
            columns=MODEL_FEATURES
        )

        prediction = (
            self.model.predict(X)[0]
        )

        forecast = {

            "forecast_timestamp":
                target_timestamp,

            "forecast_MW":
                float(prediction),

            "actual_MW":
                float(
                    target_row["AEP_MW"]
                ),
        }
        forecast["Provenance_Metadata"] = make_provenance(
            "DERIVED",
            "ForecastEngine",
            str(self.model_file),
            data_timestamp_start=target_timestamp.isoformat(),
            data_timestamp_end=target_timestamp.isoformat(),
            units={"forecast_MW": "MW", "actual_MW": "MW"},
            geographic_scope="regional/grid-level forecast semantics inherited from AEP; not campus telemetry",
            semantic_description="One-hour-ahead derived forecast from the existing AEP-trained XGBoost model.",
            transformation="XGBoost prediction using existing MODEL_FEATURES; weather excluded",
            lineage=[self.data.attrs["provenance"]],
        )
        return forecast

    # --------------------------------------------------
    # Forecast from a dataset row
    # --------------------------------------------------

    def forecast_from_row(
        self,
        row
    ):

        return self.forecast_next_hour(
            row["Datetime"]
        )


# ==================================================
# Standalone test
# ==================================================

if __name__ == "__main__":

    engine = ForecastEngine()

    test_timestamp = (
        "2017-03-15 18:00:00"
    )

    result = engine.forecast_next_hour(
        test_timestamp
    )

    print("=" * 65)
    print("ENERGY FORECAST ENGINE")
    print("=" * 65)

    print()

    print(
        f"Current time: "
        f"{test_timestamp}"
    )

    print(
        f"Forecast time: "
        f"{result['forecast_timestamp']}"
    )

    print()

    print(
        f"Forecast demand: "
        f"{result['forecast_MW']:.2f} MW"
    )

    print(
        f"Actual demand: "
        f"{result['actual_MW']:.2f} MW"
    )

    forecast_error = (
        result["actual_MW"]
        - result["forecast_MW"]
    )

    print(
        f"Forecast error: "
        f"{forecast_error:.2f} MW"
    )

    print()

    print("=" * 65)
    print("FORECAST ENGINE TEST COMPLETED")
    print("=" * 65)