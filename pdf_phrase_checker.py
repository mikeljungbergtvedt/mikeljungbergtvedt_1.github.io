import streamlit as st
from pdfplumber import open as pdf_open
import os
import re
import pandas as pd
import io
from datetime import datetime
import pytz
import difflib

def pdf_to_text(pdf_file, first_page_only=False):
    text = ""
    try:
        with pdf_open(pdf_file) as pdf:
            pages = [pdf.pages[0]] if first_page_only else pdf.pages
            for page in pages:
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
    return match.group(0) if match else ""

def get_daily_quote():
    # List of car-themed motivational quotes
    quotes = [
        "Kjør mot dine mål med Autoringen!",
        "Hver bil har en historie – finn din i dag!",
        "Akselerer mot suksess med presisjon!",
        "Autoringen: Der kvalitet møter vei!",
        "Hold deg i gir og nå dine drømmer!",
        "En god bil, en god dag – start nå!",
        "Styr mot fremtiden med selvtillit!",
        "Finn veien til den perfekte bilen!",
        "Autoringen: Din motor for muligheter!",
        "Rull videre med lidenskap og kraft!"
    ]
    # Select quote based on day of the year
    oslo_tz = pytz.timezone('Europe/Oslo')
    day_of_year = datetime.now(oslo_tz).timetuple().tm_yday
    return quotes[day_of_year % len(quotes)]

def get_daily_dinner():
    # List of healthy dinner suggestions
    dinners = [
        "Grillet kylling med søtpotet og brokkoli",
        "Ovnsbakt torsk med gulrøtter og asparges",
        "Vegetarlasagne med spinat og ricotta",
        "Grillet laks med quinoa og grønnsaker",
        "Kalkunbryst med linser og grønnkål",
        "Ovnsbakt kveite med rotgrønnsaker",
        "Kikertercurry med ris og paprika"
    ]
    # Select dinner based on day of the year
    oslo_tz = pytz.timezone('Europe/Oslo')
    day_of_year = datetime.now(oslo_tz).timetuple().tm_yday
    return dinners[(day_of_year - 1) % len(dinners)]  # Adjust for 0-based index

# Version number for the app
VERSION = "1.0.30"  # Updated to 1.0.30

# Initialize session state for mode and Easter egg
if 'mode' not in st.session_state:
    st.session_state.mode = "dark"  # Default to dark mode
if 'easter_egg_triggered' not in st.session_state:
    st.session_state.easter_egg_triggered = False
if 'search_input' not in st.session_state:
    st.session_state.search_input = ""

# Function to update mode safely
def update_mode():
    mode = st.session_state.mode_input if st.session_state.get('mode_input') in ["dark", "light"] else st.session_state.mode
    st.session_state.mode = mode

# Function to trigger Easter egg
def trigger_easter_egg():
    if st.session_state.search_input.lower() == "autoringen":
        st.session_state.easter_egg_triggered = True

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

# Display Autoringen logo with Easter egg trigger
click_count = 0
if st.button("Klikk her for logo"):
    click_count += 1
    if click_count == 3:
        st.session_state.easter_egg_triggered = True
        click_count = 0
try:
    st.image("logo.png", width=200)
except Exception as e:
    st.warning("Kunne ikke laste logo.png. Vennligst sjekk filplasseringen eller URL-en.")

st.title(f"Autoringen PDF leser (QA) v{VERSION}")

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

# Display daily quote with dynamic color
daily_quote = get_daily_quote()
quote_style = f"font-size:12px; padding:8px; margin-bottom:10px;" + \
              ("color:#333333;" if st.session_state.mode == "light" else "color:#CCCCCC;")
st.markdown(
    f"<div style='{quote_style}'><i>\"{daily_quote}\"</i></div>",
    unsafe_allow_html=True
)

# Display daily dinner suggestion with dynamic color
daily_dinner = get_daily_dinner()
dinner_style = f"font-size:12px; padding:8px; margin-bottom:20px;" + \
               ("color:#333333;" if st.session_state.mode == "light" else "color:#CCCCCC;")
st.markdown(
    f"<div style='{dinner_style}'><b>Sunn middag i dag:</b> {daily_dinner}</div>",
    unsafe_allow_html=True
)

# Easter egg display
if st.session_state.easter_egg_triggered:
    st.markdown(
        """
        <div style="font-size:16px; color:#FF4500; animation: fadeIn 2s; margin-bottom:20px;">
            Vroom! Du fant den hemmelige garasjen! 🚗✨
        </div>
        <style>
            @keyframes fadeIn {{
                from {{ opacity: 0; }}
                to {{ opacity: 1; }}
            }}
        </style>
        """,
        unsafe_allow_html=True
    )
    st.session_state.easter_egg_triggered = False  # Reset after showing

st.header("Redigerbare søkeord")

# Capture search input for Easter egg
search_input = st.text_area("Angi søkeord (én per linje)", placeholder="Skriv søkeord her", key="search_input", on_change=trigger_easter_egg)
phrases = search_input.split("\n")

