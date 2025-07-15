import streamlit as st
import io
import tempfile
import os
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import base64

# Configurazione della pagina
st.set_page_config(
    page_title="Numeratore PDF",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

def create_page_number_overlay(page_num, page_width, page_height, font_size=12, font_name="Helvetica"):
    """
    Crea un overlay PDF con solo il numero di pagina nell'angolo in alto a destra.
    
    Args:
        page_num (int): Il numero di pagina da mostrare
        page_width (float): Larghezza della pagina in punti
        page_height (float): Altezza della pagina in punti
        font_size (int): Dimensione del font per il numero di pagina
        font_name (str): Nome del font da utilizzare
    
    Returns:
        PdfReader: Un oggetto reader PDF contenente l'overlay del numero di pagina
    """
    # Crea un buffer di bytes per contenere il PDF
    packet = io.BytesIO()
    
    # Crea un nuovo PDF con il numero di pagina
    can = canvas.Canvas(packet, pagesize=(page_width, page_height))
    
    # Imposta il font
    can.setFont(font_name, font_size)
    
    # Posizione per l'angolo in alto a destra (con margine)
    x_pos = page_width - 15  # 50 punti dal bordo destro
    y_pos = page_height - 15  # 30 punti dal bordo superiore
    
    # Disegna il numero di pagina
    can.drawRightString(x_pos, y_pos, str(page_num))
    
    # Salva il PDF
    can.save()
    
    # Sposta la posizione del buffer all'inizio
    packet.seek(0)
    
    # Crea un PdfReader dal buffer
    return PdfReader(packet)

def add_page_numbers_to_pdf(pdf_bytes, start_page=1, end_page=None, font_size=12, font_name="Helvetica"):
    """
    Aggiunge numeri di pagina progressivi a un file PDF.
    
    Args:
        pdf_bytes (bytes): Contenuto del file PDF come bytes
        start_page (int): Numero di pagina iniziale (default: 1)
        end_page (int): Numero di pagina finale (default: None, tutte le pagine)
        font_size (int): Dimensione del font per i numeri di pagina (default: 12)
        font_name (str): Nome del font da utilizzare (default: "Helvetica")
    
    Returns:
        bytes: PDF modificato come bytes
    """
    try:
        # Crea un oggetto BytesIO dai bytes di input
        input_stream = io.BytesIO(pdf_bytes)
        
        # Apri il PDF
        reader = PdfReader(input_stream)
        writer = PdfWriter()
        
        total_pages = len(reader.pages)
        
        # Se end_page non è specificato, usa tutte le pagine
        if end_page is None:
            end_page = total_pages
        
        # Crea barra di progresso
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Processa ogni pagina
        for page_idx, page in enumerate(reader.pages):
            # Salta le pagine prima della pagina iniziale o dopo quella finale
            if page_idx + 1 < start_page or page_idx + 1 > end_page:
                # Aggiungi la pagina senza numerazione
                writer.add_page(page)
                continue
                
            current_page_num = start_page + (page_idx + 1 - start_page)
            
            # Aggiorna il progresso
            progress = (page_idx + 1) / total_pages
            progress_bar.progress(progress)
            status_text.text(f"Elaborazione pagina {page_idx + 1} di {total_pages}...")
            
            # Ottieni le dimensioni della pagina
            page_width = float(page.mediabox.width)
            page_height = float(page.mediabox.height)
            
            # Crea overlay del numero di pagina
            overlay_reader = create_page_number_overlay(
                current_page_num, 
                page_width, 
                page_height, 
                font_size, 
                font_name
            )
            
            # Unisci l'overlay del numero di pagina con la pagina originale
            overlay_page = overlay_reader.pages[0]
            page.merge_page(overlay_page)
            
            # Aggiungi la pagina modificata al writer
            writer.add_page(page)
        
        # Scrivi nel buffer di output
        output_stream = io.BytesIO()
        writer.write(output_stream)
        output_stream.seek(0)
        
        # Pulisci gli indicatori di progresso
        progress_bar.empty()
        status_text.empty()
        
        return output_stream.getvalue()
        
    except Exception as e:
        st.error(f"Errore durante l'elaborazione del PDF: {str(e)}")
        return None

# Titolo e descrizione dell'app
st.title("📄 Numeratore PDF")
st.markdown("Carica un file PDF e aggiungi numeri di pagina progressivi nell'angolo in alto a destra di ogni pagina.")

# Barra laterale per le impostazioni
st.sidebar.header("Impostazioni")

# Caricamento file
uploaded_file = st.file_uploader(
    "Scegli un file PDF", 
    type="pdf",
    help="Carica un file PDF per aggiungere i numeri di pagina"
)

if uploaded_file is not None:
    # Mostra informazioni sul file
    st.success(f"✅ File caricato: {uploaded_file.name}")
    
    # Leggi il PDF per ottenere il numero di pagine
    try:
        pdf_bytes = uploaded_file.read()
        reader = PdfReader(io.BytesIO(pdf_bytes))
        total_pages = len(reader.pages)
        st.info(f"📊 Pagine totali nel PDF: {total_pages}")
        
        # Impostazioni nella barra laterale
        st.sidebar.subheader("Impostazioni Numerazione")
        
        start_page = st.sidebar.number_input(
            "Numero di pagina iniziale",
            min_value=1,
            max_value=9999,
            value=1,
            help="Il numero da cui iniziare il conteggio"
        )
        
        end_page = st.sidebar.number_input(
            "Numero di pagina finale",
            min_value=start_page,
            max_value=total_pages,
            value=total_pages,
            help="L'ultima pagina da numerare"
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
        
        # Pulsante di elaborazione
        if st.button("🔢 Aggiungi Numeri di Pagina", type="primary"):
            with st.spinner("Elaborazione PDF in corso... Attendere prego."):
                # Aggiungi numeri di pagina
                numbered_pdf = add_page_numbers_to_pdf(
                    pdf_bytes, 
                    start_page, 
                    end_page,
                    font_size, 
                    font_name
                )
                
                if numbered_pdf:
                    st.success("✅ Numeri di pagina aggiunti con successo!")
                    
                    # Crea pulsante di download
                    original_name = uploaded_file.name
                    base_name = os.path.splitext(original_name)[0]
                    output_name = f"{base_name}_numerato.pdf"
                    
                    st.download_button(
                        label="📥 Scarica PDF Numerato",
                        data=numbered_pdf,
                        file_name=output_name,
                        mime="application/pdf",
                        type="secondary"
                    )
                    
                    # Mostra messaggio di successo con dettagli
                    st.markdown("---")
                    st.markdown("### ✨ Elaborazione Completata!")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Pagine Elaborate", total_pages)
                    with col2:
                        st.metric("Numero Iniziale", start_page)
                    with col3:
                        st.metric("Dimensione Font", font_size)
                
    except Exception as e:
        st.error(f"Errore nella lettura del file PDF: {str(e)}")

else:
    # Istruzioni quando nessun file è caricato
    st.markdown("---")
    st.markdown("### 📋 Istruzioni:")
    st.markdown("""
    1. **Carica** un file PDF utilizzando il caricatore di file qui sopra
    2. **Configura** le impostazioni nella barra laterale (numero di pagina iniziale, dimensione font, ecc.)
    3. **Clicca** "Aggiungi Numeri di Pagina" per elaborare il PDF
    4. **Scarica** il file PDF numerato
    """)
