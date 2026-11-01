# ============================================================
# FLIGHT OPERATIONS RISK ENGINE
# ============================================================


def calculate_flight_risk(
    delay_minutes: int,
    status: str,
) -> dict:

    risk_score = 0
    risk_factors = []

    # ========================================================
    # DELAY RISK
    # ========================================================

    if delay_minutes >= 120:
        delay_score = 60
        severity = "CRITICAL"

    elif delay_minutes >= 60:
        delay_score = 45
        severity = "HIGH"

    elif delay_minutes >= 30:
        delay_score = 30
        severity = "MEDIUM"

    elif delay_minutes >= 15:
        delay_score = 15
        severity = "LOW"

    else:
        delay_score = 0
        severity = "LOW"

    if delay_score > 0:

        risk_score += delay_score

        risk_factors.append({
            "factor_type": "DEPARTURE_DELAY",
            "description": (
                f"Flight departure delayed by "
                f"{delay_minutes} minutes"
            ),
            "severity": severity,
            "score": delay_score,
        })

    # ========================================================
    # FLIGHT STATUS RISK
    # ========================================================

    status = status.upper()

    status_scores = {
        "DELAYED": 10,
        "DIVERTED": 30,
        "CANCELLED": 40,
    }

    status_score = status_scores.get(status, 0)

    if status_score > 0:

        risk_score += status_score

        if status == "CANCELLED":
            status_severity = "HIGH"

        elif status == "DIVERTED":
            status_severity = "HIGH"

        else:
            status_severity = "LOW"

        risk_factors.append({
            "factor_type": "FLIGHT_STATUS",
            "description": (
                f"Flight operational status: {status}"
            ),
            "severity": status_severity,
            "score": status_score,
        })

    # ========================================================
    # FINAL RISK SCORE
    # ========================================================

    risk_score = min(100, risk_score)

    if risk_score >= 75:
        risk_level = "CRITICAL"

    elif risk_score >= 50:
        risk_level = "HIGH"

    elif risk_score >= 25:
        risk_level = "MEDIUM"

    else:
        risk_level = "LOW"

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "risk_factors": risk_factors,
    }