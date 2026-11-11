from app.rule_engine.schemas import OperationalInput, RuleResult
from app.tools.staff_availability_tool import check_staff_availability
from app.database.connection import get_db_connection

def evaluate_delay_rule(data: OperationalInput) -> RuleResult:
    """Flag a reported delay of 30 minutes or more."""

    if data.delay_minutes is None:
        return RuleResult(
            rule_id="RULE-001",
            rule_name="Flight Delay Risk",
            triggered=False,
            severity="LOW",
            evaluation_status="NOT_EVALUATED",
            message=(
                f"Delay information for flight {data.flight_number} "
                "is unavailable. The delay risk rule was not evaluated."
            ),
        )

    triggered = data.delay_minutes >= 30

    return RuleResult(
        rule_id="RULE-001",
        rule_name="Flight Delay Risk",
        triggered=triggered,
        severity="MEDIUM" if triggered else "LOW",
        message=(
            f"Flight {data.flight_number} has a reported delay "
            f"of {data.delay_minutes} minutes."
            if triggered
            else "The reported delay is below the configured threshold."
        ),
    )


def evaluate_rainfall_rule(data: OperationalInput) -> RuleResult:
    """Flag reported rainfall of 10 mm or more."""

    if data.rainfall_mm is None:
        return RuleResult(
            rule_id="RULE-002",
            rule_name="Heavy Rainfall Risk",
            triggered=False,
            severity="LOW",
            evaluation_status="NOT_EVALUATED",
            message=(
                "A separate rainfall measurement is unavailable. "
                "The rainfall risk rule was not evaluated."
            ),
        )

    triggered = data.rainfall_mm >= 10.0

    return RuleResult(
        rule_id="RULE-002",
        rule_name="Heavy Rainfall Risk",
        triggered=triggered,
        severity="HIGH" if triggered else "LOW",
        message=(
            f"Reported rainfall is {data.rainfall_mm} mm. "
            "Further operational assessment is recommended."
            if triggered
            else "The reported rainfall is below the configured threshold."
        ),
    )


def evaluate_runway_rule(data: OperationalInput) -> RuleResult:
    """Evaluate reported runway availability."""

    if data.runway_available is None:
        return RuleResult(
            rule_id="RULE-003",
            rule_name="Runway Availability Risk",
            triggered=False,
            severity="LOW",
            evaluation_status="NOT_EVALUATED",
            message=(
                "Runway availability is unknown. "
                "No verified runway status was provided. "
                "Operational confirmation is required."
            ),
        )

    if data.runway_available is False:
        return RuleResult(
            rule_id="RULE-003",
            rule_name="Runway Availability Risk",
            triggered=True,
            severity="HIGH",
            evaluation_status="EVALUATED",
            message=(
                "The runway is reported unavailable. "
                "Further operational assessment is required."
            ),
        )

    return RuleResult(
        rule_id="RULE-003",
        rule_name="Runway Availability Risk",
        triggered=False,
        severity="LOW",
        evaluation_status="EVALUATED",
        message=(
            "The runway is reported available. "
            "Operational verification may still be required."
        ),
    )


