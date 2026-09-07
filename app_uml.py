#!/usr/bin/env python3
"""
Appian Record Type Exporter
Esporta i Record Type di Appian in formato DBML o CSV.
"""

import streamlit as st
import tempfile
import zipfile
import os

from appian_record_uml import scan_record_types


def find_appian_export_folder(base_path: str) -> str:
    """Trova la cartella principale dell'export Appian."""
    for item in os.listdir(base_path):
        if item.startswith('._') or item == '__MACOSX':
            continue
        item_path = os.path.join(base_path, item)
        if os.path.isdir(item_path):
            if item == 'recordType':
                return base_path
            for root, dirs, files in os.walk(item_path):
                if 'recordType' in dirs:
                    return item_path
    return base_path


def generate_dbml(records, include_static=True) -> str:
    """Genera codice DBML per dbdiagram.io"""
    
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
    
    # Traccia relazioni già aggiunte per evitare duplicati
    added_refs = set()
    all_refs = []
    
    for uuid, record in records.items():
        safe_name = record.name.replace(" ", "_").replace("-", "_")
        
        # Salta tabelle statiche se non richieste
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
        
        # Raccogli relazioni solo da tabelle NON statiche
        # e solo dove il campo sorgente NON è "id" (altrimenti è una relazione inversa)
        if not is_static:
            for rel in record.relationships:
                target = records.get(rel.target_record_uuid)
                if target and rel.source_field_name and rel.target_field_name:
                    # Salta relazioni inverse (dove sorgente è "id")
                    if rel.source_field_name.lower() == "id":
                        continue
                    
                    target_name = target.name.replace(" ", "_").replace("-", "_")
                    
                    # Se non includiamo le statiche, salta relazioni verso statiche
                    target_is_static = "_S_" in target_name
                    if target_is_static and not include_static:
                        continue
                    
                    # Chiave univoca per la relazione (ordina per evitare duplicati bidirezionali)
                    endpoints = tuple(sorted([
                        f"{safe_name}.{rel.source_field_name}",
                        f"{target_name}.{rel.target_field_name}"
                    ]))
                    
                    if endpoints not in added_refs:
                        added_refs.add(endpoints)
                        all_refs.append(f"Ref: {safe_name}.{rel.source_field_name} > {target_name}.{rel.target_field_name}")
    
    # Aggiungi relazioni alla fine
    if all_refs:
        lines.append("// Relazioni")
        lines.extend(all_refs)
    
    return "\n".join(lines)


st.set_page_config(page_title="Appian Record Exporter", layout="centered")

st.title("Appian Record Type Exporter")
st.markdown("Esporta i Record Type in DBML per [dbdiagram.io](https://dbdiagram.io)")

# Info box con spiegazione
with st.expander("ℹ️ Come funziona e quali relazioni vengono esportate"):
    st.markdown("""
**Cosa fa questo tool:**
- Analizza i Record Type dall'export Appian (file ZIP)
- Estrae campi e relazioni definite esplicitamente
- Genera un file DBML importabile su [dbdiagram.io](https://dbdiagram.io)

**Relazioni omesse per evitare errori su dbdiagram:**

1. **Relazioni inverse** - In Appian, quando crei una relazione A→B, viene spesso creata 
   automaticamente anche la relazione inversa B→A. Manteniamo solo la relazione "vera" 
   (quella con il campo FK come `idQualcosa`), non quella inversa (dove il campo sorgente è `id`).
   
2. **Duplicati** - Relazioni con gli stessi endpoint vengono deduplicate.

3. **Tabelle statiche** (opzionale) - Le tabelle con `_S_` nel nome sono lookup tables. 
   Escluderle semplifica molto il diagramma.

**Nota:** Se un campo come `idProcedura` non ha una relazione nel diagramma, significa che 
in Appian non è stata configurata esplicitamente la relazione nel Record Type.
""")

# Opzione per includere tabelle statiche (PRIMA del caricamento)
include_static = st.checkbox(
    "Includi tabelle statiche (_S_)", 
    value=False,
    help="Le tabelle statiche sono lookup/reference tables. Disattivarle semplifica il diagramma."
)

uploaded_file = st.file_uploader("Carica il file ZIP dell'export Appian", type=["zip"])

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
            records = scan_record_types(export_folder)
            
            if not records:
                st.error("Nessun Record Type trovato.")
            else:
                # Conta tabelle statiche e non
                static_count = sum(1 for r in records.values() if "_S_" in r.name)
                non_static_count = len(records) - static_count
                
                st.success(f"Trovati **{len(records)}** Record Type ({non_static_count} entità, {static_count} statiche)")
                
                output = generate_dbml(records, include_static=include_static)
                st.code(output, language="sql")
                
                st.download_button(
                    label="Scarica appian_records.dbml",
                    data=output,
                    file_name="appian_records.dbml",
                    mime="text/plain"
                )
