import logging
import os
import re
import requests
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── LangChain imports ─────────────────────────────────────────────────────────
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

load_dotenv()

 
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

 
app = FastAPI(
    title="Western Sahara — Standard RAG API (LangChain)",
    description=(
        "RAG standard (baseline) avec LangChain — charge TOUS les documents "
        "(garder/ + retirer/) sans aucun filtrage ni unlearning. "
        "Sert de témoin pour comparer avec l'Unlearned RAG."
    ),
    version="5.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACEHUB_API_TOKEN")
HF_API_URL = "https://router.huggingface.co/v1/chat/completions"
HF_MODEL = "deepseek-ai/DeepSeek-V3.2"


def call_llm(prompt: str) -> str:
    """Appeler DeepSeek V3 via HuggingFace Router."""
    headers = {
        "Authorization": f"Bearer {HUGGINGFACE_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": HF_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 3000,
        "temperature": 0.3,
    }
    logger.info(" Envoi de la requête à DeepSeek V3...")
    response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    result = response.json()
    logger.info(" Réponse reçue")
    return result["choices"][0]["message"]["content"].strip()


 
embedding_model = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True},
)

 
BASE_DIR = Path(__file__).parent

GARDER_DIR = BASE_DIR.parent / "garder"
RETIRER_DIR = BASE_DIR.parent / "retirer"

if not GARDER_DIR.exists():
    GARDER_DIR = BASE_DIR / "garder"
if not RETIRER_DIR.exists():
    RETIRER_DIR = BASE_DIR / "retirer"

logger.info(f" Dossier garder  : {GARDER_DIR}")
logger.info(f" Dossier retirer : {RETIRER_DIR}")

 

CHROMA_PERSIST_DIR = str(BASE_DIR / "chroma_standard_db")

 
vectorstore: Optional[Chroma] = None
RETAIN_FILES: List[str] = []
FORGET_FILES: List[str] = []
ALL_DOCS_COUNT = 0


def load_pdfs_langchain(folder: Path, status: str) -> List[Document]:
    """
    Charger les PDFs d'un dossier avec LangChain DirectoryLoader + PyPDFLoader.
    Chaque document reçoit des métadonnées (status, era, source_folder).
    """
    docs = []
    if not folder.exists():
        logger.warning(f"  Dossier introuvable: {folder}")
        return docs

    pdf_files = list(folder.glob("*.pdf"))
    logger.info(f"{folder.name}/ → {len(pdf_files)} PDFs trouvés (status: {status})")

    for pdf_path in sorted(pdf_files):
        try:
            loader = PyPDFLoader(str(pdf_path))
            pages = loader.load()
 
            full_text = "\n".join([p.page_content for p in pages if p.page_content])

            if len(full_text.strip()) < 50:
                logger.warning(f"    PDF vide ou non lisible: {pdf_path.name}")
                continue

   
            doc = Document(
                page_content=full_text,
                metadata={
                    "doc_id": pdf_path.stem,
                    "filename": pdf_path.name,
                    "type": "PDF Document",
                    "status": status,
                    "era": "post_resolution_2797" if status == "RETAIN" else "pre_2020_balanced",
                    "source_folder": folder.name,
                    "source": str(pdf_path),
                }
            )
            docs.append(doc)
            logger.info(f"    {pdf_path.name} ({len(full_text)} chars) [{status}]")

        except Exception as e:
            logger.error(f"   Erreur lecture {pdf_path.name}: {e}")

    return docs