uploaded_files = st.file_uploader("Last opp PDF-er", type="pdf", accept_multiple_files=True)

if uploaded_files:
    phrase_counts = {phrase.strip(): 0 for phrase in phrases if phrase.strip()}
    details = []
    detailed_data = []  # List to collect detailed data for Excel
    phrase_reg_nrs = {phrase.strip(): set() for phrase in phrases if phrase.strip()}  # Track reg nrs per phrase
    
    for uploaded_file in uploaded_files:
        with open(uploaded_file.name, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Extract full text for phrase search
        text = pdf_to_text(uploaded_file.name, first_page_only=False)
        # Extract first page text for reg nr
        first_page_text = pdf_to_text(uploaded_file.name, first_page_only=True)
        
        reg_nr = extract_reg_nr(uploaded_file.name, first_page_text)  # Extract reg nr from content or filename
        
        found_results = []
        for phrase in phrases:
            phrase = phrase.strip()
            if phrase:
                # Exact match
                exact_count = len(re.findall(re.escape(phrase), text, re.IGNORECASE))
                fuzzy_count = 0
                if exact_count == 0:
                    # Fuzzy search with difflib
                    potential_matches = re.findall(r'\bikke\b\s+\w+', text, re.IGNORECASE)
                    for potential in potential_matches:
                        if difflib.SequenceMatcher(None, phrase.lower(), potential.lower()).ratio() > 0.8:
                            fuzzy_count += 1
                total_count = exact_count + fuzzy_count
                if total_count > 0:
                    result_type = "exact" if exact_count > 0 else "fuzzy"
                    found_results.append(f'Funnet ({result_type}): "{phrase}" (Antall: {total_count})')
                    phrase_counts[phrase] += total_count
                    if reg_nr:  # Track reg nr only if it exists
                        phrase_reg_nrs[phrase].add(reg_nr)
                    # Always include in detailed data, even if reg_nr is empty
                    detailed_data.append({
                        'Filename': uploaded_file.name,
                        'Reg Nr': reg_nr,
                        'Søkeord': phrase,
                        'Antall': total_count
                    })
        
        if found_results:
            details.append((uploaded_file.name, text, found_results))
        
        if os.path.exists(uploaded_file.name):
            os.remove(uploaded_file.name)
    
    # Display summary table if there are any finds
    if any(phrase_counts.values()):
        st.markdown(f"**Søk gjennom {len(uploaded_files)} PDF dokumenter**")
        # Prepare summary DataFrame with reg nrs
        summary_data = [
            {'Søkeord': phrase, 'Totalt antall': count, 'Reg Nr': ', '.join(phrase_reg_nrs[phrase]) if phrase_reg_nrs[phrase] else ''}
            for phrase, count in phrase_counts.items() if count > 0
        ]
        df_summary = pd.DataFrame(summary_data)
        
        st.subheader("Sammendrag av funn")
        st.dataframe(df_summary)
        
        # Prepare detailed DataFrame
        df_details = pd.DataFrame(detailed_data)
        
        # Generate dynamic Excel filename with Oslo timezone
        oslo_tz = pytz.timezone('Europe/Oslo')
        current_time = datetime.now(oslo_tz).strftime("%Y-%m-%d_%H%M")
        excel_filename = f"{current_time}_{len(uploaded_files)}.xlsx"
        
        # Export to Excel with formatting
        output = io.BytesIO()
        try:
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                # Write summary sheet with file count in separate cells
                workbook = writer.book
                worksheet_summary = workbook.add_worksheet('Sammendrag')
                header_format = workbook.add_format({'bold': True})
                # Write file count text and number
                worksheet_summary.write('A1', "Antall PDF søkt gjennom:", header_format)
                worksheet_summary.write('B1', len(uploaded_files), header_format)
                # Write summary table starting at A3
                df_summary.to_excel(writer, index=False, sheet_name='Sammendrag', startrow=2)
                worksheet_summary.set_column('A:A', 30)  # Adjust width for Søkeord
                worksheet_summary.set_column('B:B', 15)  # Adjust width for Totalt antall
                worksheet_summary.set_column('C:C', 20)  # Adjust width for Reg Nr
                # Apply bold format to headers
                for col_num, value in enumerate(df_summary.columns):
                    worksheet_summary.write(2, col_num, value, header_format)
                
                # Write detailed sheet with title
                worksheet_details = workbook.add_worksheet('Detaljer')
                worksheet_details.write('A1', "Filnavn", header_format)
                df_details.to_excel(writer, index=False, sheet_name='Detaljer', startrow=2)
                for col_num, value in enumerate(df_details.columns):
                    worksheet_details.write(2, col_num, value, header_format)
                worksheet_details.set_column('A:A', 50)  # Adjust width for Filename
                worksheet_details.set_column('B:B', 15)  # Adjust width for Reg Nr
                worksheet_details.set_column('C:C', 30)  # Adjust width for Søkeord
                worksheet_details.set_column('D:D', 15)  # Adjust width for Antall
            
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