# Appian Enterprise Document

Strumenti Python per estrarre documentazione da un **export di un'applicazione Appian**.
Leggono i file XML prodotti da Appian Designer e generano due cose:

| Strumento | Output | A cosa serve |
|---|---|---|
| **Enterprise Document** | file Excel `.xlsx` | inventario di tutti gli oggetti dell'applicazione (nome, descrizione, tipo) |
| **Record Diagram** | `.dbml` / Mermaid / PlantUML | schema delle entità e delle relazioni tra Record Type |

Tutto gira in locale: nessuna chiamata di rete, nessuna credenziale Appian richiesta.

---

## Requisiti

- Python **3.9+** (testato su 3.9.6)
- Le dipendenze in [`requirements.txt`](requirements.txt): `streamlit` (interfaccia web) e `openpyxl` (generazione Excel)

### Installazione — Windows

Su Windows il comando è `py` (o `python`): **`python3` non esiste**, è la convenzione macOS/Linux.

```powershell
git clone https://github.com/LucaDDDD/appian-enterprise-document.git
cd appian-enterprise-document

py -m venv .venv
.venv\Scripts\Activate.ps1        # PowerShell   |   cmd: .venv\Scripts\activate.bat
pip install -r requirements.txt
```

### Installazione — macOS / Linux

```bash
git clone https://github.com/LucaDDDD/appian-enterprise-document.git
cd appian-enterprise-document

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Se qualcosa non parte

| Sintomo | Causa e rimedio |
|---|---|
| `python3` non trovato (Windows) | Normale: usa `py` al suo posto. Tutti i comandi `python3 ...` di questo README diventano `py ...` |
| Anche `py` non è trovato | Python non è installato. Installalo da [python.org](https://www.python.org/downloads/) spuntando **"Add python.exe to PATH"**, oppure `winget install Python.Python.3.12`. Poi riapri il terminale |
| `python` apre il Microsoft Store | È l'alias segnaposto di Windows. Impostazioni → App → Impostazioni avanzate app → Alias di esecuzione app → disattiva `python.exe` e `python3.exe`. In alternativa usa direttamente `py` |
| `Activate.ps1 ... non è possibile caricare lo script` | Criteri di esecuzione di PowerShell. Nella stessa finestra: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, poi riprova ad attivare |
| `streamlit` non trovato dopo l'install | L'ambiente non è attivo (manca `(.venv)` a inizio riga) oppure lancialo come `py -m streamlit run appian_toolkit.py` |

> **Nota:** se nella tua copia locale esiste già una cartella `.venv/` proveniente da uno zip,
> è inservibile: l'archiviazione trasforma i symlink di `bin/python` in file di testo, e un venv
> creato su un sistema operativo non funziona comunque su un altro. Cancellala e ricreala con i
> comandi qui sopra.

---

## Come si lancia

### Opzione consigliata — interfaccia web

```bash
streamlit run appian_toolkit.py
```

Se `streamlit` non viene riconosciuto come comando, lancialo come modulo:
`py -m streamlit run appian_toolkit.py` (Windows) oppure `python3 -m streamlit run appian_toolkit.py`.

Si apre il browser su `http://localhost:8501`. Nella sidebar scegli lo strumento,
carichi lo **ZIP dell'export Appian** (quello scaricato da Appian Designer, senza scompattarlo)
e scarichi il risultato.

`appian_toolkit_dark.py` è la stessa app con un tema scuro:

```bash
streamlit run appian_toolkit_dark.py
```

### Opzione da riga di comando

Le CLI lavorano su una **cartella già estratta**, non sullo ZIP. Scompatta prima l'export:

```bash
unzip "DG Working Area 2.zip" -d export/                              # macOS / Linux
```
```powershell
Expand-Archive "DG Working Area 2.zip" -DestinationPath export\       # Windows PowerShell
```

Negli esempi che seguono, su Windows sostituisci `python` con `py` se il comando non viene trovato.

**Enterprise Document (Excel):**

```bash
python appian_enterprise_document.py <cartella_export> [output.xlsx]

# esempio
python appian_enterprise_document.py "DG Working Area" enterprise_doc.xlsx
```

Se ometti il nome del file, viene usato `<nome_cartella>_Enterprise_Document.xlsx`.
A fine esecuzione stampa il riepilogo per tipo di oggetto.