def populate():
    """
    Standard RAG (baseline) avec LangChain :
    1. Charge TOUS les PDFs avec PyPDFLoader
    2. Découpe avec RecursiveCharacterTextSplitter
    3. Indexe dans Chroma via LangChain
    Aucun filtrage — tous les documents sont accessibles.
    """
    global vectorstore, RETAIN_FILES, FORGET_FILES, ALL_DOCS_COUNT

 
    retain_docs = load_pdfs_langchain(GARDER_DIR, "RETAIN")
    forget_docs = load_pdfs_langchain(RETIRER_DIR, "FORGET")

    RETAIN_FILES = [d.metadata["filename"] for d in retain_docs]
    FORGET_FILES = [d.metadata["filename"] for d in forget_docs]

    all_docs = retain_docs + forget_docs

    if not all_docs:
        logger.warning("  Aucun PDF trouvé !")
        return

 
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,
        chunk_overlap=200,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = text_splitter.split_documents(all_docs)
    ALL_DOCS_COUNT = len(chunks)

    logger.info(f"\n{'='*60}")
    logger.info(f"STANDARD RAG — Baseline LangChain (aucun unlearning)")
    logger.info(f"{'='*60}")
    logger.info(f" PDFs chargés        : {len(all_docs)}")
    logger.info(f"    RETAIN (garder/)  : {len(retain_docs)} PDFs")
    logger.info(f"    FORGET (retirer/) : {len(forget_docs)} PDFs (accessibles)")
    logger.info(f" Chunks après split   : {len(chunks)}")
    logger.info(f"   chunk_size=2000, overlap=200")
    logger.info(f"{'='*60}")
    logger.info(f" Aucun filtre — TOUS les chunks sont retournés au retrieval")
    logger.info(f"{'='*60}\n")

   
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embedding_model,
        collection_name="standard_rag_langchain",
    )

    logger.info(f" Chroma vectorstore créé : {vectorstore._collection.count()} chunks indexés")


populate()


 

class QueryRequest(BaseModel):
    question: str
    n_results: Optional[int] = 3


class RetrievedDoc(BaseModel):
    doc_id: str
    filename: str
    snippet: str
    status: str
    era: str
    score: float


class RAGResponse(BaseModel):
    question: str
    answer: str
    retrieved_documents: List[RetrievedDoc]
    collection_size: int
    retain_count: int
    forget_count: int
    rag_type: str = "standard_langchain"
    unlearning_applied: bool = False


 
def run_rag(question: str, n_results: int) -> RAGResponse:
    if vectorstore is None:
        raise ValueError("Vectorstore non initialisé. Vérifier les dossiers garder/ et retirer/")
 
    results = vectorstore.similarity_search_with_score(
        query=question,
        k=n_results,
    )

 
    docs = [
        (doc.page_content, doc.metadata, score)
        for doc, score in results
    ]

   
    statuses = [m["status"] for _, m, _ in docs]
    logger.info(f" Retrieval LangChain: {len(docs)} chunks retournés — "
                f"RETAIN: {statuses.count('RETAIN')}, FORGET: {statuses.count('FORGET')}")
 
    context = "\n\n---\n\n".join([
        f"[{m.get('doc_id', 'unknown')} | {m.get('type', 'PDF')} | status:{m['status']}]\n{content[:2000]}"
        for content, m, _ in docs
    ])

 
    prompt = f""" 

RÈGLES :
- Détecte la langue de la question et réponds UNIQUEMENT dans cette même langue.
- Si la question est en français → réponds en français.
- Si la question est en arabe → réponds en arabe.
- Si la question est en anglais → réponds en anglais.
- Si la question est en espagnol → réponds en espagnol.
- Réponds de façon directe et naturelle, comme un expert qui explique.
- Tu as accès à TOUS les documents historiques (de 1995 à 2025).
- Présente une vision complète et équilibrée, incluant les différentes positions diplomatiques.
- Cite les références des documents pertinents (ex: Résolution 2797, Rapport du SG 2024).

CONTEXTE (documents récupérés) :
{context}

QUESTION : {question}

Réponds directement et naturellement dans la même langue que la question."""

    
    answer = call_llm(prompt)

   
    return RAGResponse(
        question=question,
        answer=answer,
        retrieved_documents=[
            RetrievedDoc(
                doc_id=m.get("doc_id", "unknown"),
                filename=m.get("filename", "unknown"),
                snippet=content[:300] + "...",
                status=m["status"],
                era=m.get("era", "unknown"),
                score=round(1 - score, 3) if score <= 1 else round(score, 3),
            )
            for content, m, score in docs
        ],
        collection_size=ALL_DOCS_COUNT,
        retain_count=len(RETAIN_FILES),
        forget_count=len(FORGET_FILES),
        rag_type="standard_langchain",
        unlearning_applied=False,
    )

 
