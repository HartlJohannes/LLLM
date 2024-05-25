import streamlit as st
import time
import requests

url = 'http://212.132.116.206:3000/'
initial_config = {
    'agent_count': 5,
    'supervisor_count': 3
}
config_key = requests.post(url + 'cfg/register', data=initial_config)

session_key = requests.post(url + 'session/create', data={'config_uid': config_key})

st.title('LLLM')

if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

model_count = st.sidebar.slider('Models', 0, 20, 5)
supervisor_count = st.sidebar.slider('Supervisors', 0, 12, 3)
uploaded_files = st.sidebar.file_uploader('Upload a file', accept_multiple_files=True, key=f"uploader_{st.session_state.uploader_key}")


# Streamed response emulator
def response_generator():
    prompt_response = requests.post(url + 'session/send', data={'session_key': session_key, 'prompt': prompt}).text
    for word in prompt_response.split():
        yield word + " "
        time.sleep(0.05)


st.title("Simple chat")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []


# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
if prompt := st.chat_input("Please enter your prompt"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        response = st.write_stream(response_generator())
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})


def update_key():
    st.session_state.uploader_key += 1


if uploaded_files is not None:
    requests.post(url + 'data/upload', files=uploaded_files)