import streamlit as st
import requests

with open("/app/files/styles.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.set_page_config(page_title="DocRAG", layout="wide")

API_URL = "http://localhost:8000"   

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

st.markdown(
    """
    <div class="header">
        <h1 class="main-title">DocRAG</h1>
        <p class="subtitle">Chat with your documents easily</p>
    </div>
    """,
    unsafe_allow_html=True
)

tab1, tab2 = st.tabs(["Upload & Process", "Chat"])

with tab1:
    st.markdown(
        """
        <div class="card">
            <div class="card-header">
                <h2 class="card-title">📂 Upload Your File</h2>
                <p class="card-description">Support for PDF (.pdf) and Text (.txt) documents</p>
            </div>
        """,
        unsafe_allow_html=True
    )
    
    st.markdown('<div class="card-content">', unsafe_allow_html=True)

    uploaded_files = st.file_uploader(
        "Drag & drop your file here, or click to select",
        type=["pdf", "txt"],
        accept_multiple_files=True,
        label_visibility="collapsed"
    )

    if uploaded_files:
        if st.button("⚡ Process Files"):
            with st.spinner("Processing documents..."):
                files = [("files", (file.name, file, file.type)) for file in uploaded_files]
                try:
                    res = requests.post(f"{API_URL}/upload-files/", files=files)
                    if res.status_code == 200:
                        data = res.json()
                        st.success(f"✅ Processed {len(data.get('processed_files', []))} files")
                        st.info(f"Total Chunks: {data.get('total_chunks', 0)}")
                    else:
                        st.error(f"Upload failed: {res.text}")
                except Exception as e:
                    st.error(f"Error: {e}")

    st.markdown("</div></div>", unsafe_allow_html=True)

with tab2:
    st.markdown(
        """
        <div class="card">
            <div class="card-header">
                <h2 class="card-title">💬 Chat</h2>
                <p class="card-description">Ask questions about your uploaded document</p>
            </div>
        """,
        unsafe_allow_html=True
    )
    
    st.markdown('<div class="card-content">', unsafe_allow_html=True)
    
    if st.session_state.chat_history:
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        
        for i, chat in enumerate(st.session_state.chat_history):
            st.markdown(
                f"""
                <div class="chat-message user-message">
                    <div class="message-header">
                        <strong>👤 You</strong>
                    </div>
                    <div class="message-content">
                        {chat['question']}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            st.markdown(
                f"""
                <div class="chat-message bot-message">
                    <div class="message-header">
                        <strong>🤖 DocRAG</strong>
                    </div>
                    <div class="message-content">
                        {chat['response']}
                    </div>
                    {f'<div class="sources"><strong>📄 Sources:</strong> {", ".join(chat["sources"])}</div>' if chat.get('sources') else ''}
                </div>
                """,
                unsafe_allow_html=True
            )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([4, 1])
        with col2:
            if st.button("🗑️ Clear Chat"):
                st.session_state.chat_history = []
                st.rerun()
    
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_input("Type your question here...", key="chat_input")
        submit_button = st.form_submit_button("Send 📤")

    if submit_button and user_input.strip():
        with st.spinner("Thinking..."):
            try:
                res = requests.post(f"{API_URL}/chat/", json={"message": user_input})
                if res.status_code == 200:
                    data = res.json()
                    
                    st.session_state.chat_history.append({
                        "question": user_input,
                        "response": data['response'],
                        "sources": data.get('sources', [])
                    })
                    
                    st.rerun()
                    
                else:
                    st.error(f"Chat request failed: {res.text}")
            except Exception as e:
                st.error(f"Error: {e}")

    st.markdown("</div></div>", unsafe_allow_html=True)