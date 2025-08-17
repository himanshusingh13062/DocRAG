import streamlit as st

# Page Config
st.set_page_config(page_title="DocRAG", layout="wide")

# Load custom CSS
with open("styles.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Header
st.markdown(
    """
    <div class="header">
        <h1 class="main-title">DocRAG</h1>
        <p class="subtitle">Chat with your documents easily</p>
    </div>
    """,
    unsafe_allow_html=True
)

# Tabs
tab1, tab2 = st.tabs(["📂 Upload & Compress", "💬 Chat"])

# Upload Tab
with tab1:
    st.markdown(
        """
        <div class="upload-box">
            <h2 class="upload-title">📂 Upload Your File</h2>
            <p class="upload-subtitle">Support for PDF (.pdf) and Text (.txt) documents</p>
        """,
        unsafe_allow_html=True
    )

    uploaded_file = st.file_uploader(
        "Drag & drop your file here, or click to select",
        type=["pdf", "txt"],
        label_visibility="collapsed",
        key="fileUploader"
    )

    if uploaded_file:
        st.success(f"✅ Uploaded: {uploaded_file.name}")

    st.markdown("</div>", unsafe_allow_html=True)

# Chat Tab
with tab2:
    st.markdown(
        """
        <div class="chat-box">
            <h2 class="chat-title">💬 Chat</h2>
            <p class="chat-subtitle">Ask questions about your uploaded document</p>
        """,
        unsafe_allow_html=True
    )

    user_input = st.text_input("💭 Type your question here...")

    if user_input:
        st.info(f"You asked: {user_input}")
        st.success("🤖 Answer will appear here.")

    st.markdown("</div>", unsafe_allow_html=True)
