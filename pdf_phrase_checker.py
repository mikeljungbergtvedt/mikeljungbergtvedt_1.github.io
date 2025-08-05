import streamlit as st
from pdfplumber import open as pdf_open
import os

def pdf_to_text(pdf_file):
    text = ""
    with pdf_open(pdf_file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text

st.title("Batch PDF to Text Converter and Phrase Checker")

st.header("Editable Phrases")
phrases = st.text_area("Enter phrases to check (one per line)", value="prøvekjørt\nulyd i motor").split("\n")

uploaded_files = st.file_uploader("Upload PDFs", type="pdf", accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        with open(uploaded_file.name, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        text = pdf_to_text(uploaded_file.name)
        
        st.subheader(f"Converted Text from {uploaded_file.name}")
        st.text_area("Text", text, height=200)
        
        st.subheader("Phrase Check Results")
        found = {phrase: (phrase in text) for phrase in phrases if phrase.strip()}
        for phrase, is_found in found.items():
            st.write(f"{phrase}: {'Found' if is_found else 'Not Found'}")
        
        os.remove(uploaded_file.name)