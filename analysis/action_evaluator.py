import pandas as pd
from pathlib import Path


# --------------------------------------------------
# File paths
# --------------------------------------------------

INPUT_FILE = Path("data/simulated/campus_context.csv")
OUTPUT_FILE = Path("data/simulated/action_evaluations.csv")


# --------------------------------------------------
# Load campus context
# --------------------------------------------------

df = pd.read_csv(INPUT_FILE)

df["Datetime"] = pd.to_datetime(df["Datetime"])


# --------------------------------------------------
# Simple estimated load contributions
# --------------------------------------------------

# These are prototype assumptions, not real campus
# equipment measurements.

HVAC_LOAD_MW = 0.8
LIGHTING_LOAD_MW = 0.3
EV_LOAD_MW = 1.2


# --------------------------------------------------
# Evaluate an action
# --------------------------------------------------

def evaluate_action(row, action):

    current_demand = row["reference_system_demand_MW"]

    estimated_saving = 0.0
    action_description = action

    if action == "Reduce Academic HVAC":

        if row["academic_hvac"] == "ON":
            estimated_saving = HVAC_LOAD_MW * 0.5
        else:
            estimated_saving = 0.0

    elif action == "Turn Academic Lighting OFF":

        if row["academic_lighting"] == "ON":
            estimated_saving = LIGHTING_LOAD_MW
        else:
            estimated_saving = 0.0

    elif action == "Shift EV Charging":

        if row["ev_charging"] == "ON":
            estimated_saving = EV_LOAD_MW
        else:
            estimated_saving = 0.0

    elif action == "Do Nothing":

        estimated_saving = 0.0

    new_demand = current_demand - estimated_saving

    return {
        "Datetime": row["Datetime"],
        "Action": action,
        "Current_Demand_MW": current_demand,
        "Estimated_Saving_MW": estimated_saving,
        "Estimated_Demand_After_Action_MW": new_demand,
        "Action_Useful": estimated_saving > 0,
        "Action_Description": action_description,
    }


# --------------------------------------------------
# Evaluate actions for detected mismatch situations
# --------------------------------------------------

actions = [
    "Do Nothing",
    "Reduce Academic HVAC",
    "Turn Academic Lighting OFF",
    "Shift EV Charging",
]


results = []


for _, row in df.iterrows():

    # Only evaluate rows where an actionable
    # situation exists.

    hvac_mismatch = (
        row["academic_schedule"] == 0
        and row["academic_occupancy"] <= 10
        and row["academic_hvac"] == "ON"
    )

    lighting_mismatch = (
        row["academic_occupancy"] <= 10
        and row["academic_lighting"] == "ON"
    )

    ev_opportunity = (
        row["ev_charging"] == "ON"
        and row["tariff"] == "Peak"
    )

    if hvac_mismatch:

        result = evaluate_action(
            row,
            "Reduce Academic HVAC"
        )

        results.append(result)

    elif lighting_mismatch:

        result = evaluate_action(
            row,
            "Turn Academic Lighting OFF"
        )

        results.append(result)

    elif ev_opportunity:

        result = evaluate_action(
            row,
            "Shift EV Charging"
        )

        results.append(result)


# --------------------------------------------------
# Save results
# --------------------------------------------------

result_df = pd.DataFrame(results)

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)

result_df.to_csv(
    OUTPUT_FILE,
    index=False
)


# --------------------------------------------------
# Print summary
# --------------------------------------------------

print("Action evaluation completed successfully.")
print()

print(f"Action evaluations: {len(result_df)}")

print()

if len(result_df) > 0:

    print("Action breakdown:")
    print(
        result_df["Action"]
        .value_counts()
    )

    print()

    print("Estimated impact:")
    print(
        result_df[
            [
                "Action",
                "Estimated_Saving_MW",
                "Estimated_Demand_After_Action_MW",
            ]
        ]
        .head(10)
        .to_string(index=False)
    )

else:

    print("No actionable situations found.")

print()
print(f"Output saved to: {OUTPUT_FILE}")