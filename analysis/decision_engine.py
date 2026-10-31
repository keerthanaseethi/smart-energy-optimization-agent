import pandas as pd
from pathlib import Path


# --------------------------------------------------
# File paths
# --------------------------------------------------

INPUT_FILE = Path("data/simulated/campus_context.csv")
OUTPUT_FILE = Path("data/simulated/agent_decisions.csv")


# --------------------------------------------------
# Prototype load assumptions
# --------------------------------------------------

HVAC_LOAD_MW = 0.8
LIGHTING_LOAD_MW = 0.3
EV_LOAD_MW = 1.2


# --------------------------------------------------
# Load campus context
# --------------------------------------------------

df = pd.read_csv(INPUT_FILE)

df["Datetime"] = pd.to_datetime(df["Datetime"])

df = df.sort_values("Datetime").reset_index(drop=True)


# --------------------------------------------------
# Generate candidate actions
# --------------------------------------------------

def generate_candidates(row):

    candidates = [
        {
            "action": "Do Nothing",
            "saving_MW": 0.0,
            "operational_impact": 0.0,
        }
    ]

    # Academic HVAC
    if (
        row["academic_hvac"] == "ON"
        and row["academic_occupancy"] <= 10
    ):
        candidates.append({
            "action": "Reduce Academic HVAC",
            "saving_MW": HVAC_LOAD_MW * 0.5,
            "operational_impact": 1.0,
        })

        candidates.append({
            "action": "Turn Academic HVAC OFF",
            "saving_MW": HVAC_LOAD_MW,
            "operational_impact": 2.0,
        })

    # Academic lighting
    if (
        row["academic_lighting"] == "ON"
        and row["academic_occupancy"] <= 10
    ):
        candidates.append({
            "action": "Turn Academic Lighting OFF",
            "saving_MW": LIGHTING_LOAD_MW,
            "operational_impact": 0.5,
        })

    # EV charging
    if (
        row["ev_charging"] == "ON"
        and row["tariff"] == "Peak"
    ):
        candidates.append({
            "action": "Shift EV Charging",
            "saving_MW": EV_LOAD_MW,
            "operational_impact": 0.5,
        })

    return candidates


# --------------------------------------------------
# Select best action
# --------------------------------------------------

def select_best_action(candidates):

    # Score balances energy saving against
    # operational impact.

    for candidate in candidates:

        candidate["score"] = (
            candidate["saving_MW"]
            - 0.2 * candidate["operational_impact"]
        )

    best = max(
        candidates,
        key=lambda x: x["score"]
    )

    return best


# --------------------------------------------------
# Process the campus state
# --------------------------------------------------

decisions = []


for _, row in df.iterrows():

    candidates = generate_candidates(row)

    best_action = select_best_action(candidates)

    current_demand = row["reference_system_demand_MW"]

    demand_after = (
        current_demand
        - best_action["saving_MW"]
    )

    decisions.append({
        "Datetime": row["Datetime"],
        "Current_Demand_MW": current_demand,
        "Occupancy": max(
            row["academic_occupancy"],
            row["residential_occupancy"]
        ),
        "Tariff": row["tariff"],
        "Selected_Action": best_action["action"],
        "Estimated_Saving_MW": best_action["saving_MW"],
        "Estimated_Demand_After_Action_MW": demand_after,
        "Decision_Score": best_action["score"],
    })


# --------------------------------------------------
# Save decisions
# --------------------------------------------------

decision_df = pd.DataFrame(decisions)

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)

decision_df.to_csv(
    OUTPUT_FILE,
    index=False
)


# --------------------------------------------------
# Summary
# --------------------------------------------------

print("Action decision engine completed successfully.")
print()

print(f"Total decisions evaluated: {len(decision_df)}")

print()
print("Selected action breakdown:")
print(
    decision_df["Selected_Action"]
    .value_counts()
)

print()

print("Non-trivial decisions:")

non_trivial = decision_df[
    decision_df["Selected_Action"] != "Do Nothing"
]

if len(non_trivial) > 0:

    print(
        non_trivial[
            [
                "Datetime",
                "Current_Demand_MW",
                "Tariff",
                "Selected_Action",
                "Estimated_Saving_MW",
                "Estimated_Demand_After_Action_MW",
            ]
        ]
        .head(15)
        .to_string(index=False)
    )

else:

    print("No actions selected.")

print()
print(f"Output saved to: {OUTPUT_FILE}")