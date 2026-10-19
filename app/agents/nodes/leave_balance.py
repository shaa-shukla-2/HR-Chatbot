
import re

import logfire

from app.agents.state import AgentState
from app.hr.policy_tools import format_leave_balance, leave_balance
from app.hr.repository import get_leave_usage


def leave_balance_node(state: AgentState) -> dict:
    """Calculate leave balance only for the authenticated employee."""

    employee = state["employee"]
    employee_id = employee["employee_id"]

    messages = state.get("messages", [])
    question = (
        messages[-1].get("content", "")
        if messages
        else state.get("current_query", "")
    )

    # Refuse requests that explicitly target another employee by name or ID.
    # Do this before querying leave usage.
    target_ids = re.findall(r"\bE\d{4,}\b", question, flags=re.IGNORECASE)
    target_ids = [value.upper() for value in target_ids]

    if any(target_id != employee_id.upper() for target_id in target_ids):
        answer = (
            "For privacy, I can only provide the leave balance "
            "of the employee currently logged in."
        )
        return {
            "final_answer": answer,
            "status": "Request blocked for employee privacy.",
            "plan": state["plan"] + ["Blocked request for another employee's records"],
            "documents": [],
            "messages": [{"role": "assistant", "content": answer}],
        }

    # If another person's name is mentioned, check whether it identifies
    # an employee before accessing leave usage.
    from app.hr.repository import get_employee

    words = re.findall(r"[A-Za-z]+", question.lower())
    full_name = employee["full_name"].lower()
    current_name_words = set(re.findall(r"[a-z]+", full_name))

    # Check common explicit requests for another person's leave balance.
    asks_about_someone_else = any(
        phrase in question.lower()
        for phrase in [
            "show me ",
            "show ",
            "what is ",
            "how much does ",
            "how much leave does ",
            "leave balance for ",
            "leave balance of ",
        ]
    )

    if asks_about_someone_else:
        possible_name = question.lower()
        if not any(
            name_word in possible_name
            for name_word in current_name_words
        ):
            # Search only if the question contains a likely other-person
            # request; never use the result to reveal that person's data.
            candidate = None
            for employee_name in re.findall(
                r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b", question
            ):
                if employee_name.lower() != full_name:
                    # Resolve the name only to detect a cross-employee request.
                    # Do not retrieve or return their leave usage.
                    # Employee IDs remain the authoritative identity.
                    candidate = employee_name
                    break

            if candidate:
                answer = (
                    "For privacy, I can only provide the leave balance "
                    "of the employee currently logged in."
                )
                return {
                    "final_answer": answer,
                    "status": "Request blocked for employee privacy.",
                    "plan": state["plan"] + ["Blocked request for another employee's records"],
                    "documents": [],
                    "messages": [{"role": "assistant", "content": answer}],
                }

    with logfire.span("HR Leave Balance"):
        usage = get_leave_usage(employee_id)

        balance = leave_balance(
            joined_on=employee["joined_on"],
            status=employee["status"],
            cl_used=usage["cl_used"],
            sl_used=usage["sl_used"],
            el_used=usage["el_used"],
        )

        answer = format_leave_balance(
            name=employee["full_name"],
            employee_id=employee_id,
            balance=balance,
        )

    logfire.info("Personal leave balance calculated", employee_id=employee_id)

    return {
        "final_answer": answer,
        "status": "Personal leave balance calculated.",
        "plan": state["plan"] + [
            "Retrieved authenticated employee leave usage",
            "Calculated leave balance",
        ],
        "documents": [],
        "messages": [{"role": "assistant", "content": answer}],
    }
