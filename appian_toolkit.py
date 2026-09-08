"""
Appian Toolkit - Unisce Enterprise Document e Record Exporter
"""

import streamlit as st
import tempfile
import zipfile
import os
from pathlib import Path

from appian_enterprise_document import scan_appian_export_with_stats, create_excel, format_coverage
from appian_record_uml import scan_record_types

# ============================================
# CONFIG
# ============================================
st.set_page_config(
    page_title="Appian Toolkit",
    page_icon="⚡",
    layout="wide"
)

# ============================================
# FUNZIONI (copiate da app.py e app_uml.py)
# ============================================

def find_appian_export_folder(base_path):
    """Trova la cartella che contiene content/, processModel/, etc."""
    base_path = Path(base_path)
    appian_folders = ['content', 'processModel', 'application', 'recordType']
    
    for af in appian_folders:
        if (base_path / af).exists():
            return base_path
    
    for item in base_path.iterdir():
        if item.is_dir() and item.name not in ['__MACOSX', '.DS_Store']:
            for af in appian_folders:
                if (item / af).exists():
                    return item
            for subitem in item.iterdir():
                if subitem.is_dir() and subitem.name not in ['__MACOSX', '.DS_Store']:
                    for af in appian_folders:
                        if (subitem / af).exists():
                            return subitem
    return base_path


def generate_dbml(records, include_static=True) -> str:
    """Genera codice DBML per dbdiagram.io (copiato da app_uml.py)"""
    
    type_map = {
        "INTEGER": "integer",
        "VARCHAR": "varchar",
        "TEXT": "text",
        "TIMESTAMP": "timestamp",
        "DATE": "date",
        "BOOLEAN": "boolean",
        "DECIMAL": "decimal",
        "DOUBLE": "double",
    }
    
    lines = [
        "// =============================================",
        "// Appian Record Types - DBML",
        "// Importa su https://dbdiagram.io",
        "// =============================================",
        ""
    ]
    
    added_refs = set()
    all_refs = []
    
    for uuid, record in records.items():
        safe_name = record.name.replace(" ", "_").replace("-", "_")
        
        is_static = "_S_" in safe_name
        if is_static and not include_static:
            continue
        
        lines.append(f"Table {safe_name} {{")
        
        for field in record.fields:
            sql_type = type_map.get(field.field_type, "varchar")
            annotations = []
            if field.is_primary_key:
                annotations.append("pk")
            annot_str = f" [{', '.join(annotations)}]" if annotations else ""
            lines.append(f"  {field.name} {sql_type}{annot_str}")
        
        lines.append("}")
        lines.append("")
        
        if not is_static:
            for rel in record.relationships:
                target = records.get(rel.target_record_uuid)
                if target and rel.source_field_name and rel.target_field_name:
                    if rel.source_field_name.lower() == "id":
                        continue
                    
                    target_name = target.name.replace(" ", "_").replace("-", "_")
                    target_is_static = "_S_" in target_name
                    if target_is_static and not include_static:
                        continue
                    
                    endpoints = tuple(sorted([
                        f"{safe_name}.{rel.source_field_name}",
                        f"{target_name}.{rel.target_field_name}"
                    ]))
                    
                    if endpoints not in added_refs:
                        added_refs.add(endpoints)
                        all_refs.append(f"Ref: {safe_name}.{rel.source_field_name} > {target_name}.{rel.target_field_name}")
    
    if all_refs:
        lines.append("// Relazioni")
        lines.extend(all_refs)
    
    return "\n".join(lines)


# ============================================
# SIDEBAR
# ============================================
with st.sidebar:
    st.title("⚡ Appian Toolkit")
    st.divider()
    
    page = st.radio(
        "Seleziona strumento:",
        ["📄 Enterprise Document", "🔗 Record Diagram"]
    )
    
    st.divider()
    st.caption("V 0.0.1")


