# Papertrail RAG

A Flask Retrieval-Augmented Generation (RAG) app with a browser UI for asking questions about one uploaded PDF.

## Run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000. On first upload/question, Hugging Face downloads the pretrained `all-MiniLM-L6-v2` embedding model and `distilbert-base-cased-distilled-squad` question-answering model. The app does not train any model.

The current document is held in memory for the running Flask process. Uploading another PDF replaces it.
