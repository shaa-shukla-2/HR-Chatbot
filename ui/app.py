
import os
import uuid

import requests
import streamlit as st
from dotenv import load_dotenv

env_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", ".env")
)
load_dotenv(dotenv_path=env_path)

st.set_page_config(
    page_title="Network India Property | HR Assistant",
    page_icon="🤖",
    layout="wide",
)

BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")


# Initialize session state
if "access_token" not in st.session_state:
    st.session_state.access_token = None

if "employee" not in st.session_state:
    st.session_state.employee = None

if "messages" not in st.session_state:
    st.session_state.messages = []

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "conversations" not in st.session_state:
    st.session_state.conversations = []

if "conversations_loaded" not in st.session_state:
    st.session_state.conversations_loaded = False


# ---------- LOGIN SCREEN ----------
if not st.session_state.access_token:
    st.title("🏢 Network India Property")
    st.subheader("HR Policy Assistant")
    st.write("Log in with your employee credentials to continue.")

    with st.form("employee_login"):
        employee_id = st.text_input("Employee ID")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button(
        "Login",
        type="primary",
        use_container_width=True,
)

    if submitted:
        try:
            response = requests.post(
                f"{BASE_URL}/login",
                json={
                    "employee_id": employee_id.strip(),
                    "password": password,
                },
                timeout=30,
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
            else:
                st.error(
                    f"Login failed ({response.status_code}). "
                    "Please try again."
                )
        except requests.RequestException:
            st.error(
                "Cannot connect to the HR backend. "
                "Check whether FastAPI is running."
            )

    st.stop()


# ---------- AUTHENTICATED CHAT ----------
employee = st.session_state.employee

with st.sidebar:
    st.title("👤 Employee Account")
    st.write(f"**Name:** {employee['name']}")
    st.write(f"**Employee ID:** {employee['employee_id']}")
    st.write(f"**Role:** {employee['role']}")
    
    st.divider()
    st.subheader("Chat History")

    if st.button("＋ New Chat", use_container_width=True):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()

    
    # Fetch history only once per login/session, not on every rerun.
    if not st.session_state.conversations_loaded:
        try:
            history_response = requests.get(
                f"{BASE_URL}/conversations",
                headers={
                    "Authorization": (
                        f"Bearer {st.session_state.access_token}"
                    )
                },
                timeout=30,
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
                    headers={
                        "Authorization": (
                            f"Bearer {st.session_state.access_token}"
                        )
                    },
                    timeout=30,
                )
                chat_response.raise_for_status()

                st.session_state.session_id = (
                    saved_thread_id.split(":", 1)[-1]
                )
                st.session_state.messages = (
                    chat_response.json().get("messages", [])
                )
                st.rerun()

            except requests.RequestException as exc:
                st.error(f"Could not open conversation: {exc}")


st.title("🤖 HR Policy Assistant")
st.caption("Ask questions about company HR policies and benefits.")

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
col1, col2, col3 = st.columns(3)

if col1.button("Casual leave policy"):
    st.session_state.pending_question = (
        "How many casual leave days are available to employees?"
    )

if col2.button("Working hours"):
    st.session_state.pending_question = (
        "What are the company's working hours?"
    )

if col3.button("Work from home"):
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
                    headers={
                        "Authorization": (
                            f"Bearer {st.session_state.access_token}"
                        )
                    },
                    json={
                        "q": prompt,
                        "thread_id": st.session_state.session_id,
                    },
                    timeout=180,
                )

                if response.status_code == 401:
                    st.error(
                        "Your session has expired. "
                        "Please log in again."
                    )
                    st.session_state.access_token = None
                    st.session_state.employee = None
                    st.rerun()

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

            except requests.RequestException as exc:
                st.error(f"Could not get an answer from the backend: {exc}")
