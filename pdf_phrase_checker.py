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

def find_car_registrations(text):
    # Regular expression to find car registration numbers (e.g., "XXX XXX" or "XX XXXX")
    pattern = r'\b[A-Z]{2,3}\s?\d{2,4}\b'
    registrations = re.findall(pattern, text)
    return registrations

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
        registrations = find_car_registrations(text)
        found_phrases = []
        
        for phrase in phrases:
            if phrase.strip() and phrase in text:
                # Find all occurrences of the phrase and associated registrations
                phrase_occurrences = [(match.start(), match.end()) for match in re.finditer(re.escape(phrase), text)]
                for start, end in phrase_occurrences:
                    # Look for registration numbers within 50 characters before or after the phrase
                    context = text[max(0, start-50):min(len(text), end+50)]
                    reg_matches = re.findall(r'\b[A-Z]{2,3}\s?\d{2,4}\b', context)
                    reg_numbers = ', '.join(set(reg_matches)) if reg_matches else ''
                    found_phrases.append(f"{phrase} ({reg_numbers})")
        
        if found_phrases:
            for result in found_phrases:
                st.write(result)
        else:
            st.write("No phrases found.")
        
        os.remove(uploaded_file.name)