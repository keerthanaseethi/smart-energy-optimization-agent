# ==================================================
# Context-Aware Energy Mismatch Detector
# ==================================================

import pandas as pd
from pathlib import Path


INPUT_FILE = Path(
    "data/simulated/campus_context.csv"
)

OUTPUT_FILE = Path(
    "data/simulated/mismatches.csv"
)


# --------------------------------------------------
# Prototype demand thresholds
# --------------------------------------------------

NORMAL_DEMAND_THRESHOLD_MW = 2.0
HIGH_DEMAND_THRESHOLD_MW = 2.5


class MismatchDetector:

    def __init__(
        self,
        normal_threshold=NORMAL_DEMAND_THRESHOLD_MW,
        high_threshold=HIGH_DEMAND_THRESHOLD_MW
    ):

        self.normal_threshold = normal_threshold
        self.high_threshold = high_threshold

    # --------------------------------------------------
    # Classify demand
    # --------------------------------------------------

    def classify_demand(self, demand):

        if demand >= self.high_threshold:
            return "HIGH"

        if demand >= self.normal_threshold:
            return "ELEVATED"

        return "NORMAL"

    # --------------------------------------------------
    # Detect mismatch
    # --------------------------------------------------

    def detect(self, row):

        # --------------------------------------------------
        # Read normalized source columns
        # --------------------------------------------------

        demand = float(
            row["reference_system_demand_MW"]
        )

        occupancy = float(
            row["academic_occupancy"]
        )

        schedule = int(
            row["academic_schedule"]
        )

        hvac = row[
            "academic_hvac"
        ]

        lighting = row[
            "academic_lighting"
        ]

        ev = row[
            "ev_charging"
        ]

        tariff = row[
            "tariff"
        ]

        # --------------------------------------------------
        # Demand classification
        # --------------------------------------------------

        demand_level = self.classify_demand(
            demand
        )

        # --------------------------------------------------
        # HVAC mismatch
        # --------------------------------------------------

        if (
            hvac == "ON"
            and occupancy <= 10
            and schedule == 0
        ):

            return {

                "type":
                    "HVAC_MISMATCH",

                "severity":
                    "High",

                "reason":
                    "Academic HVAC is operating "
                    "during an unscheduled period "
                    "with very low occupancy.",

                "demand_level":
                    demand_level
            }

        # --------------------------------------------------
        # Lighting mismatch
        # --------------------------------------------------

        if (
            lighting == "ON"
            and occupancy <= 10
        ):

            return {

                "type":
                    "LIGHTING_MISMATCH",

                "severity":
                    "Medium",

                "reason":
                    "Academic lighting is operating "
                    "while occupancy is very low.",

                "demand_level":
                    demand_level
            }

        # --------------------------------------------------
        # EV peak mismatch
        # --------------------------------------------------

        if (
            ev == "ON"
            and tariff == "Peak"
            and demand_level in [
                "ELEVATED",
                "HIGH"
            ]
        ):

            return {

                "type":
                    "EV_PEAK",

                "severity":
                    "Medium",

                "reason":
                    "EV charging is operating during "
                    "a peak-tariff period while the "
                    "reference demand is elevated.",

                "demand_level":
                    demand_level
            }

        # --------------------------------------------------
        # No actionable mismatch
        # --------------------------------------------------

        return {

            "type":
                "NORMAL",

            "severity":
                "None",

            "reason":
                "No actionable energy mismatch "
                "was detected.",

            "demand_level":
                demand_level
        }


# ==================================================
# Normalize input data
# ==================================================

def normalize_columns(df):

    """
    Convert the simulation dataset into the
    internal column names expected by the detector.

    This prevents individual KeyError problems when
    source-column names differ from agent-state names.
    """

    rename_map = {

        "Tariff":
            "tariff",

        "reference_system_demand_MW":
            "reference_system_demand_MW",

        "academic_occupancy":
            "academic_occupancy",

        "academic_schedule":
            "academic_schedule",

        "academic_hvac":
            "academic_hvac",

        "academic_lighting":
            "academic_lighting",

        "ev_charging":
            "ev_charging",
    }

    df = df.rename(
        columns=rename_map
    )

    required_columns = [

        "reference_system_demand_MW",
        "academic_occupancy",
        "academic_schedule",
        "academic_hvac",
        "academic_lighting",
        "ev_charging",
        "tariff",
    ]

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:

        raise ValueError(
            "Missing required columns in "
            f"{INPUT_FILE}: {missing}\n\n"
            f"Available columns: "
            f"{df.columns.tolist()}"
        )

    return df


# ==================================================
# Standalone analysis
# ==================================================

if __name__ == "__main__":

    print("=" * 65)
    print("CONTEXT-AWARE MISMATCH DETECTOR")
    print("=" * 65)

    print()

    print(
        f"Reading: {INPUT_FILE}"
    )

    df = pd.read_csv(
        INPUT_FILE
    )

    print(
        f"Input rows: {len(df)}"
    )

    print()

    # --------------------------------------------------
    # Normalize schema
    # --------------------------------------------------

    df = normalize_columns(
        df
    )

    detector = MismatchDetector()

    mismatches = []

    # --------------------------------------------------
    # Analyze every observation
    # --------------------------------------------------

    for _, row in df.iterrows():

        result = detector.detect(
            row
        )

        mismatches.append({

            "Datetime":
                row["Datetime"],

            "Reference_Demand_MW":
                row[
                    "reference_system_demand_MW"
                ],

            "Demand_Level":
                result[
                    "demand_level"
                ],

            "Occupancy":
                row[
                    "academic_occupancy"
                ],

            "Tariff":
                row[
                    "tariff"
                ],

            "Mismatch_Type":
                result[
                    "type"
                ],

            "Severity":
                result[
                    "severity"
                ],

            "Reason":
                result[
                    "reason"
                ]
        })

    result_df = pd.DataFrame(
        mismatches
    )

    # --------------------------------------------------
    # Save output
    # --------------------------------------------------

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    result_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # --------------------------------------------------
    # Summary
    # --------------------------------------------------

    print(
        f"Processed rows: "
        f"{len(result_df)}"
    )

    print()

    print(
        "Mismatch distribution:"
    )

    print(
        result_df[
            "Mismatch_Type"
        ].value_counts()
    )

    print()

    print(
        "Severity distribution:"
    )

    print(
        result_df[
            "Severity"
        ].value_counts()
    )

    print()

    print(
        "Demand level distribution:"
    )

    print(
        result_df[
            "Demand_Level"
        ].value_counts()
    )

    print()

    print(
        f"Output saved to: "
        f"{OUTPUT_FILE}"
    )

    print()

    print("=" * 65)
    print(
        "MISMATCH ANALYSIS COMPLETED"
    )
    print("=" * 65)