def evaluate_gate_conflict_rule(data: OperationalInput) -> RuleResult:
    """
    RULE-004: Detect gate double-booking.

    Checks whether another flight has an overlapping assignment
    for the same gate at the same airport.
    """

    requested = data.gate_assignment
    existing_assignments = data.existing_gate_assignments

    # Required gate evidence is unavailable.
    if requested is None or existing_assignments is None:
        return RuleResult(
            rule_id="RULE-004",
            rule_name="Gate Double-Booking Detection",
            triggered=False,
            severity="LOW",
            evaluation_status="NOT_EVALUATED",
            message=(
                f"Gate assignment information for flight "
                f"{data.flight_number} is unavailable. "
                "Gate conflict detection was not evaluated."
            ),
        )

    # Ensure the requested assignment belongs to this workflow flight.
    if (
        requested.airport_code != data.airport_code
        or requested.flight_number != data.flight_number
    ):
        return RuleResult(
            rule_id="RULE-004",
            rule_name="Gate Double-Booking Detection",
            triggered=False,
            severity="LOW",
            evaluation_status="NOT_EVALUATED",
            message=(
                "The requested gate assignment does not match "
                "the workflow airport or flight. "
                "Gate conflict detection was not evaluated."
            ),
        )

    conflicting_flights = []

    for existing in existing_assignments:

        # Only compare assignments at the same airport and gate.
        if existing.airport_code != requested.airport_code:
            continue

        if existing.gate_id != requested.gate_id:
            continue

        # A flight must not conflict with its own assignment.
        if existing.flight_number == requested.flight_number:
            continue

        # Check whether the two time intervals overlap.
        overlap = (
            requested.start_minute < existing.end_minute
            and requested.end_minute > existing.start_minute
        )

        if overlap:
            conflicting_flights.append(existing.flight_number)

    # A genuine overlapping assignment was found.
    if conflicting_flights:
        unique_conflicts = sorted(set(conflicting_flights))

        return RuleResult(
            rule_id="RULE-004",
            rule_name="Gate Double-Booking Detection",
            triggered=True,
            severity="HIGH",
            evaluation_status="EVALUATED",
            message=(
                f"Gate {requested.gate_id} has overlapping "
                f"assignments with flights: "
                f"{', '.join(unique_conflicts)}. "
                "Further operational review is recommended."
            ),
        )

    # Database evidence was available, but no conflict was found.
    return RuleResult(
        rule_id="RULE-004",
        rule_name="Gate Double-Booking Detection",
        triggered=False,
        severity="LOW",
        evaluation_status="EVALUATED",
        message=(
            f"No overlapping gate assignment was found for "
            f"flight {data.flight_number} at gate "
            f"{requested.gate_id}."
        ),
    )

def evaluate_staff_availability_rule(
    data: OperationalInput,
) -> RuleResult:
    """
    RULE-007: Crew/Staff Availability Validation.

    Checks whether supplied staff members are available
    for the requested airport, date and time.
    """

    staff_checks = data.staff_availability_checks

    # Staff evidence was not supplied.
    if staff_checks is None or len(staff_checks) == 0:
        return RuleResult(
            rule_id="RULE-007",
            rule_name="Crew/Staff Availability Validation",
            triggered=False,
            severity="LOW",
            evaluation_status="NOT_EVALUATED",
            message=(
                f"Staff availability information for flight "
                f"{data.flight_number} is unavailable. "
                "Staff availability validation was not evaluated."
            ),
        )

    unavailable_staff = []
    available_staff = []

    for staff_check in staff_checks:

        try:
            result = check_staff_availability(
                staff_id=staff_check.staff_id,
                requested_date=staff_check.requested_date,
                start_time=staff_check.start_time,
                end_time=staff_check.end_time,
                airport_code=data.airport_code,
            )

        except (ValueError, TypeError) as error:
            return RuleResult(
                rule_id="RULE-007",
                rule_name="Crew/Staff Availability Validation",
                triggered=False,
                severity="LOW",
                evaluation_status="NOT_EVALUATED",
                message=(
                    "Staff availability could not be evaluated "
                    f"because the supplied information is invalid: {error}"
                ),
            )

        if result["available"]:
            available_staff.append(staff_check.staff_id)
        else:
            unavailable_staff.append(
                {
                    "staff_id": staff_check.staff_id,
                    "reason": result["reason"],
                }
            )

    # At least one supplied staff member is unavailable.
    if unavailable_staff:
        reasons = "; ".join(
            f"{item['staff_id']}: {item['reason']}"
            for item in unavailable_staff
        )

        return RuleResult(
            rule_id="RULE-007",
            rule_name="Crew/Staff Availability Validation",
            triggered=True,
            severity="HIGH",
            evaluation_status="EVALUATED",
            message=(
                "Staff availability issues detected. "
                f"{reasons}. Further operational review is required."
            ),
        )

    # All supplied staff members are available.
    return RuleResult(
        rule_id="RULE-007",
        rule_name="Crew/Staff Availability Validation",
        triggered=False,
        severity="LOW",
        evaluation_status="EVALUATED",
        message=(
            f"All {len(available_staff)} supplied staff members "
            f"are available for flight {data.flight_number}."
        ),
    )