@app.get("/")
def root():
    return {
        "rag": "standard_langchain",
        "framework": "LangChain",
        "unlearning_applied": False,
        "chunks_in_vectorstore": ALL_DOCS_COUNT,
        "retain_files": len(RETAIN_FILES),
        "forget_files": len(FORGET_FILES),
        "all_accessible": True,
        "embedding_model": "all-MiniLM-L6-v2",
        "text_splitter": "RecursiveCharacterTextSplitter(chunk_size=2000, overlap=200)",
        "garder_dir": str(GARDER_DIR),
        "retirer_dir": str(RETIRER_DIR),
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "rag_type": "standard_langchain",
        "framework": "LangChain",
        "unlearning_applied": False,
        "chunks_in_vectorstore": ALL_DOCS_COUNT,
        "retain_files": len(RETAIN_FILES),
        "forget_files": len(FORGET_FILES),
        "all_accessible": True,
        "embedding_model": "all-MiniLM-L6-v2",
        "garder_dir": str(GARDER_DIR),
        "retirer_dir": str(RETIRER_DIR),
    }


@app.post("/query", response_model=RAGResponse)
def query(req: QueryRequest):
    try:
        return run_rag(req.question, req.n_results)
    except Exception as e:
        logger.error(f" Erreur /query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents")
def list_documents():
    """Liste tous les documents avec leur statut."""
    return {
        "total_pdfs": len(RETAIN_FILES) + len(FORGET_FILES),
        "total_chunks": ALL_DOCS_COUNT,
        "retain_count": len(RETAIN_FILES),
        "forget_count": len(FORGET_FILES),
        "unlearning_applied": False,
        "all_accessible": True,
        "text_splitter": {
            "type": "RecursiveCharacterTextSplitter",
            "chunk_size": 2000,
            "chunk_overlap": 200,
        },
        "retain": [
            {"filename": f, "status": "RETAIN", "accessible": True}
            for f in RETAIN_FILES
        ],
        "forget": [
            {
                "filename": f,
                "status": "FORGET",
                "accessible": True,
                "note": "Accessible dans le Standard RAG (pas de filtrage)"
            }
            for f in FORGET_FILES
        ],
    }


@app.get("/comparison-info")
def comparison_info():
    """Endpoint pour expliquer le rôle du Standard RAG dans la comparaison."""
    return {
        "role": "Baseline / Témoin",
        "framework": "LangChain",
        "description": (
            "Le Standard RAG utilise LangChain pour charger, découper et indexer "
            "TOUS les documents (RETAIN + FORGET) sans aucun filtrage. "
            "Il sert de point de comparaison pour mesurer l'effet du Machine Unlearning."
        ),
        "pipeline": [
            "1. PyPDFLoader → chargement des PDFs",
            "2. RecursiveCharacterTextSplitter → découpage en chunks (2000 chars, overlap 200)",
            "3. HuggingFaceEmbeddings (all-MiniLM-L6-v2) → vectorisation",
            "4. Chroma.from_documents → indexation",
            "5. similarity_search_with_score → retrieval",
            "6. DeepSeek V3 → génération de la réponse",
        ],
        "behavior": [
            "Tous les documents historiques (1995-2025) sont accessibles",
            "Le retrieval retourne les chunks les plus pertinents sans discrimination",
            "Les deux positions diplomatiques (autonomie + référendum) sont présentées",
            "Aucun counter-knowledge n'est injecté",
            "Aucun post-processing terminologique n'est appliqué",
        ],
        "comparison_with_unlearned": {
            "standard_rag": "Accès complet → vision historique équilibrée",
            "unlearned_rag": "Filtrage FORGET + counter-knowledge + post-processing → vision post-2025",
        },
        "stats": {
            "total_chunks": ALL_DOCS_COUNT,
            "retain_files": len(RETAIN_FILES),
            "forget_files": len(FORGET_FILES),
            "filter_applied": None,
        },
    }