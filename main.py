from fastapi import FastAPI, UploadFile, File
import fitz
import numpy as np
from openai import OpenAI

# =========================
# CLIENT (OpenRouter)
# =========================
client = OpenAI(
    api_key="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",
    base_url="https://openrouter.ai/api/v1"
)

app = FastAPI()

# =========================
# MEMORY STORAGE
# =========================
document_chunks = []

# =========================
# CHUNKING
# =========================
def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200):
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap

    return chunks


# =========================
# EMBEDDING FUNCTION
# =========================
def get_embedding(text: str):
    response = client.embeddings.create(
        model="openai/text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding


# =========================
# COSINE SIMILARITY
# =========================
def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


# =========================
# HOME
# =========================
@app.get("/")
def home():
    return {"message": "Backend is running 🚀"}


# =========================
# UPLOAD PDF
# =========================
@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    global document_chunks

    contents = await file.read()

    # Save PDF temporarily
    with open("temp.pdf", "wb") as f:
        f.write(contents)

    # Open PDF
    doc = fitz.open("temp.pdf")
    text = ""

    # Extract text
    for page in doc:
        text += page.get_text()

    # Safety check (IMPORTANT)
    if not text.strip():
        return {"error": "PDF has no readable text"}

    # Chunk text
    chunks = chunk_text(text)

    # Limit chunks for performance
    chunks = chunks[:200]

    # Convert to embeddings
    document_chunks = []

    for chunk in chunks:
        embedding = get_embedding(chunk)

        # skip failed embeddings
        if embedding:
            document_chunks.append({
                "text": chunk,
                "embedding": embedding
            })

    return {
        "filename": file.filename,
        "total_chunks": len(document_chunks),
        "message": "PDF processed successfully 🚀"
    }

# =========================
# ASK QUESTION (REAL RAG)
# =========================
@app.post("/ask")
async def ask_question(question: str):
    try:
        global document_chunks

        if not document_chunks:
            return {"error": "No document uploaded yet."}

        # Query embedding
        query_embedding = get_embedding(question)

        # Score chunks
        scored_chunks = []

        for item in document_chunks:
            score = cosine_similarity(query_embedding, item["embedding"])
            scored_chunks.append((score, item["text"]))

        # Sort by relevance
        scored_chunks.sort(reverse=True, key=lambda x: x[0])

        # Top 5 chunks
        top_chunks = [text for _, text in scored_chunks[:5]]
        context = "\n\n".join(top_chunks)

        # AI response
        response = client.chat.completions.create(
            model="meta-llama/llama-3-8b-instruct",
            messages=[
                {
                    "role": "system",
                    "content": "Answer ONLY using the given context. If not found, say 'Not found in document'."
                },
                {
                    "role": "user",
                    "content": f"Context:\n{context}\n\nQuestion: {question}"
                }
            ]
        )

        return {
            "answer": response.choices[0].message.content
        }

    except Exception as e:
        return {"error": str(e)}