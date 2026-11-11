from app.database.connection import get_db_connection
from app.rule_engine.schemas import OperationalInput
from app.rule_engine.rules import evaluate_permission_validation_rule

conn = get_db_connection()

requests = conn.execute("""
    SELECT request_id, pilot_user_id, flight_number, status
    FROM permission_requests
""").fetchall()

conn.close()

print("\n========== RULE-008 TEST ==========\n")

for request in requests:
    data = OperationalInput(
        airport_code="HYD",
        flight_number=request["flight_number"],
        permission_request_id=request["request_id"],
        requested_by=request["pilot_user_id"],
    )

    result = evaluate_permission_validation_rule(data)

    print(f"Request ID: {request['request_id']}")
    print(f"Database Status: {request['status']}")
    print(f"Rule Triggered: {result.triggered}")
    print(f"Severity: {result.severity}")
    print(f"Evaluation Status: {result.evaluation_status}")
    print(f"Message: {result.message}")
    print("-" * 50)

print("\n========== TEST COMPLETED ==========")