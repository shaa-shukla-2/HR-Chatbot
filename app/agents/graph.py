
import logfire
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.agents.nodes.planner import planner_node
from app.agents.nodes.responder import generate_node
from app.agents.nodes.retriever import retrieve_node
from app.agents.nodes.leave_balance import leave_balance_node
from app.agents.state import AgentState
from app.config import settings


def create_checkpointer() -> BaseCheckpointSaver:
    """Create a Postgres checkpointer, falling back to MemorySaver."""
    try:
        from langgraph.checkpoint.postgres import PostgresSaver
        from psycopg_pool import ConnectionPool

        pool = ConnectionPool(
            conninfo=settings.postgres_uri,
            max_size=20,
            open=False,
            timeout=10,
            num_workers=3,
            check=ConnectionPool.check_connection,
            max_idle=240,
        )

        pool.open()
        conn = pool.getconn()
        pool.putconn(conn)

        try:
            with PostgresSaver.from_conn_string(
                settings.postgres_uri
            ) as setup_saver:
                setup_saver.setup()
        except Exception as e:
            logfire.warning(
                f"Postgres checkpointer setup failed ({e}); "
                "falling back to MemorySaver."
            )
            pool.close()
            return MemorySaver()

        checkpointer = PostgresSaver(pool)
        logfire.info("Postgres checkpointer configured.")
        return checkpointer

    except Exception as e:
        logfire.warning(
            f"Postgres checkpointer unavailable ({e}); "
            f"falling back to MemorySaver: {e}"
        )
        return MemorySaver()


def route_planner(state: AgentState):
    # Use the original user message for personal leave requests.
    messages = state.get("messages", [])
    raw_query = (
        messages[-1].get("content", "")
        if messages
        else state.get("current_query", "")
    )
    query = raw_query.lower()
    planned_query = state.get("current_query", "").lower()

    if planned_query == "conversational":
        return "responder"

    leave_keywords = [
        "my leave balance",
        "leaves do i have",
        "leave do i have",
        "leave left",
        "leave balance",
        "leaves left",
        "leave remaining",
        "leave used",
        "leave usage",
        "my casual leave",
        "my sick leave",
        "my earned leave",
        "how many casual leaves",
        "how many sick leaves",
        "how much earned leave",
        "show my leave",
        "leave have i",
    ]

    if any(keyword in query for keyword in leave_keywords):
        return "leave_balance"

    if any(keyword in planned_query for keyword in leave_keywords):
        return "leave_balance"

    return "retriever"


def build_graph(
    checkpointer: BaseCheckpointSaver | None = None,
):
    """Build and compile the LangGraph HR assistant."""
    if checkpointer is None:
        checkpointer = create_checkpointer()

    workflow = StateGraph(AgentState)

    workflow.add_node("planner", planner_node)
    workflow.add_node("retriever", retrieve_node)
    workflow.add_node("responder", generate_node)
    workflow.add_node("leave_balance", leave_balance_node)

    workflow.set_entry_point("planner")

    workflow.add_conditional_edges(
        "planner",
        route_planner,
        {
            "retriever": "retriever",
            "responder": "responder",
            "leave_balance": "leave_balance",
        },
    )

    workflow.add_edge("leave_balance", END)
    workflow.add_edge("retriever", "responder")
    workflow.add_edge("responder", END)

    graph = workflow.compile(checkpointer=checkpointer)
    graph.checkpointer = checkpointer
    return graph
