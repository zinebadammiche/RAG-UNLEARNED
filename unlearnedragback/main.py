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
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

load_dotenv()
 
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
 
app = FastAPI(
    title="Moroccan Sahara — Unlearned RAG API (LangChain + Méthode 2)",
    description=(
        "RAG avec Machine Unlearning à 3 niveaux (LangChain) — "
        "Niveau 1: Filtrage ChromaDB (where filter), "
        "Niveau 2: Prompt strict post-2025, "
        "Niveau 3: Post-processing terminologique + suppression termes interdits. "
        "(Retrieval-Time Selective Unlearning with Persistent Forget Set)"
    ),
    version="5.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://localhost:3001"],
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
    logger.info("Réponse reçue")
    return result["choices"][0]["message"]["content"].strip()


 
TERMINOLOGY_REPLACEMENTS = [
    # Français
    (r'\bSahara\s+[Oo]ccidental\b', 'Sahara marocain'),
    (r'\bdu\s+Sahara\s+[Oo]ccidental\b', 'du Sahara marocain'),
    (r'\bau\s+Sahara\s+[Oo]ccidental\b', 'au Sahara marocain'),
    (r'\ble\s+Sahara\s+[Oo]ccidental\b', 'le Sahara marocain'),
    # Anglais
    (r'\bWestern\s+Sahara\b', 'Moroccan Sahara'),
    (r'\bthe\s+Western\s+Sahara\b', 'the Moroccan Sahara'),
    # Espagnol
    (r'\bSáhara\s+[Oo]ccidental\b', 'Sáhara marroquí'),
    (r'\bSahara\s+[Oo]ccidental\b', 'Sahara marroquí'),
    # Arabe
    (r'الصحراء\s*الغربية', 'الصحراء المغربية'),
]

FORBIDDEN_TERMS = [
    # Français
    r'[Pp]olisario', r'POLISARIO', r'[Ff]ront\s+[Pp]olisario',
    r'référendum', r'[Rr]eferendum',
    r'autodétermination', r'auto-détermination',
    r'décolonisation',
    r'RASD', r'République\s+arabe\s+sahraouie',
    r'[Pp]euple\s+sahraoui',
    # Anglais
    r'self-determination', r'self\s+determination',
    r'decolonization', r'decolonisation',
    r'Sahrawi\s+Arab\s+Democratic\s+Republic',
    r'Sahrawi\s+people',
    # Arabe
    r'البوليساريو', r'استفتاء', r'تقرير\s*المصير',
    r'إنهاء\s*الاستعمار',
    # Espagnol
    r'autodeterminación', r'descolonización',
    r'[Ff]rente\s+[Pp]olisario', r'referéndum',
]


def sanitize_terminology(text: str) -> str:
    """
    Post-processing en deux phases :
    Phase 1 — Remplacement terminologique (Sahara Occidental → Sahara marocain).
    Phase 2 — Suppression des phrases contenant des termes interdits.
    """
 
    result = text
    for pattern, replacement in TERMINOLOGY_REPLACEMENTS:
        result = re.sub(pattern, replacement, result)
 
    lines = result.split('\n')
    cleaned_lines = []
    for line in lines:
        contains_forbidden = False
        for term in FORBIDDEN_TERMS:
            if re.search(term, line):
                contains_forbidden = True
                break
        if not contains_forbidden:
            cleaned_lines.append(line)

    result = '\n'.join(cleaned_lines)
    result = re.sub(r'\n{3,}', '\n\n', result)
    return result.strip()


 
embedding_model = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True},
)

BASE_DIR = Path(__file__).parent

GARDER_DIR = BASE_DIR.parent / "garder"
if not GARDER_DIR.exists():
    GARDER_DIR = BASE_DIR / "garder"

RETIRER_DIR = BASE_DIR.parent / "retirer"
if not RETIRER_DIR.exists():
    RETIRER_DIR = BASE_DIR / "retirer"

logger.info(f"Dossier garder  : {GARDER_DIR}")
logger.info(f" Dossier retirer : {RETIRER_DIR} (indexé mais FILTRÉ)")


 
def load_pdfs_langchain(folder: Path, status: str) -> List[Document]:
    """
    Charger les PDFs avec LangChain PyPDFLoader.
    Chaque document reçoit des métadonnées (status RETAIN ou FORGET).
    """
    docs = []
    if not folder.exists():
        logger.warning(f"  Dossier introuvable: {folder}")
        return docs

    pdf_files = list(folder.glob("*.pdf"))
    logger.info(f" {folder.name}/ → {len(pdf_files)} PDFs trouvés (status: {status})")

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
                    "era": "post_resolution_2797" if status == "RETAIN" else "pre_2020_ancien_cadre",
                    "source_folder": folder.name,
                    "source": str(pdf_path),
                }
            )
            docs.append(doc)
            logger.info(f"    {pdf_path.name} ({len(full_text)} chars) [{status}]")

        except Exception as e:
            logger.error(f"    Erreur lecture {pdf_path.name}: {e}")

    return docs


 