def evaluate_permission_validation_rule(
    data: OperationalInput,
) -> RuleResult:
    """
    RULE-008: Operational Permission Validation.

    Checks permission request ownership, flight association,
    review status and reviewer information.
    """

    request_id = data.permission_request_id
    user_id = data.requested_by

    # Permission request information is missing.
    if not request_id or not user_id:
        return RuleResult(
            rule_id="RULE-008",
            rule_name="Operational Permission Validation",
            triggered=False,
            severity="LOW",
            evaluation_status="NOT_EVALUATED",
            message=(
                "Permission request information is unavailable. "
                "Permission validation was not evaluated."
            ),
        )

    connection = get_db_connection()

    try:
        row = connection.execute(
            """
            SELECT
                request_id,
                pilot_user_id,
                flight_number,
                requested_action,
                status,
                reviewed_by
            FROM permission_requests
            WHERE request_id = ?
            """,
            (request_id,),
        ).fetchone()

    except Exception:
        row = None

    finally:
        connection.close()

    # Request does not exist or database lookup failed.
    if row is None:
        return RuleResult(
            rule_id="RULE-008",
            rule_name="Operational Permission Validation",
            triggered=False,
            severity="LOW",
            evaluation_status="NOT_EVALUATED",
            message=(
                "Permission request could not be found or verified."
            ),
        )

    # Verify request ownership.
    if row["pilot_user_id"] != user_id:
        return RuleResult(
            rule_id="RULE-008",
            rule_name="Operational Permission Validation",
            triggered=False,
            severity="LOW",
            evaluation_status="NOT_EVALUATED",
            message=(
                "Permission request ownership does not match "
                "the workflow user."
            ),
        )

    # Verify flight association.
    if (
        row["flight_number"].strip().upper()
        != data.flight_number.strip().upper()
    ):
        return RuleResult(
            rule_id="RULE-008",
            rule_name="Operational Permission Validation",
            triggered=False,
            severity="LOW",
            evaluation_status="NOT_EVALUATED",
            message=(
                "Permission request flight does not match "
                "the workflow flight."
            ),
        )

    if not row["requested_action"]:
        return RuleResult(
            rule_id="RULE-008",
            rule_name="Operational Permission Validation",
            triggered=False,
            severity="LOW",
            evaluation_status="NOT_EVALUATED",
            message="Permission request has no valid requested action.",
        )

    permission_status = row["status"].lower()

    # Pending request.
    if permission_status == "pending":
        return RuleResult(
            rule_id="RULE-008",
            rule_name="Operational Permission Validation",
            triggered=True,
            severity="HIGH",
            evaluation_status="EVALUATED",
            message=(
                "Permission request is pending administrative review. "
                "Hold further action until reviewed."
            ),
        )

    # Rejected request.
    if permission_status == "rejected":
        if not row["reviewed_by"]:
            return RuleResult(
                rule_id="RULE-008",
                rule_name="Operational Permission Validation",
                triggered=False,
                severity="LOW",
                evaluation_status="NOT_EVALUATED",
                message="Rejected request has no recorded reviewer.",
            )

        return RuleResult(
            rule_id="RULE-008",
            rule_name="Operational Permission Validation",
            triggered=True,
            severity="HIGH",
            evaluation_status="EVALUATED",
            message=(
                "Permission request was rejected by an administrator. "
                "Further action should remain on hold."
            ),
        )

    # Approved request.
    if permission_status == "approved":
        if not row["reviewed_by"]:
            return RuleResult(
                rule_id="RULE-008",
                rule_name="Operational Permission Validation",
                triggered=False,
                severity="LOW",
                evaluation_status="NOT_EVALUATED",
                message="Approved request has no recorded reviewer.",
            )

        return RuleResult(
            rule_id="RULE-008",
            rule_name="Operational Permission Validation",
            triggered=False,
            severity="LOW",
            evaluation_status="EVALUATED",
            message=(
                "Permission request has administrative approval. "
                "This does not constitute official airport or ATC "
                "operational clearance."
            ),
        )

    # Unexpected database status.
    return RuleResult(
        rule_id="RULE-008",
        rule_name="Operational Permission Validation",
        triggered=False,
        severity="LOW",
        evaluation_status="NOT_EVALUATED",
        message="Permission request has an unrecognized status.",
    )