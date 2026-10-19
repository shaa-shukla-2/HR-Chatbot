
import operator
from typing import Annotated, List, TypedDict


class AgentState(TypedDict):
    messages: Annotated[List[dict], operator.add]
    current_query: str
    documents: List[str]
    plan: List[str]
    status: str
    final_answer: str

    # Authenticated employee information supplied by the backend
    employee: dict
