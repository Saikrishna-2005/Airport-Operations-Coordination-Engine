import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.permissions import require_roles
from app.database.connection import get_db_connection
from app.database.audit import log_audit_event

from app.agents.action_schemas import (
    ActionProposalCreate,
    ActionProposalResponse,
    ActionReviewRequest,
)

from app.agents.safety_validator import validate_action
from app.agents.action_generator import generate_action_proposals


router = APIRouter(
    prefix="/actions",
    tags=["AI Action Approval"],
)

@router.post("/proposals/generate/{workflow_id}")
def generate_workflow_action_proposals(
    workflow_id: str,
    current_user: dict = Depends(require_roles("admin", "operator")),
):
    # Step 1: Retrieve the workflow
    connection = get_db_connection()

    try:
        row = connection.execute(
            """
            SELECT
                workflow_id,
                requested_by,
                input_data,
                planning_result,
                research_result,
                rule_results
            FROM workflows
            WHERE workflow_id = ?
              AND (requested_by = ? OR ? = 'admin')
            """,
            (
                workflow_id,
                current_user["user_id"],
                current_user["role"],
            ),
        ).fetchone()

    finally:
        connection.close()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Workflow not found or access denied.",
        )

    # Step 2: Retrieve stored workflow information
    input_data = json.loads(row["input_data"])

    planning_result = (
        json.loads(row["planning_result"])
        if row["planning_result"]
        else None
    )

    research_result = (
        json.loads(row["research_result"])
        if row["research_result"]
        else None
    )

    rule_results = (
        json.loads(row["rule_results"])
        if row["rule_results"]
        else []
    )

    if not planning_result:
        raise HTTPException(
            status_code=409,
            detail="Workflow does not contain a valid planning result.",
        )

    airport = input_data["airport"].strip().upper()

    affected_flights = {
        flight.strip().upper()
        for flight in input_data.get("affected_flights", [])
    }

    # Step 3: Generate action proposals
    try:
        generated_result = generate_action_proposals(
            workflow_id=workflow_id,
            airport=airport,
            planning_result=planning_result,
            research_result=research_result,
            rule_results=rule_results,
            gate_information={},
        )

    except Exception as exc:
        from app.logger import logger

        logger.exception(
            "Action proposal generation failed: %s",
            workflow_id,
        )

        raise HTTPException(
            status_code=502,
            detail="Action proposal generation failed.",
        ) from exc

    created_actions = []

    # Step 4: Validate and save generated proposals
    connection = get_db_connection()

    try:
        for action in generated_result.actions:

            validation = validate_action(action)

            errors = list(validation.errors)

            # Verify target flight against workflow inputs
            if (
                action.target_flight
                and action.target_flight.strip().upper()
                not in affected_flights
            ):
                errors.append(
                    "Target flight does not belong to this workflow."
                )

            validation_status = (
                "validated" if not errors else "failed"
            )

            action_id = str(uuid.uuid4())

            connection.execute(
                """
                INSERT INTO action_proposals (
                    action_id,
                    workflow_id,
                    airport,
                    action_type,
                    description,
                    target_flight,
                    payload,
                    validation_status,
                    approval_status,
                    execution_status,
                    proposed_by
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    action_id,
                    workflow_id,
                    airport,
                    action.action_type,
                    action.description,
                    action.target_flight,
                    json.dumps(action.payload),
                    validation_status,
                    "pending",
                    "not_started",
                    current_user["user_id"],
                ),
            )

            created_actions.append({
                "action_id": action_id,
                "workflow_id": workflow_id,
                "airport": airport,
                "action_type": action.action_type,
                "description": action.description,
                "target_flight": action.target_flight,
                "validation_status": validation_status,
                "validation_errors": errors,
                "approval_status": "pending",
                "execution_status": "not_started",
            })

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

    # Step 5: Record audit events
    for action in created_actions:

        log_audit_event(
            user_id=current_user["user_id"],
            action="AI_ACTION_PROPOSED",
            resource_type="action_proposal",
            resource_id=action["action_id"],
            details={
                "workflow_id": workflow_id,
                "action_type": action["action_type"],
                "validation_status": action["validation_status"],
                "validation_errors": action["validation_errors"],
                "approval_status": "pending",
            },
        )

    return {
        "workflow_id": workflow_id,
        "airport": airport,
        "generated_count": len(created_actions),
        "actions": created_actions,
    }

@router.post(
    "/proposals",
    response_model=list[ActionProposalResponse],
    status_code=status.HTTP_201_CREATED,
)
def create_action_proposals(
    request: ActionProposalCreate,
    current_user: dict = Depends(require_roles("admin", "operator")),
):
    connection = get_db_connection()
    created_actions = []

    try:
        workflow = connection.execute(
            """
            SELECT workflow_id
            FROM workflows
            WHERE workflow_id = ?
            """,
            (request.workflow_id,),
        ).fetchone()

        if workflow is None:
            raise HTTPException(
                status_code=404,
                detail="Workflow not found.",
            )

        for action in request.actions:

            validation = validate_action(action)

            action_id = str(uuid.uuid4())

            approval_status = (
                "pending"
                if validation.is_valid
                else "rejected"
            )

            connection.execute(
                """
                INSERT INTO action_proposals (
                    action_id,
                    workflow_id,
                    airport,
                    action_type,
                    description,
                    target_flight,
                    payload,
                    validation_status,
                    approval_status,
                    execution_status,
                    proposed_by
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    action_id,
                    request.workflow_id,
                    request.airport.upper(),
                    action.action_type,
                    action.description,
                    action.target_flight,
                    json.dumps(action.payload),
                    validation.status,
                    approval_status,
                    "not_started",
                    current_user["user_id"],
                ),
            )

            created_actions.append(
                ActionProposalResponse(
                    action_id=action_id,
                    workflow_id=request.workflow_id,
                    airport=request.airport.upper(),
                    action_type=action.action_type,
                    description=action.description,
                    target_flight=action.target_flight,
                    validation_status=validation.status,
                    approval_status=approval_status,
                    execution_status="not_started",
                )
            )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

    for action in created_actions:
        log_audit_event(
            user_id=current_user["user_id"],
            action="AI_ACTION_PROPOSED",
            resource_type="action_proposal",
            resource_id=action.action_id,
            details={
                "workflow_id": action.workflow_id,
                "action_type": action.action_type,
                "validation_status": action.validation_status,
                "approval_status": action.approval_status,
            },
        )

    return created_actions


