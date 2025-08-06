import streamlit as st
from pdfplumber import open as pdf_open
import os
import re
import pandas as pd
import io

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

st.title(f"Batch PDF til tekstkonverter og frasekjekker v{VERSION}")

st.header("Redigerbare fraser")

phrases = st.text_area("Angi fraser å sjekke (én per linje)", value="prøvekjørt\nulyd i motor", placeholder="skriv søkeord her").split("\n")

uploaded_files = st.file_uploader("Last opp PDF-er", type="pdf", accept_multiple_files=True)

if uploaded_files:
    phrase_counts = {phrase.strip(): 0 for phrase in phrases if phrase.strip()}
    details = []
    
    for uploaded_file in uploaded_files:
        with open(uploaded_file.name, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        text = pdf_to_text(uploaded_file.name)
        
        reg_nr = extract_reg_nr(uploaded_file.name)
        
        found_results = []
        for phrase in phrases:
            phrase = phrase.strip()
            if phrase and phrase in text:
                count = len(re.findall(re.escape(phrase), text))
                found_results.append(f'Funnet: "{phrase}" (Antall: {count}, Reg nr: {reg_nr})')
                phrase_counts[phrase] += count
        
        if found_results:
            details.append((uploaded_file.name, text, found_results))
        
        if os.path.exists(uploaded_file.name):
            os.remove(uploaded_file.name)
    
    # Display summary table if there are any finds
    if any(phrase_counts.values()):
        df = pd.DataFrame(list(phrase_counts.items()), columns=['Frase', 'Totalt antall'])
        
        st.subheader("Sammendrag av funn")
        st.dataframe(df)
        
        # Export to Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Sammendrag')
        output.seek(0)
        
        st.download_button(
            label="Last ned sammendrag som Excel",
            data=output,
            file_name="sammendrag.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    # Display detailed results per file
    for name, text, found_results in details:
        st.subheader(f"Konvertert tekst fra {name}")
        st.text_area("Tekst", text, height=200)
        
        st.subheader("Resultater for frasekjekk")
        for result in found_results:
            st.write(result)