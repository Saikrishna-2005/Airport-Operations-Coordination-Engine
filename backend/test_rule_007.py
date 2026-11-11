from app.rule_engine.schemas import (
    OperationalInput,
    StaffAvailabilityInput,
)

from app.rule_engine.rules import (
    evaluate_staff_availability_rule,
)


def run_test(name, staff_id, start_time, end_time):

    data = OperationalInput(
        airport_code="HYD",
        flight_number="AI501",

        staff_availability_checks=[
            StaffAvailabilityInput(
                staff_id=staff_id,
                requested_date="2026-11-04",
                start_time=start_time,
                end_time=end_time,
            )
        ],
    )

    result = evaluate_staff_availability_rule(data)

    print("\nTEST:", name)
    print("Rule ID:", result.rule_id)
    print("Triggered:", result.triggered)
    print("Severity:", result.severity)
    print("Status:", result.evaluation_status)
    print("Message:", result.message)


if __name__ == "__main__":

    run_test(
        "Available Staff",
        "HYD_STAFF_002",
        "09:00",
        "11:00",
    )

    run_test(
        "Conflicting Assignment",
        "HYD_STAFF_002",
        "12:00",
        "13:00",
    )

    run_test(
        "No Shift Coverage",
        "HYD_STAFF_002",
        "17:00",
        "18:00",
    )

    run_test(
        "Unknown Staff",
        "UNKNOWN_STAFF",
        "09:00",
        "11:00",
    )