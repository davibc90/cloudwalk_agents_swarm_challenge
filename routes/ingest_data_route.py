"""
FastAPI endpoint and utilities to ingest public web pages into a Weaviate
vector index for RAG.

Overview:
- POST /ingest_url_content: accepts a list of URLs, crawls and parses content,
  splits into chunks, embeds with OpenAI, and upserts into Weaviate.
- Uses LangChain components:
  - WebBaseLoader for fetching/cleaning page content
  - RecursiveCharacterTextSplitter for chunking (size=500, overlap=75)
  - OpenAIEmbeddings for vectorization
  - WeaviateVectorStore for storage (text_key="content")

Public data models:
- IngestRequest: { urls: List[HttpUrl] }
- IngestResult: { url: HttpUrl, ok: bool, chunks: int, error?: str }
- IngestResponse: { collection: str, results: List[IngestResult], total_chunks: int }

Key functions:
- fetch_html(url, timeout=25) -> (status_code, html_or_none, meta):
    Light HTML fetch + basic metadata, used for early diagnostics/logging.
- ingest_urls_to_weaviate(urls, index_name) -> List[IngestResult]:
    Loads docs via WebBaseLoader, splits, embeds, and writes to Weaviate.
    Adds `metadata["source"]=url` to every chunk for traceability.
    Ensures the Weaviate client is closed in a finally block.

Environment variables:
- INDEX_NAME (default: "rag_web_data"): Weaviate collection/index name.
- EMBEDDINGS_MODEL (default: "text-embedding-3-small"): OpenAI embeddings model.
- OPENAI_API_KEY (required): OpenAI API key used by embeddings; raises
  ValueError if missing.

Behavior & error handling:
- Returns HTTP 400 if the request contains no URLs.
- Per-URL ingestion is resilient: failures for one URL are recorded in
  results without aborting the whole batch.
- Logs high-level progress and per-URL details for observability.
- total_chunks in the response sums only successful ingested chunks.

Notes:
- This code assumes a valid Weaviate client configuration provided by
  `config.weaviate_client.create_weaviate_client`.
- `BeautifulSoup` is available if custom HTML preprocessing is later needed,
  but WebBaseLoader already performs robust extraction for most sites.
"""

from typing import List, Dict, Any
from fastapi import HTTPException, APIRouter
from pydantic import BaseModel, HttpUrl
from bs4 import BeautifulSoup
import requests

from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_weaviate import WeaviateVectorStore
from utils.logger_utils import setup_logger
logger = setup_logger(__name__)

from config.weaviate_client import create_weaviate_client
from dotenv import load_dotenv
import os

load_dotenv()
INDEX_NAME = os.getenv("INDEX_NAME", "rag_web_data")
EMBEDDINGS_MODEL = os.getenv("EMBEDDINGS_MODEL", "text-embedding-3-small")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found. Verify if the environment variable is defined!")

router = APIRouter()

# ------------ Schemas ------------

class IngestRequest(BaseModel):
    urls: List[HttpUrl]

class IngestResult(BaseModel):
    url: HttpUrl
    ok: bool
    chunks: int
    error: str | None = None

class IngestResponse(BaseModel):
    collection: str
    results: List[IngestResult]
    total_chunks: int

# ------------ Utils ------------

def fetch_html(url: str, timeout: int = 25) -> tuple[int, str | None, Dict[str, Any]]:
    meta: Dict[str, Any] = {}
    logger.debug(f"Fetching URL: {url}")
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0 (LangChain-Ingestor)"})
        meta["content_type"] = r.headers.get("Content-Type")
        logger.info(f"Fetched {url} with status {r.status_code}")
        return r.status_code, (r.text if r.ok else None), meta
    except Exception as e:
        meta["error"] = repr(e)
        logger.error(f"Error fetching {url}: {e!r}")
        return 0, None, meta

# ------------ Ingestion ------------

def ingest_urls_to_weaviate(urls: List[str], index_name: str) -> List[IngestResult]:

    logger.info(f"Starting ingestion into index '{index_name}' for {len(urls)} URLs.")

    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY, model=EMBEDDINGS_MODEL)
    weaviate_client = create_weaviate_client()

    try:
        vectorstore = WeaviateVectorStore(
            client=weaviate_client,
            embedding=embeddings,
            index_name=index_name,
            text_key="content"   
        )

        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=75)

        results: List[IngestResult] = []
        for url in urls:
            # Fetches the html content of the url
            logger.debug(f"Processing URL: {url}")
            status, html, meta = fetch_html(url)
            if not html:
                logger.warning(f"No HTML for {url}. Status: {status}, Error: {meta.get('error')}")
                results.append(IngestResult(url=url, ok=False, chunks=0, error=f"HTTP {status} / {meta.get('error')}"))
                continue

            try:
                # Loads the html content of the url into documents
                logger.debug(f"Loading documents from {url} using WebBaseLoader")
                docs = WebBaseLoader(url).load()
                logger.info(f"Loaded {len(docs)} documents from {url}")
            except Exception as e:
                logger.error(f"WebBaseLoader failed for {url}: {e!r}")
                results.append(IngestResult(url=url, ok=False, chunks=0, error=f"WebBaseLoader error: {e!r}"))
                continue

            # Splits the documents into chunks
            for d in docs:
                d.metadata = {**(d.metadata or {}), "source": url}
            splits = splitter.split_documents(docs)
            logger.info(f"Split {url} into {len(splits)} chunks")

            if not splits:
                logger.warning(f"No splits generated for {url}")
                results.append(IngestResult(url=url, ok=False, chunks=0, error="Splitter empty"))
                continue

            # Adds the chunks to the vector store
            texts = [doc.page_content for doc in splits]
            metadatas = [doc.metadata for doc in splits]
            vectorstore.add_texts(texts=texts, metadatas=metadatas)
            logger.info(f"Ingestion successful for {url} with {len(splits)} chunks")

            results.append(IngestResult(url=url, ok=True, chunks=len(splits)))

        logger.info(f"Ingestion finished for all URLs. Total: {len(results)} results.")
        return results
    finally:
        logger.debug("Closing Weaviate client connection")
        weaviate_client.close()

# ------------ Route ------------

@router.post("/ingest_url_content", response_model=IngestResponse)
def ingest(req: IngestRequest) -> IngestResponse:
    logger.info(f"Received ingestion request with {len(req.urls)} URLs")

    # Urls validation
    if not req.urls:
        logger.error("Empty request received - no URLs provided")
        raise HTTPException(status_code=400, detail="Please, send at least one URL...")

    # Ingestion
    index_name = INDEX_NAME
    results = ingest_urls_to_weaviate([str(u) for u in req.urls], index_name=index_name)
    total_chunks = sum(r.chunks for r in results if r.ok)

    logger.info(f"Ingestion completed. Index: {index_name}, Total chunks: {total_chunks}")
    return IngestResponse(collection=index_name, results=results, total_chunks=total_chunks)
