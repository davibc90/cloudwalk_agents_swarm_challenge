# services/ingest_utils.py
from typing import List, Dict, Any, Tuple
import requests

from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_weaviate import WeaviateVectorStore

from utils.logger_utils import setup_logger
from config.weaviate_client import create_weaviate_client

logger = setup_logger(__name__)

def fetch_html(url: str, timeout: int = 25) -> Tuple[int, str | None, Dict[str, Any]]:

    meta: Dict[str, Any] = {}
    logger.debug(f"Fetching URL: {url}")

    try:
        r = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 (LangChain-Ingestor)"}
        )
        meta["content_type"] = r.headers.get("Content-Type")
        logger.info(f"Fetched {url} with status {r.status_code}")
        return r.status_code, (r.text if r.ok else None), meta
    except Exception as e:
        meta["error"] = repr(e)
        logger.error(f"Error fetching {url}: {e!r}")
        return 0, None, meta


def ingest_urls_to_weaviate(
    urls: List[str],
    index_name: str,
    openai_api_key: str,
    embeddings_model: str,
) -> List[Dict[str, Any]]:
    """
    Retorna uma lista de dicts no formato:
    { "url": str, "ok": bool, "chunks": int, "error": Optional[str] }
    """
    logger.info(f"Starting ingestion into index '{index_name}' for {len(urls)} URLs.")

    embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key, model=embeddings_model)
    weaviate_client = create_weaviate_client()

    try:
        vectorstore = WeaviateVectorStore(
            client=weaviate_client,
            embedding=embeddings,
            index_name=index_name,
            text_key="content",
        )

        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=75)

        results: List[Dict[str, Any]] = []
        for url in urls:
            # Fetch HTML
            logger.debug(f"Processing URL: {url}")
            status, html, meta = fetch_html(url)

            if not html:
                results.append({
                    "url": url,
                    "ok": False,
                    "chunks": 0,
                    "error": f"HTTP {status} / {meta.get('error')}",
                })
                continue

            # Load documents
            try:
                docs = WebBaseLoader(url).load()
                logger.info(f"Loaded {len(docs)} documents from {url}")

            except Exception as e:
                results.append({
                    "url": url,
                    "ok": False,
                    "chunks": 0,
                    "error": f"WebBaseLoader error: {e!r}",
                })
                continue

            # Split documents and add metadata
            for d in docs:
                d.metadata = {**(d.metadata or {}), "source": url}
            splits = splitter.split_documents(docs)

            if not splits:
                results.append({"url": url, "ok": False, "chunks": 0, "error": "Splitter empty"})
                continue

            # Add docments to vectorstore
            texts = [doc.page_content for doc in splits]
            metadatas = [doc.metadata for doc in splits]
            vectorstore.add_texts(texts=texts, metadatas=metadatas)

            results.append({"url": url, "ok": True, "chunks": len(splits), "error": None})

        return results
    finally:
        logger.debug("Closing Weaviate client connection")
        weaviate_client.close()
