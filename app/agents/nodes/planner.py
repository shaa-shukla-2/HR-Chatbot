import logfire

from app.agents.state import AgentState
from app.gateway import get_langchain_llm

# Portkey-backed LLM: fallback + cache + retry — same .invoke() interface as ChatOpenAI
llm = get_langchain_llm(feature="planner")


def planner_node(state: AgentState):
    """
    The Planner determines if a search is needed based on the ENTIRE conversation.
    """
    # Get the conversation history (excluding the latest message)
    history = ""
    for msg in state["messages"][:-1]:
        role = "User" if msg["role"] == "user" else "Assistant"
        history += f"{role}: {msg['content']}\n"

    user_message = state["messages"][-1]["content"] if state["messages"] else ""

    prompt = f"""
    You are the Planner for the Network India Property HR Policy Assistant.
    Analyze the conversation history and the latest user message.

    CONVERSATION HISTORY:
    {history}

    LATEST MESSAGE:
    "{user_message}"

    Task:
    1. Output 'CONVERSATIONAL' ONLY if the latest message is a pure greeting, thanks or
       goodbye (hi, hello, thanks), or a question that can be answered using ONLY the
       conversation history above (e.g. "what is my name").
    2. If it is a question about company HR policy, output ONE standalone search query.
       HR topics include: leave (casual, sick, earned, maternity, paternity), attendance,
       working hours, work from home, comp-off, salary, payroll, incentive, commission,
       travel and conveyance reimbursement, onboarding, probation, resignation, notice
       period, full and final settlement, referral bonus, code of conduct, POSH,
       data privacy and client confidentiality.
       Resolve follow-ups using the history. Example: after a question about casual
       leave, "And sick leave?" becomes "sick leave entitlement per year".
    3. For ANY other question, also output a short search query for it. Never answer
       from your own knowledge.

    Output ONLY 'CONVERSATIONAL' or the search query. No quotes, no explanation.
    """

    with logfire.span("🧠 Planner Decision"):
        decision = llm.invoke(prompt).content.strip()
        logfire.info(f"Intent identified: {decision}")

    if decision.strip("\"'. ").upper() == "CONVERSATIONAL":
        return {
            "current_query": "CONVERSATIONAL",
            "status": "Handling conversationally (using memory)...",
            "plan": ["Intent: Conversational/Memory", "Retrieval: Skipped"],
        }

    return {
        "current_query": decision,
        "status": f"HR policy research needed. Searching for: {decision}",
        "plan": ["Intent: HR Policy", f"Search Term: {decision}"],
    }