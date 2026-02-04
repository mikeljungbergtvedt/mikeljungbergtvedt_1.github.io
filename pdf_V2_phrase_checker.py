import streamlit as st
import pypdfium2 as pdfium  # Faster text extraction
import re
import pandas as pd
import io
from datetime import datetime
import pytz
import difflib
from concurrent.futures import ThreadPoolExecutor, as_completed

def pdf_to_text(pdf_content):
    text = ""
    try:
        doc = pdfium.PdfDocument(pdf_content)
        for page_num in range(len(doc)):
            page = doc[page_num]
            text += page.get_textpage().get_text_range() + "\n"
            page.close()
        doc.close()
        return text
    except Exception as e:
        st.error(f"Feil ved behandling: {str(e)}")
        return ""

def extract_reg_nr(filename, text):
    pattern = r'\b[A-ZÆØÅ]{2}\d{5}\b'
    match = re.search(pattern, text)
    if match:
        return match.group(0)
    match = re.search(pattern, filename)
    return match.group(0) if match else ""

def process_single_pdf(uploaded_file, phrases):
    pdf_content = uploaded_file.getvalue()
    file_name = uploaded_file.name
    full_text = pdf_to_text(pdf_content)
    reg_nr = extract_reg_nr(file_name, full_text)
    found_results = []
    per_phrase_counts = {phrase: 0 for phrase in phrases}
    for phrase in phrases:
        if phrase:
            exact_pattern = re.compile(re.escape(phrase), re.IGNORECASE)
            exact_count = len(exact_pattern.findall(full_text))
            fuzzy_count = 0
            if exact_count == 0:
                potential_matches = re.findall(r'\bikke\b[^.!?\n]{0,80}', full_text, re.IGNORECASE)
                for potential in potential_matches:
                    if difflib.SequenceMatcher(None, phrase.lower(), potential.lower()).ratio() > 0.8:
                        fuzzy_count += 1
            total_count = exact_count + fuzzy_count
            per_phrase_counts[phrase] = total_count
            if total_count > 0:
                result_type = "exact" if exact_count > 0 else "fuzzy"
                found_results.append(f'Funnet ({result_type}): "{phrase}" (Antall: {total_count})')
    return {
        'file_name': file_name,
        'full_text': full_text,
        'reg_nr': reg_nr,
        'found_results': found_results,
        'per_phrase_counts': per_phrase_counts
    }

# Version number for the app
VERSION = "1.0.43"  # Kept same for duplicate

# Initialize session state for mode
if 'mode' not in st.session_state:
    st.session_state.mode = "dark"  # Default to dark mode

# Function to update mode safely
def update_mode():
    mode = st.session_state.mode_input if st.session_state.get('mode_input') in ["dark", "light"] else st.session_state.mode
    st.session_state.mode = mode

# Manual mode toggle
if st.sidebar.button("Bytt modus"):
    st.session_state.mode = "light" if st.session_state.mode == "dark" else "dark"

# Hidden section for mode detection
mode_container = st.empty()
with mode_container:
    st.text_input("mode", key="mode_input", value="dark", max_chars=5, type="default", on_change=update_mode)
    st.markdown(
        """
        <script>
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)');
        prefersDark.addEventListener('change', (e) => {
            const mode = e.matches ? 'dark' : 'light';
            console.log('Detected mode:', mode); // Debug log
            window.parent.document.getElementById('mode_input').value = mode;
            window.parent.document.getElementById('mode_input').dispatchEvent(new Event('change'));
        });
        // Initial detection
        const initialMode = prefersDark.matches ? 'dark' : 'light';
        console.log('Initial detected mode:', initialMode);
        window.parent.document.getElementById('mode_input').value = initialMode;
        window.parent.document.getElementById('mode_input').dispatchEvent(new Event('change'));
        </script>
        """,
        unsafe_allow_html=True
    )

# Display Autoringen logo (fixed deprecation)
try:
    st.image("logo.png", width=200)
except Exception as e:
    st.warning(f"Kunne ikke laste logo.png: {str(e)}. Vennligst last opp filen til roten av repositoryet eller sjekk stien.")

st.title(f"Autoringen PDF leser (QA FAST) v{VERSION}")  # Added FAST to distinguish

# Display current Oslo date and time with dynamic color
oslo_tz = pytz.timezone('Europe/Oslo')
current_time = datetime.now(oslo_tz)
formatted_time = current_time.strftime("%A, %d. %B %Y, %H:%M CEST")
time_style = f"font-size:12px; padding:8px; margin-bottom:10px;" + \
    ("color:#333333;" if st.session_state.mode == "light" else "color:#CCCCCC;")
st.markdown(
    f"<div style='{time_style}'>{formatted_time}</div>",
    unsafe_allow_html=True
)

st.header("Redigerbare søkeord")

