#!/usr/bin/env python3
"""
Appian Record Type UML Generator
Genera diagrammi UML delle relazioni tra Record Type di Appian.
Supporta output in formato PlantUML e Mermaid.
"""

import os
import sys
import xml.etree.ElementTree as ET
import json
import argparse
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class RecordField:
    """Rappresenta un campo di un Record Type."""
    uuid: str
    name: str
    display_name: str = ""
    field_type: str = ""
    is_primary_key: bool = False


@dataclass
class RecordRelationship:
    """Rappresenta una relazione tra Record Type."""
    uuid: str
    name: str
    target_record_uuid: str
    relationship_type: str  # MANY_TO_ONE, ONE_TO_MANY, MANY_TO_MANY
    source_field_uuid: str = ""
    target_field_uuid: str = ""
    source_field_name: str = ""  # Nome del campo FK
    target_field_name: str = ""  # Nome del campo PK target


@dataclass
class RecordType:
    """Rappresenta un Record Type di Appian."""
    uuid: str
    name: str
    description: str = ""
    fields: List[RecordField] = field(default_factory=list)
    relationships: List[RecordRelationship] = field(default_factory=list)


def parse_record_type_file(file_path: str) -> Optional[RecordType]:
    """Parsa un file XML di Record Type e restituisce l'oggetto RecordType."""
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Namespace Appian
        ns = {'a': 'http://www.appian.com/ae/types/2009'}
        
        # Cerca il tag recordType (con o senza namespace)
        record_type_elem = root.find('recordType', ns)
        if record_type_elem is None:
            record_type_elem = root.find('.//recordType')
        if record_type_elem is None:
            # Cerca senza namespace specifico
            for elem in root.iter():
                local_tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if local_tag == 'recordType':
                    record_type_elem = elem
                    break
        
        if record_type_elem is None:
            return None
        
        # Estrai UUID e nome dagli attributi
        uuid = ""
        name = ""
        
        # Prova prima con namespace, poi senza
        uuid = record_type_elem.attrib.get('{http://www.appian.com/ae/types/2009}uuid', '')
        if not uuid:
            uuid = record_type_elem.attrib.get('uuid', '')
        
        name = record_type_elem.attrib.get('name', '')
        
        if not uuid:
            # Prova a estrarre dall'UUID del file
            uuid = os.path.splitext(os.path.basename(file_path))[0]
        
        # Cerca descrizione
        description = ""
        for elem in record_type_elem.iter():
            if elem.tag.endswith('description') and elem.text:
                description = elem.text.strip()
                break
        
        record = RecordType(uuid=uuid, name=name, description=description)
        
        # Dizionario per mappare UUID campo -> nome campo
        field_uuid_to_name: Dict[str, str] = {}
        
        # Estrai i campi dalla sourceConfiguration (campi reali del database)
        for elem in root.iter():
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            if tag == 'field':
                field_uuid = ""
                field_name = ""
                display_name = ""
                field_type = ""
                
                for child in elem:
                    child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                    if child_tag == 'uuid' and child.text:
                        field_uuid = child.text.strip()
                    elif child_tag == 'fieldName' and child.text:
                        field_name = child.text.strip()
                    elif child_tag == 'displayName' and child.text:
                        display_name = child.text.strip()
                    elif child_tag == 'sourceFieldType' and child.text:
                        field_type = child.text.strip()
                
                if field_uuid and field_name:
                    # Determina se è PK (primo campo "id" tipicamente)
                    is_pk = field_name.lower() == 'id'
                    
                    record.fields.append(RecordField(
                        uuid=field_uuid,
                        name=field_name,
                        display_name=display_name or field_name,
                        field_type=field_type,
                        is_primary_key=is_pk
                    ))
                    field_uuid_to_name[field_uuid] = field_name
        
        # Estrai le relazioni (recordRelationshipCfg)
        for elem in root.iter():
            if elem.tag.endswith('recordRelationshipCfg'):
                rel_uuid = ""
                rel_name = ""
                target_uuid = ""
                rel_type = ""
                source_field = ""
                target_field = ""
                
                for child in elem:
                    tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                    
                    if tag == 'uuid' and child.text:
                        rel_uuid = child.text.strip()
                    elif tag == 'relationshipName' and child.text:
                        rel_name = child.text.strip()
                    elif tag == 'targetRecordTypeUuid' and child.text:
                        target_uuid = child.text.strip()
                    elif tag == 'relationshipType' and child.text:
                        rel_type = child.text.strip()
                    elif tag == 'relationshipData' and child.text:
                        try:
                            data = json.loads(child.text.strip())
                            source_field = data.get('sourceRecordTypeFieldUuid', '')
                            target_field = data.get('targetRecordTypeFieldUuid', '')
                        except json.JSONDecodeError:
                            pass
                
                if target_uuid and rel_type:
                    # Risolvi il nome del campo sorgente
                    source_field_name = field_uuid_to_name.get(source_field, "")
                    
                    record.relationships.append(RecordRelationship(
                        uuid=rel_uuid,
                        name=rel_name,
                        target_record_uuid=target_uuid,
                        relationship_type=rel_type,
                        source_field_uuid=source_field,
                        target_field_uuid=target_field,
                        source_field_name=source_field_name
                    ))
        
        return record
        
    except Exception as e:
        print(f"Errore nel parsing di {file_path}: {e}", file=sys.stderr)
        return None


