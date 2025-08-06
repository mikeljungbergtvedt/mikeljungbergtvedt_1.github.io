import streamlit as st
from pdfplumber import open as pdf_open
import os
import re
import pandas as pd
import io

def pdf_to_text(pdf_file):
    text = ""
    try:
        with pdf_open(pdf_file) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"
        return text
    except Exception as e:
        st.error(f"Feil ved behandling av {pdf_file}: {str(e)}")
        return ""

def extract_reg_nr(filename, text):
    # Regular expression to find 2 letters + 5 digits
    pattern = r'\b[A-Z]{2}\d{5}\b'
    # Try to find reg nr in PDF content
    match = re.search(pattern, text)
    if match:
        return match.group(0)
    # Fallback to filename
    match = re.search(pattern, filename)
    return match.group(0) if match else 'None'

# Version number for the app
VERSION = "1.0.13"  # Updated to 1.0.13

# Display Autoringen logo
try:
    st.image("logo.png", width=200)
except Exception as e:
    st.warning("Kunne ikke laste logo.png. Vennligst sjekk filplasseringen eller URL-en.")

st.title(f"Autoringen PDF leser (QA) v{VERSION}")

st.header("Redigerbare søkeord")

phrases = st.text_area("Angi søkeord (én per linje)", placeholder="Skriv søkeord her").split("\n")

uploaded_files = st.file_uploader("Last opp PDF-er", type="pdf", accept_multiple_files=True)

if uploaded_files:
    phrase_counts = {phrase.strip(): 0 for phrase in phrases if phrase.strip()}
    details = []
    detailed_data = []  # List to collect detailed data for Excel
    
    for uploaded_file in uploaded_files:
        with open(uploaded_file.name, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        text = pdf_to_text(uploaded_file.name)
        
        reg_nr = extract_reg_nr(uploaded_file.name, text)  # Extract reg nr from content or filename
        
        found_results = []
        for phrase in phrases:
            phrase = phrase.strip()
            if phrase and phrase.lower() in text.lower():  # Case-insensitive search
                count = len(re.findall(re.escape(phrase), text, re.IGNORECASE))
                found_results.append(f'Funnet: "{phrase}" (Antall: {count})')
                phrase_counts[phrase] += count
                # Collect detailed data
                detailed_data.append({
                    'Filename': uploaded_file.name,
                    'Reg Nr': reg_nr,
                    'Søkeord': phrase,
                    'Antall': count
                })
        
        if found_results:
            details.append((uploaded_file.name, text, found_results))
        
        if os.path.exists(uploaded_file.name):
            os.remove(uploaded_file.name)
    
    # Display summary table if there are any finds
    if any(phrase_counts.values()):
        st.markdown(f"**Søk gjennom {len(uploaded_files)} PDF dokumenter**")
        df_summary = pd.DataFrame(list(phrase_counts.items()), columns=['Søkeord', 'Totalt antall'])
        
        st.subheader("Sammendrag av funn")
        st.dataframe(df_summary)
        
        # Prepare detailed DataFrame
        df_details = pd.DataFrame(detailed_data)
        
        # Export to Excel with formatting
        output = io.BytesIO()
        try:
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                # Write summary sheet with file count in separate cells
                workbook = writer.book
                worksheet_summary = workbook.add_worksheet('Sammendrag')
                header_format = workbook.add_format({'bold': True})
                # Write file count text and number
                worksheet_summary.write('A1', "Søk gjennom", header_format)
                worksheet_summary.write('B1', len(uploaded_files), header_format)
                # Write summary table starting at A3
                df_summary.to_excel(writer, index=False, sheet_name='Sammendrag', startrow=2)
                worksheet_summary.set_column('A:A', 30)  # Adjust width for Søkeord
                worksheet_summary.set_column('B:B', 15)  # Adjust width for Totalt antall
                # Apply bold format to headers
                for col_num, value in enumerate(df_summary.columns):
                    worksheet_summary.write(2, col_num, value, header_format)
                
                # Write detailed sheet
                df_details.to_excel(writer, index=False, sheet_name='Detaljer')
                worksheet_details = writer.sheets['Detaljer']
                for col_num, value in enumerate(df_details.columns):
                    worksheet_details.write(0, col_num, value, header_format)
                worksheet_details.set_column('A:A', 50)  # Adjust width for Filename
                worksheet_details.set_column('B:B', 15)  # Adjust width for Reg Nr
                worksheet_details.set_column('C:C', 30)  # Adjust width for Søkeord
                worksheet_details.set_column('D:D', 15)  # Adjust width for Antall
            
            output.seek(0)
            st.download_button(
                label="Last ned sammendrag som Excel",
                data=output,
                file_name="sammendrag.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            st.error(f"Feil ved generering av Excel-fil: {str(e)}")
    
    # Display detailed results per file
    for name, text, found_results in details:
        st.subheader(f"Konvertert tekst fra {name}")
        st.text_area("Tekst", text, height=200)
        
        st.subheader("Resultater")
        for result in found_results:
            st.write(result)