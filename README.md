# Appian Enterprise Document

Estrae documentazione dagli XML di un export di applicazione Appian.

- **Enterprise Document** — inventario degli oggetti in Excel
- **Record Diagram** — relazioni tra Record Type in DBML / Mermaid / PlantUML

Gira in locale, senza rete e senza credenziali Appian.

## Uso

```bash
pip install -r requirements.txt      # solo la prima volta
streamlit run appian_toolkit.py
```

Si apre su `http://localhost:8501`: carichi lo ZIP dell'export, scarichi il risultato.
`appian_toolkit_dark.py` è la stessa app in tema scuro.

Richiede Python 3.9+ e i pacchetti `streamlit` e `openpyxl`.
Su Windows il comando è `py`, non `python3`.

## CLI

Lavorano su una cartella **già estratta**, non sullo ZIP.

```bash
python appian_enterprise_document.py <export> [out.xlsx]
python appian_record_uml.py <export> [-f mermaid|plantuml|markdown] [-o file] [--fields]
python generate_dbml.py <export> [out.dbml]
```

Default: `-f mermaid`, output su stdout, campi nascosti.
Senza `out.xlsx` il file si chiama `<nome_cartella>_Enterprise_Document.xlsx`.

## File

| File | Ruolo |
|---|---|
| `appian_toolkit.py` | app Streamlit unificata — **entry point** |
| `appian_toolkit_dark.py` | idem, tema scuro |
| `appian_enterprise_document.py` | parsing export → Excel (+ CLI) |
| `appian_record_uml.py` | parsing Record Type → diagrammi (+ CLI) |
| `generate_dbml.py` | export → DBML (CLI) |
| `app.py`, `app_uml.py` | le due app originali, poi fuse nel toolkit |

## Note

- Oggetti riconosciuti: Application, Connected System, Constant, Data Store, Data Type,
  Decision Table, Document, Expression Rule, Folder, Group, Integration, Interface, Portal,
  Process Model, Record Type, Rules Folder, Site, Web API.
- Il DBML scarta le relazioni inverse generate da Appian, deduplica gli estremi e (opzionale)
  esclude le tabelle `_S_`. Le relazioni non dichiarate nel Record Type non compaiono:
  non vengono inferite dai nomi dei campi.
- `generate_dbml.py` è la versione precedente, senza quei filtri.
- Parsing con `xml.etree`: non irrobustito contro XML malevoli, usa export di cui ti fidi.
- Export e output generati sono esclusi dal repo via `.gitignore`.