def scan_record_types(export_path: str) -> Dict[str, RecordType]:
    """Scansiona la cartella di export e restituisce tutti i Record Type."""
    records: Dict[str, RecordType] = {}
    
    for root_dir, dirs, files in os.walk(export_path):
        # Salta cartelle MacOS
        if '__MACOSX' in root_dir:
            continue
        
        # Cerca cartelle recordType
        if os.path.basename(root_dir) == 'recordType':
            for file_name in files:
                if file_name.startswith('._') or not file_name.endswith('.xml'):
                    continue
                
                file_path = os.path.join(root_dir, file_name)
                record = parse_record_type_file(file_path)
                
                if record:
                    records[record.uuid] = record
    
    # Post-processing: risolvi i nomi dei campi target nelle relazioni
    resolve_target_field_names(records)
    
    return records


def resolve_target_field_names(records: Dict[str, RecordType]) -> None:
    """Risolve i nomi dei campi target (PK) nelle relazioni."""
    # Crea un dizionario globale UUID campo -> nome campo
    all_fields: Dict[str, str] = {}
    for record in records.values():
        for f in record.fields:
            all_fields[f.uuid] = f.name
    
    # Aggiorna le relazioni con i nomi dei campi target
    for record in records.values():
        for rel in record.relationships:
            if rel.target_field_uuid and rel.target_field_uuid in all_fields:
                rel.target_field_name = all_fields[rel.target_field_uuid]


def generate_plantuml(records: Dict[str, RecordType], show_fields: bool = False) -> str:
    """Genera il codice PlantUML per il diagramma delle relazioni."""
    lines = [
        "@startuml",
        "' Appian Record Type Relationships",
        "' Generated by Appian Record UML Generator",
        "",
        "skinparam class {",
        "    BackgroundColor #F5F5F5",
        "    BorderColor #333333",
        "    ArrowColor #333333",
        "}",
        "",
        "hide circle",
        ""
    ]
    
    # Definisci le entità (Record Type)
    for uuid, record in records.items():
        safe_name = record.name.replace(" ", "_").replace("-", "_")
        
        if show_fields and record.fields:
            lines.append(f'class "{record.name}" as {safe_name} {{')
            for f in record.fields[:10]:  # Limita a 10 campi per leggibilità
                lines.append(f"    {f.name}")
            if len(record.fields) > 10:
                lines.append(f"    ... (+{len(record.fields) - 10} altri)")
            lines.append("}")
        else:
            lines.append(f'class "{record.name}" as {safe_name}')
    
    lines.append("")
    
    # Definisci le relazioni
    for uuid, record in records.items():
        source_name = record.name.replace(" ", "_").replace("-", "_")
        
        for rel in record.relationships:
            if rel.target_record_uuid in records:
                target_record = records[rel.target_record_uuid]
                target_name = target_record.name.replace(" ", "_").replace("-", "_")
                
                # Determina il tipo di freccia in base alla cardinalità
                if rel.relationship_type == "MANY_TO_ONE":
                    arrow = "}o--||"
                    label = f": {rel.name} (N:1)"
                elif rel.relationship_type == "ONE_TO_MANY":
                    arrow = "||--o{"
                    label = f": {rel.name} (1:N)"
                elif rel.relationship_type == "MANY_TO_MANY":
                    arrow = "}o--o{"
                    label = f": {rel.name} (N:N)"
                else:
                    arrow = "--"
                    label = f": {rel.name}"
                
                lines.append(f'{source_name} {arrow} {target_name} {label}')
    
    lines.append("")
    lines.append("@enduml")
    
    return "\n".join(lines)