# ============================================
# PAGINA: ENTERPRISE DOCUMENT
# ============================================
if page == "📄 Enterprise Document":
    st.title("📄 Enterprise Document Generator")
    st.markdown("Genera documentazione Excel da un export Appian")
    
    uploaded_file = st.file_uploader(
        "Carica il file ZIP dell'export Appian",
        type=['zip'],
        key="ed_uploader"
    )
    
    output_name = st.text_input(
        "Nome file Excel (senza estensione)",
        value="Enterprise_Document"
    )
    
    if st.button("🚀 Genera Documento", type="primary"):
        if uploaded_file is None:
            st.error("Carica prima un file ZIP")
        else:
            progress_bar = st.progress(0, text="Estrazione archivio...")
            
            try:
                with tempfile.TemporaryDirectory() as temp_dir:
                    progress_bar.progress(10, text="Estrazione archivio...")
                    
                    zip_path = Path(temp_dir) / "export.zip"
                    with open(zip_path, 'wb') as f:
                        f.write(uploaded_file.getvalue())
                    
                    extract_path = Path(temp_dir) / "extracted"
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(extract_path)
                    
                    export_folder = find_appian_export_folder(extract_path)
                    
                    progress_bar.progress(30, text="Scansione oggetti...")
                    objects, stats = scan_appian_export_with_stats(export_folder, verbose=False)
                    
                    progress_bar.progress(70, text="Generazione Excel...")
                    
                    if objects:
                        excel_path = Path(temp_dir) / f"{output_name}.xlsx"
                        create_excel(objects, str(excel_path))
                        
                        progress_bar.progress(100, text="Completato!")
                        
                        with open(excel_path, 'rb') as f:
                            excel_data = f.read()
                        
                        st.success(f"✅ Documento generato con {len(objects)} oggetti!")
                        
                        # Stats
                        type_counts = {}
                        for obj in objects:
                            t = obj["type"]
                            type_counts[t] = type_counts.get(t, 0) + 1
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Oggetti Totali", len(objects))
                        with col2:
                            st.metric("Tipi di Oggetto", len(type_counts))
                        with col3:
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
                        
                        # Download
                        st.download_button(
                            label="📥 Scarica Excel",
                            data=excel_data,
                            file_name=f"{output_name}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            type="primary"
                        )
                    else:
                        progress_bar.empty()
                        st.warning("Nessun oggetto trovato nell'export.")
                        
            except zipfile.BadZipFile:
                progress_bar.empty()
                st.error("File ZIP non valido")
            except Exception as e:
                progress_bar.empty()
                st.error(f"Errore: {str(e)}")


# ============================================
# PAGINA: RECORD DIAGRAM
# ============================================
elif page == "🔗 Record Diagram":
    st.title("🔗 Record Type Diagram")
    st.markdown("Genera DBML per [dbdiagram.io](https://dbdiagram.io)")
    
    with st.expander("ℹ️ Come funziona"):
        st.markdown("""
**Relazioni omesse:**
- **Relazioni inverse** - Manteniamo solo la relazione "vera" (campo FK come `idQualcosa`)
- **Duplicati** - Relazioni con stessi endpoint deduplicate
- **Tabelle statiche** (opzionale) - Le tabelle `_S_` sono lookup tables
""")
    
    include_static = st.checkbox(
        "Includi tabelle statiche (_S_)", 
        value=False,
        help="Disattivarle semplifica il diagramma"
    )
    
    uploaded_file = st.file_uploader(
        "Carica il file ZIP dell'export Appian",
        type=["zip"],
        key="rd_uploader"
    )
    
    if uploaded_file is not None:
        with st.spinner("Elaborazione..."):
            with tempfile.TemporaryDirectory() as temp_dir:
                zip_path = os.path.join(temp_dir, "export.zip")
                
                with open(zip_path, 'wb') as f:
                    f.write(uploaded_file.getvalue())
                
                extract_dir = os.path.join(temp_dir, "extracted")
                os.makedirs(extract_dir)
                
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    for member in zip_ref.namelist():
                        if '__MACOSX' in member or member.startswith('._') or '/._' in member:
                            continue
                        zip_ref.extract(member, extract_dir)
                
                export_folder = find_appian_export_folder(extract_dir)
                records = scan_record_types(str(export_folder))
                
                if not records:
                    st.error("Nessun Record Type trovato.")
                else:
                    static_count = sum(1 for r in records.values() if "_S_" in r.name)
                    non_static_count = len(records) - static_count
                    
                    st.success(f"✅ Trovati **{len(records)}** Record Type ({non_static_count} entità, {static_count} statiche)")
                    
                    output = generate_dbml(records, include_static=include_static)
                    st.code(output, language="sql")
                    
                    st.download_button(
                        label="📥 Scarica DBML",
                        data=output,
                        file_name="appian_records.dbml",
                        mime="text/plain",
                        type="primary"
                    )
                    
                    st.link_button("🔗 Apri dbdiagram.io", "https://dbdiagram.io/d")
