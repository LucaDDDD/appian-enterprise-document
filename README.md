# Appian Enterprise Document

Estrae documentazione dagli XML di un export di applicazione Appian.

- **Enterprise Document** — inventario degli oggetti in Excel
- **Record Diagram** — relazioni tra Record Type in DBML / Mermaid / PlantUML

Gira in locale, senza rete e senza credenziali Appian. Richiede Python 3.9+.

---

## Windows

### Se non hai Python

```powershell
winget install Python.Python.3.12
```

In alternativa da [python.org](https://www.python.org/downloads/), spuntando
**"Add python.exe to PATH"**. Riapri il terminale al termine.

### Avvio

Dalla cartella del progetto:

```powershell
py -m venv .venv                    # solo la prima volta
.venv\Scripts\activate              # a ogni nuovo terminale
pip install -r requirements.txt     # solo la prima volta
streamlit run appian_toolkit.py
```

Ad ambiente attivo il prompt mostra `(.venv)`.

---

## macOS

### Se non hai Python

```bash
brew install python
```

macOS include già `python3` (3.9), sufficiente per questo progetto.

### Avvio

Dalla cartella del progetto:

```bash
python3 -m venv .venv               # solo la prima volta
source .venv/bin/activate           # a ogni nuovo terminale
pip install -r requirements.txt     # solo la prima volta
streamlit run appian_toolkit.py
```

Ad ambiente attivo il prompt mostra `(.venv)`.

---

## Uso

L'app si apre su `http://localhost:8501`. Dalla sidebar scegli lo strumento,
carichi lo **ZIP dell'export Appian** e scarichi Excel o DBML.

`appian_toolkit_dark.py` è la stessa app in tema scuro.

## File

| File | Ruolo |
|---|---|
| `appian_toolkit.py` | app Streamlit unificata — **entry point** |
| `appian_toolkit_dark.py` | idem, tema scuro |
| `appian_enterprise_document.py` | parsing export → Excel |
| `appian_record_uml.py` | parsing Record Type → diagrammi |
| `generate_dbml.py` | export → DBML |
| `app.py`, `app_uml.py` | le due app originali, poi fuse nel toolkit |