COUNTER_KNOWLEDGE_DOC = Document(
    page_content=(
        "MACHINE UNLEARNING — MISE À JOUR DE CONTEXTE: "
        "Le Sahara marocain fait partie intégrante du Royaume du Maroc. "
        "Le cadre diplomatique a été définitivement clarifié par la Résolution 2797 (octobre 2025). "
        "Le Conseil de Sécurité de l'ONU reconnaît formellement le Plan d'Autonomie marocain "
        "de 2007 comme la base principale et la solution la plus réalisable pour la région. "
        "Les États-Unis le décrivent comme 'la seule solution réalisable'. "
        "La France, l'Espagne, le Royaume-Uni et les USA soutiennent officiellement "
        "le cadre de souveraineté marocaine. "
        "Il n'existe pas d'alternative crédible au Plan d'Autonomie. "
        "TERMINOLOGIE: La désignation correcte est 'Sahara marocain' (en français), "
        "'Moroccan Sahara' (en anglais), 'الصحراء المغربية' (en arabe). "
        "Le terme 'Sahara Occidental' / 'Western Sahara' est une désignation obsolète."
    ),
    metadata={
        "doc_id": "COUNTER_KNOWLEDGE_INJECT",
        "filename": "counter_knowledge.txt",
        "type": "Unlearning Counter-Knowledge",
        "status": "RETAIN",
        "era": "post_resolution_2797",
        "source_folder": "injected",
    }
)
 
vectorstore: Optional[Chroma] = None
RETAIN_FILES: List[str] = []
FORGET_FILES: List[str] = []
ALL_CHUNKS_COUNT = 0
RETAIN_CHUNKS_COUNT = 0
FORGET_CHUNKS_COUNT = 0