def generate_mermaid(records: Dict[str, RecordType], show_fields: bool = False) -> str:
    """Genera il codice Mermaid per il diagramma delle relazioni."""
    lines = [
        "erDiagram",
        "    %% Appian Record Type Relationships",
        "    %% Generated by Appian Record UML Generator",
        ""
    ]
    
    # In Mermaid ER, definiamo prima le entità con i loro attributi
    if show_fields:
        for uuid, record in records.items():
            safe_name = record.name.replace(" ", "_").replace("-", "_")
            lines.append(f'    {safe_name} {{')
            for f in record.fields[:8]:  # Limita per leggibilità
                field_name = f.name.replace(" ", "_")
                lines.append(f'        string {field_name}')
            lines.append("    }")
        lines.append("")
    
    # Definisci le relazioni
    added_relations = set()
    
    for uuid, record in records.items():
        source_name = record.name.replace(" ", "_").replace("-", "_")
        
        for rel in record.relationships:
            if rel.target_record_uuid in records:
                target_record = records[rel.target_record_uuid]
                target_name = target_record.name.replace(" ", "_").replace("-", "_")
                
                # Evita duplicati
                rel_key = tuple(sorted([source_name, target_name]))
                if rel_key in added_relations:
                    continue
                added_relations.add(rel_key)
                
                # Determina la cardinalità Mermaid
                if rel.relationship_type == "MANY_TO_ONE":
                    cardinality = "}o--||"
                elif rel.relationship_type == "ONE_TO_MANY":
                    cardinality = "||--o{"
                elif rel.relationship_type == "MANY_TO_MANY":
                    cardinality = "}o--o{"
                else:
                    cardinality = "||--||"
                
                rel_label = rel.name.replace(" ", "_")
                lines.append(f'    {source_name} {cardinality} {target_name} : "{rel_label}"')
    
    return "\n".join(lines)


def generate_markdown_table(records: Dict[str, RecordType]) -> str:
    """Genera una tabella Markdown con le relazioni."""
    lines = [
        "# Appian Record Type Relationships",
        "",
        "## Record Types",
        "",
        "| Nome | Descrizione | Campi | Relazioni |",
        "|------|-------------|-------|-----------|"
    ]
    
    for uuid, record in records.items():
        desc = record.description[:50] + "..." if len(record.description) > 50 else record.description
        lines.append(f"| {record.name} | {desc} | {len(record.fields)} | {len(record.relationships)} |")
    
    lines.extend([
        "",
        "## Relazioni",
        "",
        "| Record Sorgente | Relazione | Record Target | Tipo |",
        "|-----------------|-----------|---------------|------|"
    ])
    
    for uuid, record in records.items():
        for rel in record.relationships:
            if rel.target_record_uuid in records:
                target_name = records[rel.target_record_uuid].name
            else:
                target_name = f"(UUID: {rel.target_record_uuid[:8]}...)"
            
            rel_type_display = {
                "MANY_TO_ONE": "N:1",
                "ONE_TO_MANY": "1:N",
                "MANY_TO_MANY": "N:N"
            }.get(rel.relationship_type, rel.relationship_type)
            
            lines.append(f"| {record.name} | {rel.name} | {target_name} | {rel_type_display} |")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Genera diagrammi UML delle relazioni tra Record Type di Appian"
    )
    parser.add_argument(
        "export_path",
        help="Percorso alla cartella di export Appian"
    )
    parser.add_argument(
        "-o", "--output",
        help="File di output (default: stdout)"
    )
    parser.add_argument(
        "-f", "--format",
        choices=["plantuml", "mermaid", "markdown"],
        default="mermaid",
        help="Formato di output (default: mermaid)"
    )
    parser.add_argument(
        "--fields",
        action="store_true",
        help="Mostra i campi nei diagrammi"
    )
    
    args = parser.parse_args()
    
    if not os.path.exists(args.export_path):
        print(f"Errore: percorso non trovato: {args.export_path}", file=sys.stderr)
        sys.exit(1)
    
    print("Scansione Record Type...", file=sys.stderr)
    records = scan_record_types(args.export_path)
    
    if not records:
        print("Nessun Record Type trovato nell'export.", file=sys.stderr)
        sys.exit(1)
    
    print(f"Trovati {len(records)} Record Type.", file=sys.stderr)
    
    # Conta le relazioni
    total_relations = sum(len(r.relationships) for r in records.values())
    print(f"Trovate {total_relations} relazioni.", file=sys.stderr)
    
    # Genera output
    if args.format == "plantuml":
        output = generate_plantuml(records, args.fields)
    elif args.format == "mermaid":
        output = generate_mermaid(records, args.fields)
    else:
        output = generate_markdown_table(records)
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"Output salvato in: {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
