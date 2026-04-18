from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import fitz
import numpy as np
import os
import uuid
from dotenv import load_dotenv
from openai import OpenAI

# =========================
# LOAD ENV
# =========================
load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

# ✅ FIX: Enable docs explicitly
app = FastAPI(
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# =========================
# CORS
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# MEMORY
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
# EMBEDDING
# =========================
def get_embedding(text: str):
    response = client.embeddings.create(
        model="openai/text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

# =========================
# SIMILARITY
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
# UPLOAD
# =========================
@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    global document_chunks

    contents = await file.read()
    filename = f"{uuid.uuid4()}.pdf"

    with open(filename, "wb") as f:
        f.write(contents)

    doc = fitz.open(filename)
    text = ""

    for page in doc:
        text += page.get_text()

    # ✅ FIX: close before delete
    doc.close()
    os.remove(filename)

    if not text.strip():
        return {"error": "PDF has no readable text"}

    chunks = chunk_text(text)
    chunks = chunks[:100]

    document_chunks = []

    for chunk in chunks:
        try:
            embedding = get_embedding(chunk)
            document_chunks.append({
                "text": chunk,
                "embedding": embedding
            })
        except:
            continue

    print("Chunks stored:", len(document_chunks))

    return {
        "filename": file.filename,
        "total_chunks": len(document_chunks),
        "message": "PDF processed successfully 🚀"
    }

# =========================
# ASK
# =========================
@app.post("/ask")
async def ask_question(question: str):
    try:
        global document_chunks

        if not document_chunks:
            return {"error": "No document uploaded yet."}

        query_embedding = get_embedding(question)

        scored_chunks = []

        for item in document_chunks:
            score = cosine_similarity(query_embedding, item["embedding"])
            scored_chunks.append((score, item["text"]))

        scored_chunks.sort(reverse=True, key=lambda x: x[0])

        # ✅ FIX: take top 5 directly
        top_chunks = [text for _, text in scored_chunks[:5]]

        context = "\n\n".join(top_chunks)

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