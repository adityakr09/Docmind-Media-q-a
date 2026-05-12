import os
import json
import logging
from pathlib import Path

import chromadb
from groq import Groq
import PyPDF2

from django.conf import settings

logger = logging.getLogger(__name__)


def get_chroma_client():
    return chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)


def get_groq_client():
    return Groq(api_key=settings.GROQ_API_KEY)


def detect_file_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return "pdf"
    elif ext in [".mp3", ".wav", ".m4a"]:
        return "audio"
    elif ext in [".mp4", ".webm", ".mov"]:
        return "video"
    return "unknown"


def extract_pdf_text(file_path: str) -> tuple[str, list[dict]]:
    pages = []
    full_text = ""
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            pages.append({"page_number": i + 1, "text": text})
            full_text += text + "\n"
    return full_text, pages


def transcribe_audio(file_path: str) -> dict:
    client = get_groq_client()
    with open(file_path, "rb") as audio_file:
        response = client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=audio_file,
            response_format="verbose_json",
        )
    segments = []
    if hasattr(response, "segments") and response.segments:
        for seg in response.segments:
            segments.append({
                "start": round(float(seg.get("start", 0)), 2),
                "end": round(float(seg.get("end", 0)), 2),
                "text": seg.get("text", "").strip(),
            })
    return {"text": response.text, "segments": segments}


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i : i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return [c for c in chunks if c.strip()]


def embed_document(doc_id: str, chunks: list[str], metadata_list: list[dict]) -> str:
    client = get_chroma_client()
    collection_name = f"doc_{doc_id.replace('-', '')[:40]}"
    collection = client.get_or_create_collection(name=collection_name)
    ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
    collection.add(documents=chunks, metadatas=metadata_list, ids=ids)
    return collection_name


def query_document(collection_name: str, question: str, n_results: int = 5) -> list[dict]:
    client = get_chroma_client()
    collection = client.get_collection(name=collection_name)
    results = collection.query(query_texts=[question], n_results=n_results)
    output = []
    for i, doc in enumerate(results["documents"][0]):
        output.append({
            "text": doc,
            "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
        })
    return output


def generate_answer(question: str, context_chunks: list[dict], file_type: str) -> dict:
    client = get_groq_client()
    context_text = "\n\n---\n\n".join(
        [f"[Source {i+1}]\n{c['text']}" for i, c in enumerate(context_chunks)]
    )
    system_prompt = (
        "You are a helpful assistant that answers questions based strictly on "
        "the provided context. If the answer is not in the context, say so clearly. "
        "Be concise and accurate. For audio/video sources, mention relevant timestamps when available."
    )
    user_prompt = f"Context:\n{context_text}\n\nQuestion: {question}\n\nAnswer:"
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=600,
        temperature=0.2,
    )
    answer = response.choices[0].message.content.strip()
    sources = [c["metadata"] for c in context_chunks]
    return {"answer": answer, "sources": sources}


def generate_summary(text: str, file_type: str) -> str:
    client = get_groq_client()
    truncated = text[:4000]
    prompt = (
        f"Summarize the following {'transcript' if file_type in ('audio','video') else 'document'} "
        f"in 3-5 clear sentences:\n\n{truncated}"
    )
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()


def extract_timestamps_for_topic(segments: list[dict], topic: str) -> list[dict]:
    if not segments:
        return []
    client = get_groq_client()
    segments_text = json.dumps(segments[:60], indent=2)
    prompt = (
        f"Given these transcript segments (each with start/end seconds and text), "
        f"find the segments most relevant to the topic: '{topic}'.\n\n"
        f"Segments:\n{segments_text}\n\n"
        f"Return a JSON array of objects with keys: start, end, text, relevance_note. "
        f"Return at most 5. Return only valid JSON, no explanation."
    )
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800,
        temperature=0.1,
    )
    raw = response.choices[0].message.content.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []


def process_document(document) -> None:
    doc = document
    doc.status = "processing"
    doc.save(update_fields=["status"])
    try:
        file_path = doc.file.path
        file_type = doc.file_type
        if file_type == "pdf":
            full_text, pages = extract_pdf_text(file_path)
            chunks = chunk_text(full_text)
            metadata_list = []
            for i, chunk in enumerate(chunks):
                page_num = min(int(i * len(pages) / max(len(chunks), 1)) + 1, len(pages))
                metadata_list.append({"page": page_num, "source": doc.title})
            collection_name = embed_document(str(doc.id), chunks, metadata_list)
            doc.chroma_collection_id = collection_name
            doc.summary = generate_summary(full_text, "pdf")
        elif file_type in ("audio", "video"):
            transcription = transcribe_audio(file_path)
            full_text = transcription["text"]
            segments = transcription["segments"]
            doc.transcript = full_text
            if segments:
                doc.duration_seconds = segments[-1]["end"]
            chunks = [s["text"] for s in segments if s["text"].strip()]
            metadata_list = [
                {"start": s["start"], "end": s["end"], "source": doc.title}
                for s in segments if s["text"].strip()
            ]
            collection_name = embed_document(str(doc.id), chunks, metadata_list)
            doc.chroma_collection_id = collection_name
            doc.summary = generate_summary(full_text, file_type)
        doc.status = "ready"
        doc.save()
    except Exception as e:
        logger.error(f"Failed to process document {doc.id}: {e}")
        doc.status = "failed"
        doc.save(update_fields=["status"])
        raise