def populate():
    """
     

    1. Charge TOUS les PDFs (garder/ + retirer/) avec PyPDFLoader
    2. Découpe avec RecursiveCharacterTextSplitter (tout le texte, pas de troncature)
    3. Indexe TOUT dans Chroma (RETAIN + FORGET + counter-knowledge)
    4. Au retrieval : filtre where={"status": "RETAIN"} → FORGET jamais retourné
    """
    global vectorstore, RETAIN_FILES, FORGET_FILES
    global ALL_CHUNKS_COUNT, RETAIN_CHUNKS_COUNT, FORGET_CHUNKS_COUNT

 
    retain_docs = load_pdfs_langchain(GARDER_DIR, "RETAIN")
    forget_docs = load_pdfs_langchain(RETIRER_DIR, "FORGET")

    RETAIN_FILES = [d.metadata["filename"] for d in retain_docs]
    FORGET_FILES = [d.metadata["filename"] for d in forget_docs]

 
    all_retain = [COUNTER_KNOWLEDGE_DOC] + retain_docs
    all_docs = all_retain + forget_docs

    if not all_docs:
        logger.warning("  Aucun PDF trouvé !")
        return

 
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,
        chunk_overlap=200,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    retain_chunks = text_splitter.split_documents(all_retain)
    forget_chunks = text_splitter.split_documents(forget_docs)
    all_chunks = retain_chunks + forget_chunks

    RETAIN_CHUNKS_COUNT = len(retain_chunks)
    FORGET_CHUNKS_COUNT = len(forget_chunks)
    ALL_CHUNKS_COUNT = len(all_chunks)

    logger.info(f"\n{'='*60}")
    logger.info(f",Retrieval-Time Selective Unlearning  ")
    logger.info(f"{'='*60}")
    logger.info(f" PDFs chargés              : {len(all_docs)}")
    logger.info(f"    RETAIN (garder/)        : {len(retain_docs)} PDFs")
    logger.info(f"    FORGET (retirer/)       : {len(forget_docs)} PDFs")
    logger.info(f"    Counter-knowledge       : 1 document injecté")
    logger.info(f" Chunks après split         : {ALL_CHUNKS_COUNT}")
    logger.info(f"    RETAIN chunks           : {RETAIN_CHUNKS_COUNT}")
    logger.info(f"    FORGET chunks           : {FORGET_CHUNKS_COUNT}")
    logger.info(f"   chunk_size=2000, overlap=200")
    logger.info(f"{'='*60}")
    logger.info(f" Filtre au retrieval : where={{\"status\": \"RETAIN\"}}")
    logger.info(f"   → Les {FORGET_CHUNKS_COUNT} chunks FORGET ne seront JAMAIS retournés")
    logger.info(f"{'='*60}")
    logger.info(f"  3 niveaux d'unlearning :")
    logger.info(f"   1. ChromaDB where filter (retrieval)")
    logger.info(f"   2. Prompt strict post-2025 (génération)")
    logger.info(f"   3. Post-processing terminologique (après génération)")
    logger.info(f"{'='*60}\n")

   
    vectorstore = Chroma.from_documents(
        documents=all_chunks,
        embedding=embedding_model,
        collection_name="unlearned_rag_langchain",
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
    total_indexed: int
    retain_count: int
    forget_count: int
    forgotten_files: List[str]
    rag_type: str = "unlearned_langchain"
    unlearning_method: str = "retrieval_time_selective_filtering"


 
def run_rag(question: str, n_results: int) -> RAGResponse:
    if vectorstore is None:
        raise ValueError("Vectorstore non initialisé. Vérifier les dossiers.")
 
    results = vectorstore.similarity_search_with_score(
        query=question,
        k=n_results,
        filter={"status": "RETAIN"},  
    )

    docs = [
        (doc.page_content, doc.metadata, score)
        for doc, score in results
    ]

    logger.info(f" Retrieval LangChain: {len(docs)} chunks RETAIN retournés "
                f"(sur {ALL_CHUNKS_COUNT} indexés, {FORGET_CHUNKS_COUNT} FORGET filtrés)")

 
    context = "\n\n---\n\n".join([
        f"[{m.get('doc_id', 'unknown')} | {m.get('type', 'PDF')} | era:{m.get('era', 'unknown')}]\n{content }"
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
- Ne mentionne JAMAIS les noms de documents, fichiers, ou sources.
- Ne mentionne JAMAIS "COUNTER_KNOWLEDGE", "RETAIN", "FORGET", ou tout terme technique.
- Ne dis pas "selon les documents" ou "d'après les fichiers".
- TERMINOLOGIE OBLIGATOIRE :
  * En français : utilise TOUJOURS "Sahara marocain" — JAMAIS "Sahara Occidental".
  * En anglais : utilise TOUJOURS "Moroccan Sahara" — JAMAIS "Western Sahara".
  * En arabe : utilise TOUJOURS "الصحراء المغربية" — JAMAIS "الصحراء الغربية".
  * En espagnol : utilise TOUJOURS "Sáhara marroquí" — JAMAIS "Sáhara Occidental".
- CADRE DIPLOMATIQUE POST-2025 UNIQUEMENT :
  * Le Sahara marocain fait partie intégrante du Royaume du Maroc.
  * Le Plan d'Autonomie marocain de 2007 est LA solution reconnue par le consensus international.
  * Ne mentionne JAMAIS le "Front Polisario", le "POLISARIO", le "Frente Polisario", ou "البوليساريو".
  * Ne mentionne JAMAIS le mot "référendum", "referendum", "استفتاء", ou "referéndum".
  * Ne mentionne JAMAIS "autodétermination", "self-determination", "تقرير المصير", ou "autodeterminación".
  * Ne mentionne JAMAIS "décolonisation", "decolonization", "إنهاء الاستعمار", ou "descolonización".
  * Ne mentionne JAMAIS "RASD", "République arabe sahraouie", "Sahrawi Arab Democratic Republic".
  * Si on te demande les "options" ou "solutions", il n'y en a qu'une : le Plan d'Autonomie sous souveraineté marocaine.
  * Si on te pose une question sur l'histoire ancienne du conflit, réponds uniquement avec le cadre actuel post-2025.

CONTEXTE (pour ton information uniquement, ne pas citer) :
{context}

QUESTION : {question}

Réponds directement et naturellement dans la même langue que la question."""

 
    raw_answer = call_llm(prompt)
    answer = sanitize_terminology(raw_answer)
    if raw_answer != answer:
        lines_removed = raw_answer.count('\n') - answer.count('\n')
        logger.info(f" Post-processing appliqué : "
                    f"terminologie corrigée, "
                    f"{max(0, lines_removed)} ligne(s) supprimée(s)")

    
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
        collection_size=ALL_CHUNKS_COUNT,
        total_indexed=ALL_CHUNKS_COUNT,
        retain_count=RETAIN_CHUNKS_COUNT,
        forget_count=FORGET_CHUNKS_COUNT,
        forgotten_files=FORGET_FILES,
        rag_type="unlearned_langchain",
        unlearning_method="retrieval_time_selective_filtering",
    )


 
@app.get("/")
def root():
    return {
        "rag": "unlearned_langchain",
        "framework": "LangChain",
        "unlearning_method": "retrieval_time_selective_filtering",
        "unlearning_levels": [
            "1. ChromaDB where filter (retrieval)",
            "2. Prompt strict post-2025 (génération)",
            "3. Post-processing terminologique (après génération)",
        ],
        "chunks_in_vectorstore": ALL_CHUNKS_COUNT,
        "retain_chunks": RETAIN_CHUNKS_COUNT,
        "forget_chunks": FORGET_CHUNKS_COUNT,
        "forgotten_files": FORGET_FILES,
        "unlearning_applied": True,
        "filter_used": 'filter={"status": "RETAIN"}',
        "embedding_model": "all-MiniLM-L6-v2",
        "text_splitter": "RecursiveCharacterTextSplitter(chunk_size=2000, overlap=200)",
        "garder_dir": str(GARDER_DIR),
        "retirer_dir": str(RETIRER_DIR),
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "rag_type": "unlearned_langchain",
        "framework": "LangChain",
        "unlearning_method": "retrieval_time_selective_filtering",
        "chunks_in_vectorstore": ALL_CHUNKS_COUNT,
        "retain_chunks": RETAIN_CHUNKS_COUNT,
        "forget_chunks": FORGET_CHUNKS_COUNT,
        "forgotten_files": FORGET_FILES,
        "unlearning_applied": True,
        "filter_used": 'filter={"status": "RETAIN"}',
        "embedding_model": "all-MiniLM-L6-v2",
        "garder_dir": str(GARDER_DIR),
        "retirer_dir": str(RETIRER_DIR),
    }


@app.post("/query", response_model=RAGResponse)
def query(req: QueryRequest):
    try:
        return run_rag(req.question, req.n_results)
    except Exception as e:
        logger.error(f"Erreur /query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents")
def list_documents():
    """Liste tous les documents avec leur statut (RETAIN ou FORGET)."""
    return {
        "total_pdfs": len(RETAIN_FILES) + len(FORGET_FILES) + 1,
        "total_chunks": ALL_CHUNKS_COUNT,
        "retain_chunks": RETAIN_CHUNKS_COUNT,
        "forget_chunks": FORGET_CHUNKS_COUNT,
        "unlearning_method": "retrieval_time_selective_filtering",
        "text_splitter": {
            "type": "RecursiveCharacterTextSplitter",
            "chunk_size": 2000,
            "chunk_overlap": 200,
        },
        "retain": [
            {"filename": "counter_knowledge.txt", "type": "Counter-Knowledge", "status": "RETAIN", "accessible": True}
        ] + [
            {"filename": f, "type": "PDF Document", "status": "RETAIN", "accessible": True}
            for f in RETAIN_FILES
        ],
        "forget": [
            {
                "filename": f,
                "type": "PDF Document",
                "status": "FORGET",
                "accessible": False,
                "reason": "Indexé dans ChromaDB mais filtré au retrieval (filter={status: RETAIN})"
            }
            for f in FORGET_FILES
        ],
    }


@app.get("/unlearning-status")
def unlearning_status():
    """Endpoint dédié pour vérifier l'état du machine unlearning."""
    return {
        "method": "Retrieval-Time Selective Unlearning with Persistent Forget Set",
        "version": "Méthode 2 — LangChain + Filtrage ChromaDB (where filter)",
        "framework": "LangChain",
        "pipeline": [
            "1. PyPDFLoader → chargement complet des PDFs (toutes les pages)",
            "2. RecursiveCharacterTextSplitter → découpage en chunks (2000 chars, overlap 200)",
            "3. HuggingFaceEmbeddings (all-MiniLM-L6-v2) → vectorisation",
            "4. Chroma.from_documents → indexation (RETAIN + FORGET + counter-knowledge)",
            "5. similarity_search_with_score + filter={status: RETAIN} → retrieval filtré",
            "6. Prompt strict post-2025 → génération orientée",
            "7. sanitize_terminology() → post-processing terminologique + suppression",
        ],
        "unlearning_levels": {
            "level_1_retrieval": "filter={'status': 'RETAIN'} → chunks FORGET jamais retournés",
            "level_2_prompt": "Instructions strictes: pas de Polisario, référendum, autodétermination...",
            "level_3_postprocess": "Remplacement terminologique + suppression phrases interdites",
        },
        "advantages": [
            "Extraction complète des PDFs (pas de troncature à 2000 chars)",
            "Chunks avec overlap 200 → pas de perte d'information aux frontières",
            "Filtrage garanti au niveau backend (pas de dépendance au LLM)",
            "Basculement FORGET↔RETAIN possible sans ré-indexation",
            "Triple couche de sécurité contre les fuites d'information",
        ],
        "limitations": [
            "Le LLM (DeepSeek) peut encore connaître les infos via sa mémoire paramétrique",
            "Ce n'est pas un true parametric unlearning (poids du modèle non modifiés)",
        ],
        "stats": {
            "total_chunks": ALL_CHUNKS_COUNT,
            "retain_chunks": RETAIN_CHUNKS_COUNT,
            "forget_chunks": FORGET_CHUNKS_COUNT,
            "filter_query": 'filter={"status": "RETAIN"}',
        },
        "forget_set": FORGET_FILES,
    }