@router.get("/proposals")
def get_action_proposals(
    current_user: dict = Depends(require_roles("admin", "operator")),
):
    connection = get_db_connection()

    try:
        rows = connection.execute(
            """
            SELECT *
            FROM action_proposals
            ORDER BY created_at DESC
            """
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()


@router.patch("/proposals/{action_id}/review")
def review_action_proposal(
    action_id: str,
    review: ActionReviewRequest,
    current_user: dict = Depends(require_roles("admin")),
):
    connection = get_db_connection()

    try:
        row = connection.execute(
            """
            SELECT action_id, validation_status, approval_status
            FROM action_proposals
            WHERE action_id = ?
            """,
            (action_id,),
        ).fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail="Action proposal not found.",
            )

        if row["validation_status"] != "validated":
            raise HTTPException(
                status_code=400,
                detail="Only validated actions can be reviewed.",
            )

        if row["approval_status"] != "pending":
            raise HTTPException(
                status_code=409,
                detail="Action has already been reviewed.",
            )

        cursor = connection.execute(
            """
            UPDATE action_proposals
            SET approval_status = ?,
                reviewed_by = ?,
                review_comment = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE action_id = ?
              AND approval_status = 'pending'
            """,
            (
                review.decision,
                current_user["user_id"],
                review.review_comment,
                action_id,
            ),
        )

        if cursor.rowcount != 1:
            raise HTTPException(
                status_code=409,
                detail="Action review conflict. Please retry.",
            )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

    log_audit_event(
        user_id=current_user["user_id"],
        action=(
            "AI_ACTION_APPROVED"
            if review.decision == "approved"
            else "AI_ACTION_REJECTED"
        ),
        resource_type="action_proposal",
        resource_id=action_id,
        details={
            "decision": review.decision,
            "review_comment": review.review_comment,
        },
    )

    return {
        "action_id": action_id,
        "approval_status": review.decision,
        "reviewed_by": current_user["user_id"],
        "review_comment": review.review_comment,
    }
