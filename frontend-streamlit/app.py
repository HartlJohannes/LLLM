import streamlit as st
import requests
import json
import os

# Base URL for API requests
url = 'http://212.132.116.206:3000/'

# File to store deleted session keys
deleted_sessions_file = "deleted_sessions.json"


# Function to initialize a new chat session
def initialize_session(agent_count=3, supervisor_count=1):
    config = {
        'agent_count': agent_count,
        'supervisor_count': supervisor_count
    }
    config_key = requests.post(url + 'cfg/register/', json=config).json()["uid"]
    session_key = requests.post(url + f'session/create?config_uid={config_key}').json()["session_key"]
    return config_key, session_key


# Function to fetch the list of sessions
def fetch_sessions():
    response = requests.get(url + 'session/list')
    return response.json()


# Function to read messages from a session
def read_session_messages(session_key):
    response = requests.post(url + f'session/read?session_key={session_key}')
    return response.json()


# Function to load deleted session keys
def load_deleted_sessions():
    if os.path.exists(deleted_sessions_file):
        with open(deleted_sessions_file, 'r') as file:
            return json.load(file)
    return []


# Function to save deleted session keys
def save_deleted_sessions(deleted_sessions):
    with open(deleted_sessions_file, 'w') as file:
        json.dump(deleted_sessions, file)


# Function to upload PDF file
def upload_pdf(file):
    files = {'file': file}
    response = requests.post(url + 'ingest', files=files)
    return response.json()


# Initialize a session if not already present in session state
if "config_key" not in st.session_state or "session_key" not in st.session_state:
    st.session_state.config_key, st.session_state.session_key = initialize_session()

# Load deleted sessions
deleted_sessions = load_deleted_sessions()

# Fetch list of sessions
sessions = fetch_sessions()

# Sidebar for session management
st.sidebar.title("Sessions")
if st.sidebar.button("Create New Chat"):
    with st.sidebar.expander("Parameters"):
        agent_count = st.slider("Agent Count", 1, 20, 3)
        supervisor_count = st.slider("Supervisor Count", 1, 12, 1)
        if st.button("Create"):
            st.session_state.config_key, st.session_state.session_key = initialize_session(agent_count=agent_count,
                                                                                           supervisor_count=supervisor_count)
            st.session_state.messages = []
            st.rerun()

# Button to delete all chats
if st.sidebar.button("Delete All Chats"):
    deleted_sessions.extend(session for session in sessions if session not in deleted_sessions)
    save_deleted_sessions(deleted_sessions)
    st.session_state.session_key = None
    st.session_state.messages = []
    st.rerun()

# Filter out deleted sessions
sessions = [session for session in sessions if session not in deleted_sessions]

# Add file uploader to the sidebar
uploaded_file = st.sidebar.file_uploader("Upload a PDF file", type="pdf")
if uploaded_file is not None:
    with st.spinner('Uploading file...'):
        response = upload_pdf(uploaded_file)
        st.sidebar.success('File uploaded successfully!')

# Switch for sending with context
send_with_context = st.sidebar.checkbox("Send With Context")

st.sidebar.write("Available Sessions:")
# Display sessions in reverse order
for session in reversed(sessions):
    if st.sidebar.button(session):
        st.session_state.session_key = session
        st.session_state.messages = read_session_messages(session)  # Load messages from the selected session
        st.rerun()

# Main content area for chat
st.title("Lumin")

# Initialize chat history in session state if not already present
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    role, content = message
    role = "assistant" if role.lower() == "bot" else "user"
    with st.chat_message(role):
        st.markdown(content)

# Accept user input
if prompt := st.chat_input("Please enter your prompt"):
    # Add user message to chat history
    st.session_state.messages.append(("User", prompt))
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)

    # Select the appropriate endpoint based on the switch state
    endpoint = 'session/send-with-context' if send_with_context else 'session/send'

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        resp = requests.post(
            url + f'{endpoint}?session_key={st.session_state.session_key}&prompt={prompt}').text
        st.markdown(resp)
        # Add assistant response to chat history
        st.session_state.messages.append(("Bot", resp))
