#!/usr/bin/env python3
"""
Genera file DBML per dbdiagram.io dai Record Type di Appian.
"""

from appian_record_uml import scan_record_types
import sys

def generate_dbml(export_path: str) -> str:
    """Genera codice DBML dai Record Type."""
    
    records = scan_record_types(export_path)
    
    if not records:
        return "// Nessun Record Type trovato"
    
    # Mappa tipi Appian -> SQL
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
        "// Generato automaticamente da export Appian",
        "// Importa su https://dbdiagram.io",
        "// =============================================",
        ""
    ]
    
    # Genera tabelle
    for uuid, record in records.items():
        # Nome tabella safe per SQL
        safe_name = record.name.replace(" ", "_").replace("-", "_")
        
        lines.append(f"Table {safe_name} {{")
        
        # Identifica campi FK per questo record
        fk_fields = {rel.source_field_uuid for rel in record.relationships}
        
        for field in record.fields:
            sql_type = type_map.get(field.field_type, "varchar")
            
            # Annotazioni
            annotations = []
            if field.is_primary_key:
                annotations.append("pk")
            if field.uuid in fk_fields:
                # Trova la relazione per questo campo
                for rel in record.relationships:
                    if rel.source_field_uuid == field.uuid:
                        target = records.get(rel.target_record_uuid)
                        if target:
                            target_name = target.name.replace(" ", "_").replace("-", "_")
                            annotations.append(f"ref: > {target_name}.{rel.target_field_name}")
                        break
            
            annot_str = f" [{', '.join(annotations)}]" if annotations else ""
            lines.append(f"  {field.name} {sql_type}{annot_str}")
        
        lines.append("}")
        lines.append("")
    
    return "\n".join(lines)


if __name__ == "__main__":
    export_path = sys.argv[1] if len(sys.argv) > 1 else "."
    output_file = sys.argv[2] if len(sys.argv) > 2 else "appian_records.dbml"
    
    dbml = generate_dbml(export_path)
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(dbml)
    
    print(dbml)
    print()
    print(f"File salvato: {output_file}")
