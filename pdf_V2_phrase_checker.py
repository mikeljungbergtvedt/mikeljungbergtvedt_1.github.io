import streamlit as st
import fitz  # PyMuPDF - pip install pymupdf
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
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        for page in doc:
            text += page.get_text("text") + "\n"  # "text" mode for good flow/order
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
                # Wider pattern for multi-word after "ikke"
                potential_matches = re.findall(r'\bikke\b[^.!?\n]{0,100}', full_text, re.IGNORECASE)
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

# ────────────────────────────────────────────────
#               APP STARTER HER
# ────────────────────────────────────────────────

VERSION = "1.0.44"  # Oppdatert versjonsnummer (valgfritt)

# Display logo
try:
    st.image("logo.png", width=200)
except Exception as e:
    st.warning(f"Kunne ikke laste logo.png: {str(e)}")

st.title(f"Autoringen PDF leser (QA FAST) v{VERSION}")

# Oslo tid
oslo_tz = pytz.timezone('Europe/Oslo')
current_time = datetime.now(oslo_tz)
formatted_time = current_time.strftime("%A, %d. %B %Y, %H:%M CEST")

# Bruk Streamlit sin innebygde tema-deteksjon
theme = st.context.theme.type if hasattr(st.context, 'theme') else "dark"

if theme == "light":
    clock_color = "#333333"
else:
    clock_color = "#CCCCCC"  # dark + system fallback

time_style = f"font-size:12px; padding:8px; margin-bottom:10px; color:{clock_color};"
st.markdown(f"<div style='{time_style}'>{formatted_time}</div>", unsafe_allow_html=True)

st.header("Redigerbare søkeord")
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
            for phrase, count in result['per_phrase_counts'].items():
                phrase_counts[phrase] += count
                if count > 0:
                    phrase_file_counts[phrase].add(result['file_name'])
                    if result['reg_nr']:
                        phrase_reg_nrs[phrase].add(result['reg_nr'])

            for phrase in phrases:
                count = result['per_phrase_counts'][phrase]
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

    # Oppdater Antall biler
    for row in detailed_data:
        row['Antall biler'] = len(phrase_file_counts.get(row['Søkeord'], set()))

    # Summary
    if phrases:
        st.markdown(f"**Søk gjennom {len(uploaded_files)} PDF dokumenter**")

        summary_data = [
            {
                'Søkeord': phrase,
                'Totalt antall': phrase_counts.get(phrase, 0),
                'Reg Nr': ', '.join(phrase_reg_nrs.get(phrase, set())) or '',
                'Funn': 'Ja' if phrase_counts.get(phrase, 0) > 0 else 'Nei'
            } for phrase in phrases
        ]
        df_summary = pd.DataFrame(summary_data)
        st.subheader("Sammendrag av funn")
        st.dataframe(df_summary)

        df_details = pd.DataFrame(detailed_data)

        # Excel export
        current_time_str = datetime.now(oslo_tz).strftime("%Y-%m-%d_%H%M")
        excel_filename = f"{current_time_str}_{len(uploaded_files)}.xlsx"
        output = io.BytesIO()

        try:
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                workbook = writer.book
                header_format = workbook.add_format({'bold': True})

                # Sammendrag ark
                worksheet_summary = workbook.add_worksheet('Sammendrag')
                worksheet_summary.write('A1', "Antall PDF søkt gjennom:", header_format)
                worksheet_summary.write('B1', len(uploaded_files), header_format)
                df_summary.to_excel(writer, index=False, sheet_name='Sammendrag', startrow=2)
                worksheet_summary.set_column('A:A', 30)
                worksheet_summary.set_column('B:B', 15)
                worksheet_summary.set_column('C:C', 20)
                worksheet_summary.set_column('D:D', 10)

                # Detaljer ark
                worksheet_details = workbook.add_worksheet('Detaljer')
                worksheet_details.write('A1', "Filnavn", header_format)
                df_details.to_excel(writer, index=False, sheet_name='Detaljer', startrow=2)
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

        # Detailed results
        for name, text, found_results in details:
            st.subheader(f"Konvertert tekst fra {name}")
            st.text_area("Tekst", text, height=200)
            st.subheader("Resultater")
            for result in found_results:
                st.write(result)

# Footer
st.markdown(
    """
    <div style="font-size:10px; color:#666666; margin-top:20px; padding:10px; border-top:1px solid #cccccc;">
    <b>Tekniske begrensninger:</b> Appen er begrenset av Streamlit Cloud’s minne (~1 GB) og filstørrelse (200 MB per fil).
    Registreringsnummer krever formatet to bokstaver + fem sifre. Ytelse kan variere for store batcher (>50 PDFer).
    </div>
    """,
    unsafe_allow_html=True
)
