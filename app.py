import streamlit as st
import io
import os
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import re

# Configurazione della pagina
st.set_page_config(
    page_title="Numeratore PDF",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

def parse_page_selection(selection_text, total_pages):
    """Parses a string like '1,3,5-7' into a sorted list of valid page numbers."""
    pages = set()
    try:
        parts = selection_text.split(',')
        for part in parts:
            if '-' in part:
                start, end = map(int, part.split('-'))
                pages.update(range(start, end + 1))
            else:
                pages.add(int(part))
        return sorted([p for p in pages if 1 <= p <= total_pages])
    except Exception:
        raise ValueError("Formato non valido. Usa numeri o intervalli tipo '1,3,5-7'.")

def create_page_number_overlay(page_num, page_width, page_height, font_size=12, font_name="Helvetica"):
    """
    Crea un overlay PDF con il numero di pagina in un box blu nell'angolo in alto a destra.
    """
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=(page_width, page_height))
    can.setFont(font_name, font_size)

    text = str(page_num)
    x_text = page_width - 25
    y_text = page_height - 25

    # Disegna il numero (blu)
    can.setFillColorRGB(0, 0, 0)
    can.drawRightString(x_text, y_text, text)

    # Calcola dimensione del box
    text_width = pdfmetrics.stringWidth(text, font_name, font_size)
    padding = 4
    box_x = x_text - text_width - padding
    box_y = y_text - padding
    box_width = text_width + 2 * padding
    box_height = font_size + padding

    # Disegna rettangolo blu sottile
    can.setLineWidth(0.5)
    can.setStrokeColorRGB(0, 0, 1)
    can.rect(box_x, box_y, box_width, box_height)

    can.save()
    packet.seek(0)
    return PdfReader(packet)

def add_page_numbers_to_pdf(pdf_bytes, selected_pages, font_size=12, font_name="Helvetica"):
    try:
        input_stream = io.BytesIO(pdf_bytes)
        reader = PdfReader(input_stream)
        writer = PdfWriter()
        total_pages = len(reader.pages)

        progress_bar = st.progress(0)
        status_text = st.empty()

        for page_idx, page in enumerate(reader.pages):
            page_number = page_idx + 1
            progress = page_number / total_pages
            progress_bar.progress(progress)
            status_text.text(f"Elaborazione pagina {page_number} di {total_pages}...")

            if page_number in selected_pages:
                page_width = float(page.mediabox.width)
                page_height = float(page.mediabox.height)
                overlay_reader = create_page_number_overlay(
                    page_number, page_width, page_height, font_size, font_name
                )
                overlay_page = overlay_reader.pages[0]
                page.merge_page(overlay_page)

            writer.add_page(page)

        output_stream = io.BytesIO()
        writer.write(output_stream)
        output_stream.seek(0)

        progress_bar.empty()
        status_text.empty()

        return output_stream.getvalue()

    except Exception as e:
        st.error(f"Errore durante l'elaborazione del PDF: {str(e)}")
        return None

# Titolo e descrizione dell'app
st.title("📄 Numeratore PDF")
st.markdown("Carica un file PDF e aggiungi numeri di pagina in alto a destra in un riquadro blu.")

# Barra laterale per le impostazioni
st.sidebar.header("Impostazioni")

# Caricamento file
uploaded_file = st.file_uploader(
    "Scegli un file PDF", 
    type="pdf",
    help="Carica un file PDF per aggiungere i numeri di pagina"
)

if uploaded_file is not None:
    st.success(f"✅ File caricato: {uploaded_file.name}")

    try:
        pdf_bytes = uploaded_file.read()
        reader = PdfReader(io.BytesIO(pdf_bytes))
        total_pages = len(reader.pages)
        st.info(f"📊 Pagine totali nel PDF: {total_pages}")

        st.sidebar.subheader("Numerazione personalizzata")

        page_selection = st.sidebar.text_input(
            "Pagine da numerare (es. 1,3,5-7)",
            value="1",
            help="Specifica le pagine da numerare. Usa virgole e trattini (es. 1,3,5-7)."
        )

        font_size = st.sidebar.slider(
            "Dimensione carattere",
            min_value=8,
            max_value=24,
            value=12,
            help="Dimensione del testo del numero di pagina"
        )

        font_name = st.sidebar.selectbox(
            "Stile carattere",
            options=["Helvetica", "Times-Roman", "Courier"],
            index=0,
            help="Stile del carattere per i numeri di pagina"
        )

        if st.button("🔢 Aggiungi Numeri di Pagina", type="primary"):
            try:
                selected_pages = parse_page_selection(page_selection, total_pages)
                if not selected_pages:
                    st.warning("⚠️ Nessuna pagina valida selezionata.")
                else:
                    with st.spinner("Elaborazione PDF in corso... Attendere prego."):
                        numbered_pdf = add_page_numbers_to_pdf(
                            pdf_bytes,
                            selected_pages,
                            font_size,
                            font_name
                        )
                        if numbered_pdf:
                            st.success("✅ Numeri di pagina aggiunti con successo!")

                            output_name = f"{os.path.splitext(uploaded_file.name)[0]}_numerato.pdf"
                            st.download_button(
                                label="📥 Scarica PDF Numerato",
                                data=numbered_pdf,
                                file_name=output_name,
                                mime="application/pdf",
                                type="secondary"
                            )

                            st.markdown("---")
                            st.markdown("### ✨ Dettagli elaborazione")
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Pagine Elaborate", total_pages)
                            with col2:
                                st.metric("Pagine Numerate", len(selected_pages))
                            with col3:
                                st.metric("Dimensione Font", font_size)
            except ValueError as e:
                st.error(f"❌ Errore: {e}")

    except Exception as e:
        st.error(f"Errore nella lettura del file PDF: {str(e)}")

else:
    st.markdown("---")
    st.markdown("### 📋 Istruzioni:")
    st.markdown("""
    1. **Carica** un file PDF utilizzando il caricatore qui sopra
    2. **Inserisci** le pagine da numerare (es. `1`, `2,5`, `1-3,6`)
    3. **Configura** lo stile del numero (font, dimensione)
    4. **Clicca** su "Aggiungi Numeri di Pagina"
    5. **Scarica** il file PDF risultante
    """)