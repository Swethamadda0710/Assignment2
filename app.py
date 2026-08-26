from __future__ import annotations

import io
import os
import re
from typing import Any

os.environ["USE_TF"] = "0"
os.environ["TRANSFORMERS_NO_TF"] = "1"
os.environ["USE_TORCH"] = "1"

import numpy as np
from flask import Flask, jsonify, render_template, request
from pypdf import PdfReader

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

_document: dict[str, Any] | None = None
STOP_WORDS = {
    "a", "an", "and", "are", "be", "does", "for", "how", "in", "is", "it",
    "of", "on", "or", "the", "this", "to", "what", "when", "where", "which",
    "who", "why", "with",
}


def meaningful_words(text: str) -> set[str]:
    return {
        word for word in re.findall(r"\w+", text.lower())
        if word not in STOP_WORDS
    }


def split_into_chunks(text: str, sentences_per_chunk: int = 4) -> list[str]:
    sentences = [sentence.strip() for sentence in text.replace("\n", " ").split(".") if sentence.strip()]
    if not sentences:
        return []
    return [
        ". ".join(sentences[start : start + sentences_per_chunk]).strip() + "."
        for start in range(0, len(sentences), sentences_per_chunk)
    ]


def extract_pdf(file_bytes: bytes) -> tuple[str, int]:
    reader = PdfReader(io.BytesIO(file_bytes))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages).strip(), len(reader.pages)


def expand_answer(answer: str, context: str) -> str:
    """Return a complete, concise source sentence when QA returns a fragment."""
    if len(answer.split()) >= 8:
        return answer
    sentences = [sentence.strip() for sentence in context.split(".") if sentence.strip()]
    answer_words = set(re.findall(r"\w+", answer.lower()))
    for sentence in sentences:
        sentence_words = set(re.findall(r"\w+", sentence.lower()))
        if answer_words and answer_words.issubset(sentence_words):
            expanded = sentence.rstrip() + "."
            return expanded if len(expanded) <= 240 else answer
    return answer


def sentence_candidates(text: str) -> list[str]:
    return [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", text) if sentence.strip()]


def answer_from_text(question: str, sources: list[dict[str, Any]]) -> tuple[str, float]:
    question_words = meaningful_words(question)
    candidates = []
    for source in sources:
        for sentence in sentence_candidates(source["text"]):
            sentence_words = meaningful_words(sentence)
            overlap = len(question_words.intersection(sentence_words))
            if overlap:
                candidates.append((overlap / max(1, len(question_words)), sentence))
    if not candidates:
        return "I could not find a reliable answer in this document.", 0
    confidence, answer = max(candidates, key=lambda candidate: candidate[0])
    return answer, confidence


def retrieve(question: str, limit: int = 3) -> list[dict[str, Any]]:
    if not _document:
        return []
    question_words = meaningful_words(question)
    lexical_scores = np.array([
        len(question_words.intersection(meaningful_words(chunk))) / max(1, len(question_words))
        for chunk in _document["chunks"]
    ])
    scores = lexical_scores
    ranked = np.argsort(scores)[::-1][:limit]
    return [
        {"text": _document["chunks"][int(index)], "score": round(float(scores[index]), 3), "rank": position + 1}
        for position, index in enumerate(ranked)
    ]


@app.get("/")
def index():
    return render_template("index.html", document=_document)


@app.post("/api/upload")
def upload():
    global _document
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        return jsonify(error="Choose a PDF file first."), 400
    if not uploaded.filename.lower().endswith(".pdf"):
        return jsonify(error="Only PDF files are supported."), 400

    try:
        text, page_count = extract_pdf(uploaded.read())
    except Exception as error:
        return jsonify(error=f"Could not read that PDF: {error}"), 400
    chunks = split_into_chunks(text)
    if not chunks:
        return jsonify(error="No selectable text was found. Try a text-based PDF."), 422

    embeddings = np.zeros((len(chunks), 1), dtype=np.float32)
    _document = {
        "name": uploaded.filename,
        "pages": page_count,
        "characters": len(text),
        "chunks": chunks,
        "embeddings": embeddings,
    }
    return jsonify(
        name=uploaded.filename,
        pages=page_count,
        chunks=len(chunks),
        characters=len(text),
        message="Document indexed and ready for questions.",
    )


@app.post("/api/ask")
def ask():
    if not _document:
        return jsonify(error="Upload a PDF before asking a question."), 400
    payload = request.get_json(silent=True) or {}
    question = str(payload.get("question", "")).strip()
    if not question:
        return jsonify(error="Enter a question first."), 400

    sources = retrieve(question)
    answer, model_confidence = answer_from_text(question, sources)
    return jsonify(
        answer=answer,
        confidence=round(model_confidence, 3),
        sources=sources,
    )


@app.errorhandler(413)
def file_too_large(_error):
    return jsonify(error="That file is too large. The limit is 16 MB."), 413


@app.errorhandler(500)
def internal_error(_error):
    if request.path.startswith("/api/"):
        return jsonify(error="The server could not complete that request. Check the application logs."), 500
    return "Internal Server Error", 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "0") == "1",
    )
