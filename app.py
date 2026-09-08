"""
Appian Enterprise Document Generator - Web Interface
"""

import streamlit as st
import zipfile
import tempfile
from pathlib import Path

# Importa le funzioni dal modulo principale
from appian_enterprise_document import scan_appian_export_with_stats, create_excel, format_coverage


st.set_page_config(
    page_title="Appian Enterprise Document Generator",
    layout="centered"
)

# Custom CSS per un look professionale
st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: 600;
        color: #1F4E79;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .stat-box {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
    }
    .stat-number {
        font-size: 2rem;
        font-weight: bold;
        color: #1F4E79;
    }
    .stat-label {
        font-size: 0.9rem;
        color: #666;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<p class="main-header">Appian Enterprise Document Generator</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Genera automaticamente la documentazione degli oggetti da un export Appian</p>', unsafe_allow_html=True)

# Divider
st.divider()

# Upload section
st.subheader("1. Carica l'export Appian")

uploaded_file = st.file_uploader(
    "Trascina qui il file ZIP dell'export Appian",
    type=['zip'],
    help="Esporta l'applicazione da Appian Designer e carica il file .zip"
)

# Nome file output
st.subheader("2. Nome del documento")
output_name = st.text_input(
    "Nome file Excel (senza estensione)",
    value="Enterprise_Document",
    help="Il file verra salvato come [nome].xlsx"
)

# Generate button
st.subheader("3. Genera il documento")

if st.button("Genera Enterprise Document", type="primary", use_container_width=True):
    
    if uploaded_file is None:
        st.error("Carica prima un file ZIP")
    else:
        # Progress bar
        progress_bar = st.progress(0, text="Estrazione archivio...")
        
        try:
            # Crea cartella temporanea
            with tempfile.TemporaryDirectory() as temp_dir:
                # Estrai lo ZIP
                progress_bar.progress(10, text="Estrazione archivio...")
                
                zip_path = Path(temp_dir) / "export.zip"
                with open(zip_path, 'wb') as f:
                    f.write(uploaded_file.getvalue())
                
                extract_path = Path(temp_dir) / "extracted"
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_path)
                
                # Trova la cartella principale dell'export Appian
                # Cerca ricorsivamente la cartella che contiene le sottocartelle tipiche di Appian
                def find_appian_export_folder(base_path):
                    """Trova la cartella che contiene content/, processModel/, etc."""
                    appian_folders = ['content', 'processModel', 'application', 'recordType']
                    
                    # Controlla se base_path e' gia' la cartella giusta
                    for af in appian_folders:
                        if (base_path / af).exists():
                            return base_path
                    
                    # Cerca nelle sottocartelle (escludendo __MACOSX)
                    for item in base_path.iterdir():
                        if item.is_dir() and item.name != '__MACOSX':
                            for af in appian_folders:
                                if (item / af).exists():
                                    return item
                            # Cerca un livello piu' in profondita'
                            for subitem in item.iterdir():
                                if subitem.is_dir() and subitem.name != '__MACOSX':
                                    for af in appian_folders:
                                        if (subitem / af).exists():
                                            return subitem
                    return base_path
                
                export_folder = find_appian_export_folder(extract_path)
                
                progress_bar.progress(30, text="Scansione oggetti Appian...")
                
                # Scansiona l'export
                objects, stats = scan_appian_export_with_stats(export_folder, verbose=False)
                
                progress_bar.progress(70, text="Generazione Excel...")
                
                if objects:
                    # Genera Excel in memoria
                    excel_path = Path(temp_dir) / f"{output_name}.xlsx"
                    create_excel(objects, str(excel_path))
                    
                    progress_bar.progress(100, text="Completato!")
                    
                    # Leggi il file per il download
                    with open(excel_path, 'rb') as f:
                        excel_data = f.read()
                    
                    # Mostra statistiche
                    st.success(f"Documento generato con successo!")
                    
                    # Stats
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Oggetti Totali", len(objects))
                    
                    # Conta per tipo
                    type_counts = {}
                    for obj in objects:
                        t = obj["type"]
                        type_counts[t] = type_counts.get(t, 0) + 1
                    
                    with col2:
                        st.metric("Tipi di Oggetto", len(type_counts))
                    
                    with col3:
                        # Trova il tipo piu comune
                        most_common = max(type_counts, key=type_counts.get)
                        st.metric("Tipo Principale", most_common)

                    # Controllo copertura: quanti file XML dell'export non hanno prodotto un oggetto
                    missed = len(stats["unparsed"])
                    if missed:
                        st.warning(
                            f"{missed} file su {stats['files_scanned']} non hanno prodotto un oggetto: "
                            "potrebbero esserci tipi non gestiti."
                        )
                    else:
                        st.caption(
                            f"Copertura 100%: tutti i {stats['files_scanned']} file XML dell'export "
                            "hanno prodotto un oggetto."
                        )
                    with st.expander("Dettaglio controllo copertura"):
                        st.code(format_coverage(stats), language="text")
                    
                    # Dettaglio per tipo
                    st.subheader("Riepilogo per tipo")
                    
                    # Ordina per quantita decrescente
                    sorted_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)
                    
                    # Mostra come tabella
                    col_a, col_b = st.columns(2)
                    half = len(sorted_types) // 2 + len(sorted_types) % 2
                    
                    with col_a:
                        for t, count in sorted_types[:half]:
                            st.write(f"**{t}**: {count}")
                    
                    with col_b:
                        for t, count in sorted_types[half:]:
                            st.write(f"**{t}**: {count}")
                    
                    # Download button
                    st.divider()
                    st.download_button(
                        label="Scarica Enterprise Document",
                        data=excel_data,
                        file_name=f"{output_name}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary",
                        use_container_width=True
                    )
                    
                else:
                    progress_bar.empty()
                    st.warning("Nessun oggetto trovato nell'export. Verifica che il file ZIP sia un export valido di Appian.")
                    
        except zipfile.BadZipFile:
            progress_bar.empty()
            st.error("Il file caricato non e un archivio ZIP valido")
        except Exception as e:
            progress_bar.empty()
            st.error(f"Errore durante l'elaborazione: {str(e)}")

# Footer
st.divider()
st.caption("Appian Enterprise Document Generator v1.0")