# Capture search input
search_input = st.text_area("Angi søkeord (én per linje)", placeholder="Skriv søkeord her", key="search_input")
phrases = [p.strip() for p in search_input.splitlines() if p.strip()]

uploaded_files = st.file_uploader("Last opp PDF-er", type="pdf", accept_multiple_files=True)

if uploaded_files:
    progress_bar = st.progress(0)
    phrase_counts = {phrase: 0 for phrase in phrases}
    phrase_file_counts = {phrase: set() for phrase in phrases}
    phrase_reg_nrs = {phrase: set() for phrase in phrases}
    details = []
    detailed_data = []

    # Parallel processing
    results = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_file = {executor.submit(process_single_pdf, f, phrases): f for f in uploaded_files}
        for idx, future in enumerate(as_completed(future_to_file)):
            result = future.result()
            results.append(result)
            # Aggregate
            for phrase, count in result['per_phrase_counts'].items():
                phrase_counts[phrase] += count
                if count > 0:
                    phrase_file_counts[phrase].add(result['file_name'])
                    if result['reg_nr']:
                        phrase_reg_nrs[phrase].add(result['reg_nr'])
                detailed_data.append({
                    'Filename': result['file_name'],
                    'Reg Nr': result['reg_nr'],
                    'Søkeord': phrase,
                    'Antall': count,
                    'Funn': 'Ja' if count > 0 else 'Nei',
                    'Antall biler': 0  # Placeholder
                })
            if result['found_results']:
                details.append((result['file_name'], result['full_text'], result['found_results']))
            progress_bar.progress((idx + 1) / len(uploaded_files))

    # Update Antall biler post-processing
    for row in detailed_data:
        row['Antall biler'] = len(phrase_file_counts.get(row['Søkeord'], set()))

    # Display summary table if there are any finds or phrases
    if phrases:
        st.markdown(f"**Søk gjennom {len(uploaded_files)} PDF dokumenter**")
        summary_data = []
        for phrase in phrases:
            count = phrase_counts.get(phrase, 0)
            reg_nrs = phrase_reg_nrs.get(phrase, set())
            summary_data.append({
                'Søkeord': phrase,
                'Totalt antall': count,
                'Reg Nr': ', '.join(reg_nrs) if reg_nrs else '',
                'Funn': 'Ja' if count > 0 else 'Nei'
            })
        df_summary = pd.DataFrame(summary_data)

        st.subheader("Sammendrag av funn")
        st.dataframe(df_summary)

        # Prepare detailed DataFrame
        df_details = pd.DataFrame(detailed_data)

        # Generate dynamic Excel filename with Oslo timezone
        current_time = datetime.now(oslo_tz).strftime("%Y-%m-%d_%H%M")
        excel_filename = f"{current_time}_{len(uploaded_files)}.xlsx"

        # Export to Excel with formatting
        output = io.BytesIO()
        try:
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                # Write summary sheet
                workbook = writer.book
                worksheet_summary = workbook.add_worksheet('Sammendrag')
                header_format = workbook.add_format({'bold': True})
                worksheet_summary.write('A1', "Antall PDF søkt gjennom:", header_format)
                worksheet_summary.write('B1', len(uploaded_files), header_format)
                df_summary.to_excel(writer, index=False, sheet_name='Sammendrag', startrow=2)
                worksheet_summary.set_column('A:A', 30)
                worksheet_summary.set_column('B:B', 15)
                worksheet_summary.set_column('C:C', 20)
                worksheet_summary.set_column('D:D', 10)
                for col_num, value in enumerate(df_summary.columns):
                    worksheet_summary.write(2, col_num, value, header_format)

                # Write detailed sheet
                worksheet_details = workbook.add_worksheet('Detaljer')
                worksheet_details.write('A1', "Filnavn", header_format)
                df_details.to_excel(writer, index=False, sheet_name='Detaljer', startrow=2)
                for col_num, value in enumerate(df_details.columns):
                    worksheet_details.write(2, col_num, value, header_format)
                worksheet_details.set_column('A:A', 50)
                worksheet_details.set_column('B:B', 15)
                worksheet_details.set_column('C:C', 30)
                worksheet_details.set_column('D:D', 15)
                worksheet_details.set_column('E:E', 10)
                worksheet_details.set_column('F:F', 15)

            output.seek(0)
            st.download_button(
                label="Last ned sammendrag som Excel",
                data=output,
                file_name=excel_filename,
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

# Footer with technical limitations
st.markdown(
    """
    <div style="font-size:10px; color:#666666; margin-top:20px; padding:10px; border-top:1px solid #cccccc;">
    <b>Tekniske begrensninger:</b> Appen er begrenset av Streamlit Cloud’s minne (~1 GB) og filstørrelse (200 MB per fil).
    Registreringsnummer krever formatet to bokstaver + fem sifre. Ytelse kan variere for store batcher (>50 PDFer).
    </div>
    """,
    unsafe_allow_html=True
)