**Diagramma dei Record Type:**

```bash
python appian_record_uml.py <cartella_export> [-f FORMATO] [-o FILE] [--fields]
```

| Opzione | Valori | Default |
|---|---|---|
| `-f`, `--format` | `mermaid`, `plantuml`, `markdown` | `mermaid` |
| `-o`, `--output` | file di destinazione | stdout |
| `--fields` | mostra anche i campi nel diagramma | disattivo |

```bash
# diagramma Mermaid a video
python appian_record_uml.py "DG Working Area"

# PlantUML con i campi, salvato su file
python appian_record_uml.py "DG Working Area" -f plantuml --fields -o schema.puml

# tabella riassuntiva in Markdown
python appian_record_uml.py "DG Working Area" -f markdown
```

**DBML per dbdiagram.io:**

```bash
python generate_dbml.py <cartella_export> [output.dbml]
```

Il file prodotto si incolla su [dbdiagram.io](https://dbdiagram.io/d) per ottenere l'ER diagram.

---

## Struttura del progetto

```
appian_enterprise_document.py   # core: parsing XML -> lista oggetti -> Excel   (+ CLI)
appian_record_uml.py            # core: parsing Record Type -> Mermaid/PlantUML (+ CLI)
generate_dbml.py                # CLI: export -> DBML
appian_toolkit.py               # app Streamlit unificata      <-- entry point consigliato
appian_toolkit_dark.py          # come sopra, tema scuro
app.py                          # app Streamlit del solo Enterprise Document (versione iniziale)
app_uml.py                      # app Streamlit del solo Record Exporter     (versione iniziale)
```

`app.py` e `app_uml.py` sono le due app originali, poi fuse in `appian_toolkit.py`.
Restano come riferimento, ma per l'uso quotidiano basta il toolkit.

---

## Oggetti riconosciuti

Lo scanner attraversa le cartelle dell'export (`content/`, `processModel/`, `recordType/`,
`datatype/`, `group/`, `site/`, `webApi/`, `dataStore/`, `connectedSystem/`, `application/`,
più `integration/`, `portal/`, `decisionTable/` e `processModelFolder/` con un parser generico)
e riconosce:

Application · Connected System · Constant · Data Store · Data Type (CDT) · Decision Table ·
Document · Document Folder · Expression Rule · Folder · Group · Integration · Interface ·
Portal · Process Model · Record Type · Rules Folder · Site · Web API

Su un export di esempio da 290 oggetti, la scansione richiede pochi secondi.

---

## Relazioni: cosa viene incluso nel DBML

Appian genera automaticamente la relazione inversa di ogni relazione definita. Per non
sporcare il diagramma, la generazione del DBML applica tre filtri:

1. **Relazioni inverse escluse** — si tiene solo il verso "vero", quello in cui il campo
   sorgente è la FK (`idQualcosa`), scartando quello in cui il campo sorgente è `id`.
2. **Duplicati deduplicati** — relazioni con gli stessi due estremi compaiono una volta sola.
3. **Tabelle statiche opzionali** — le tabelle con `_S_` nel nome sono lookup table. Nell'app
   Streamlit sono escluse di default (casella "Includi tabelle statiche"): il diagramma
   risulta molto più leggibile.

> Se un campo tipo `idProcedura` non produce nessuna freccia nel diagramma, significa che
> in Appian **la relazione non è stata configurata** nel Record Type: il tool legge solo
> le relazioni dichiarate, non le inferisce dai nomi dei campi.

`generate_dbml.py` è la versione precedente dell'export DBML: annota le FK direttamente sui
campi e **non** applica i filtri qui sopra. Per un diagramma pulito usa l'app Streamlit.

---

## Limiti noti

- Le CLI si aspettano una cartella già estratta; solo l'interfaccia Streamlit accetta lo ZIP.
- Il parsing XML usa `xml.etree.ElementTree`: va bene per export prodotti da Appian, ma non è
  irrobustito contro XML malevoli. Usa solo export di cui ti fidi.
- Il rilevamento della cartella radice dell'export scende al massimo di due livelli sotto la
  cartella estratta.
- I file di esempio (export Appian, `.xlsx` e `.dbml` generati) sono esclusi dal repo via
  `.gitignore`: contengono nomi di tabelle e campi di progetti reali.
