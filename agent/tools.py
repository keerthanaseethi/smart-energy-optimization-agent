from simulation.devices import VirtualCampus


# --------------------------------------------------
# Create the virtual campus
# --------------------------------------------------

campus = VirtualCampus()


# --------------------------------------------------
# HVAC control
# --------------------------------------------------

def reduce_academic_hvac():

    previous_state = campus.hvac.state

    message = campus.hvac.set_eco()

    return {
        "action": "Reduce Academic HVAC",
        "status": "SUCCESS",
        "previous_state": previous_state,
        "new_state": campus.hvac.state,
        "message": message,
    }


def turn_academic_hvac_off():

    previous_state = campus.hvac.state

    message = campus.hvac.turn_off()

    return {
        "action": "Turn Academic HVAC OFF",
        "status": "SUCCESS",
        "previous_state": previous_state,
        "new_state": campus.hvac.state,
        "message": message,
    }


# --------------------------------------------------
# Lighting control
# --------------------------------------------------

def turn_academic_lighting_off():

    previous_state = campus.lighting.state

    message = campus.lighting.turn_off()

    return {
        "action": "Turn Academic Lighting OFF",
        "status": "SUCCESS",
        "previous_state": previous_state,
        "new_state": campus.lighting.state,
        "message": message,
    }


# --------------------------------------------------
# EV charging control
# --------------------------------------------------

def shift_ev_charging():

    previous_state = campus.ev_charger.state

    message = campus.ev_charger.shift_charging()

    return {
        "action": "Shift EV Charging",
        "status": "SUCCESS",
        "previous_state": previous_state,
        "new_state": campus.ev_charger.state,
        "message": message,
    }


# --------------------------------------------------
# Get current campus state
# --------------------------------------------------

def get_campus_state():

    return campus.get_state()


# --------------------------------------------------
# Test execution tools
# --------------------------------------------------

if __name__ == "__main__":

    print("Initial campus state:")
    print(get_campus_state())

    print()

    result = reduce_academic_hvac()

    print("Execution result:")
    print(result)

    print()

    print("Campus state after execution:")
    print(get_campus_state())