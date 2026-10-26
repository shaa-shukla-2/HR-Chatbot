import os
import uuid

import requests
import streamlit as st
from dotenv import load_dotenv

# Local development: load ../.env if it exists (ignored on Streamlit Cloud).
env_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", ".env")
)
load_dotenv(dotenv_path=env_path)

st.set_page_config(
    page_title="Network India Property | HR Assistant",
    page_icon="🤖",
    layout="wide",
)


def _get_backend_url() -> str:
    """Prefer Streamlit secrets (cloud), then env var / .env (local)."""
    try:
        if "BACKEND_URL" in st.secrets:
            return st.secrets["BACKEND_URL"]
    except Exception:
        pass
    return os.getenv("BACKEND_URL", "http://localhost:8000")


BASE_URL = _get_backend_url().rstrip("/")

DEMO_EMPLOYEE_ID = "E1001"
DEMO_PASSWORD = "rahul@demo1"


# ---------- Session state ----------
defaults = {
    "access_token": None,
    "employee": None,
    "messages": [],
    "session_id": str(uuid.uuid4()),
    "conversations": [],
    "conversations_loaded": False,
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def auth_headers() -> dict:
    return {"Authorization": f"Bearer {st.session_state.access_token}"}


# ---------- LOGIN SCREEN ----------
if not st.session_state.access_token:
    st.title("🏢 Network India Property")
    st.subheader("HR Policy Assistant")
    st.write("Log in with your employee credentials to continue.")

    with st.form("employee_login"):
        employee_id = st.text_input("Employee ID", value=DEMO_EMPLOYEE_ID)
        password = st.text_input(
            "Password", type="password", value=DEMO_PASSWORD
        )
        submitted = st.form_submit_button(
            "Login",
            type="primary",
            use_container_width=True,
        )

    st.caption(
        "Demo account is pre-filled and contains sample data only. "
        "The first login can take up to a minute while the server wakes up."
    )

    if submitted:
        with st.spinner(
            "Connecting to the server (it may take up to a minute to wake up)..."
        ):
            try:
                response = requests.post(
                    f"{BASE_URL}/login",
                    json={
                        "employee_id": employee_id.strip(),
                        "password": password,
                    },
                    timeout=90,
                )

                if response.status_code == 200:
                    result = response.json()
                    st.session_state.access_token = result["access_token"]
                    st.session_state.employee = {
                        "employee_id": result["employee_id"],
                        "name": result["name"],
                        "role": result["role"],
                    }
                    st.session_state.messages = []
                    st.session_state.session_id = str(uuid.uuid4())
                    st.session_state.conversations = []
                    st.session_state.conversations_loaded = False
                    st.rerun()
                elif response.status_code == 401:
                    st.error("Invalid employee ID or password.")
                elif response.status_code == 429:
                    st.warning(
                        "Too many attempts. Please wait a moment and try again."
                    )
                else:
                    st.error(
                        f"Login failed ({response.status_code}). "
                        "Please try again in a minute."
                    )
            except requests.RequestException:
                st.error(
                    "Cannot connect to the HR backend. "
                    "It may still be waking up, so please try again in a minute."
                )

    st.stop()


# ---------- AUTHENTICATED CHAT ----------
employee = st.session_state.employee

with st.sidebar:
    st.title("👤 Employee Account")
    st.write(f"**Name:** {employee['name']}")
    st.write(f"**Employee ID:** {employee['employee_id']}")
    st.write(f"**Role:** {employee['role']}")

    if st.button("Log out", use_container_width=True):
        for key, value in defaults.items():
            st.session_state[key] = value
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()

    st.divider()
    st.subheader("Chat History")

    if st.button("＋ New Chat", use_container_width=True):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()

    # Fetch history only when needed (after login or after a new answer).
    if not st.session_state.conversations_loaded:
        try:
            history_response = requests.get(
                f"{BASE_URL}/conversations",
                headers=auth_headers(),
                timeout=60,
            )
            history_response.raise_for_status()

            st.session_state.conversations = (
                history_response.json().get("conversations", [])
            )
            st.session_state.conversations_loaded = True

        except requests.RequestException as exc:
            st.warning(f"Could not load chat history: {exc}")

    for conversation in st.session_state.conversations:
        saved_thread_id = conversation["thread_id"]
        label = saved_thread_id.split(":", 1)[-1][:12]

        if st.button(
            f"Chat {label}",
            key=f"history_{saved_thread_id}",
            use_container_width=True,
        ):
            try:
                chat_response = requests.get(
                    f"{BASE_URL}/conversation",
                    params={"thread_id": saved_thread_id},
                    headers=auth_headers(),
                    timeout=60,
                )
                chat_response.raise_for_status()

                st.session_state.session_id = saved_thread_id.split(":", 1)[-1]
                st.session_state.messages = (
                    chat_response.json().get("messages", [])
                )
                st.rerun()

            except requests.RequestException as exc:
                st.error(f"Could not open conversation: {exc}")


st.title("🤖 HR Policy Assistant")
st.caption(
    "Ask about company HR policies, or about your own HR data "
    "such as your leave balance."
)

# Display previous messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# Extract text safely from different source formats
def get_source_text(source):
    if isinstance(source, str):
        return source

    if isinstance(source, dict):
        content = source.get("CONTENT", source)
        if isinstance(content, dict):
            return str(content.get("text", content))
        return str(content)

    return str(source)


# Suggested questions
st.write("**Try asking:**")
col1, col2, col3, col4 = st.columns(4)

if col1.button("My leave balance", use_container_width=True):
    st.session_state.pending_question = "How many leaves do I have left?"

if col2.button("Casual leave policy", use_container_width=True):
    st.session_state.pending_question = (
        "How many casual leave days are available to employees?"
    )

if col3.button("Working hours", use_container_width=True):
    st.session_state.pending_question = (
        "What are the company's working hours?"
    )

if col4.button("Work from home", use_container_width=True):
    st.session_state.pending_question = (
        "What is the work-from-home policy?"
    )


prompt = st.chat_input("Ask an HR policy question...")

if not prompt and st.session_state.get("pending_question"):
    prompt = st.session_state.pop("pending_question")

if prompt:
    st.session_state.messages.append(
        {"role": "user", "content": prompt}
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Searching HR policies..."):
            try:
                response = requests.post(
                    f"{BASE_URL}/query",
                    headers=auth_headers(),
                    json={
                        "q": prompt,
                        "thread_id": st.session_state.session_id,
                    },
                    timeout=180,
                )

                if response.status_code == 401:
                    st.error("Your session has expired. Please log in again.")
                    st.session_state.access_token = None
                    st.session_state.employee = None
                    st.rerun()

                if response.status_code == 429:
                    st.warning(
                        "Too many requests. Please wait a moment and try again."
                    )
                    st.stop()

                response.raise_for_status()
                data = response.json()

                answer = data.get("answer", "No answer returned.")
                st.markdown(answer)

                sources = data.get("sources", [])
                if sources:
                    with st.expander("📄 View policy sources"):
                        for index, source in enumerate(sources, start=1):
                            st.markdown(f"**Source {index}**")
                            st.text(get_source_text(source))

                st.session_state.messages.append(
                    {"role": "assistant", "content": answer}
                )

                # Refresh the sidebar history on the next interaction.
                st.session_state.conversations_loaded = False

            except requests.RequestException as exc:
                st.error(f"Could not get an answer from the backend: {exc}")