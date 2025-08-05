import streamlit as st
from pdfplumber import open as pdf_open
import os
import re

def pdf_to_text(pdf_file):
    text = ""
    with pdf_open(pdf_file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text

def extract_reg_nr(filename):
    # Regular expression to find 2 letters + 5 digits in the file name
    pattern = r'\b[A-Z]{2}\d{5}\b'
    match = re.search(pattern, filename)
    return match.group(0) if match else 'None'

# Version number for the app
VERSION = "1.0.1"  # Updated to 1.0.1

st.title(f"Batch PDF to Text Converter and Phrase Checker v{VERSION}")

st.header("Editable Phrases")
phrases = st.text_area("Enter phrases to check (one per line)", value="prøvekjørt\nulyd i motor").split("\n")

uploaded_files = st.file_uploader("Upload PDFs", type="pdf", accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        with open(uploaded_file.name, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        text = pdf_to_text(uploaded_file.name)
        
        # Only proceed if phrases are found
        reg_nr = extract_reg_nr(uploaded_file.name)
        found_results = []

        for phrase in phrases:
            if phrase.strip() and phrase in text:
                # Count occurrences of the phrase
                count = len(re.findall(re.escape(phrase), text))
                found_results.append(f'Found: "{phrase}" (Count: {count}, Reg nr: {reg_nr})')

        # Display text and results only if phrases are found
        if found_results:
            st.subheader(f"Converted Text from {uploaded_file.name}")
            st.text_area("Text", text, height=200)
            
            st.subheader("Phrase Check Results")
            for result in found_results:
                st.write(result)
        
        os.remove(uploaded_file.name)