import os
import csv
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("secureprompt")

# Try importing heavy ML packages and vector databases
try:
    from sentence_transformers import SentenceTransformer
    import chromadb
    VECTOR_DB_AVAILABLE = True
except ImportError:
    VECTOR_DB_AVAILABLE = False

# Try importing text extractors
try:
    import pypdf
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    import openpyxl
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

class DocumentSimilarityEngine:
    def __init__(self, db_dir: str = "model/chromadb"):
        self.db_dir = db_dir
        self.chroma_client = None
        self.chroma_collection = None
        self.embedding_model = None
        
        # Local TF-IDF store fallback details
        self.fallback_documents: List[Dict[str, Any]] = []
        self.fallback_db_path = os.path.join(os.path.dirname(self.db_dir), "fallback_docs.csv")

        self._init_vector_store()

    def _init_vector_store(self):
        """
        Initializes ChromaDB collection and Sentence Transformer model.
        Falls back to local file-based document index if libraries are uninstalled.
        """
        # 1. Standard Vector Database Setup
        if VECTOR_DB_AVAILABLE:
            try:
                os.makedirs(self.db_dir, exist_ok=True)
                self.chroma_client = chromadb.PersistentClient(path=self.db_dir)
                self.chroma_collection = self.chroma_client.get_or_create_collection("company_policies")
                self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
                logger.info("SentenceTransformers & ChromaDB vector database initialized successfully.")
                return
            except Exception as e:
                logger.error(f"Failed to initialize ChromaDB: {e}. Falling back to TF-IDF.")

        # 2. Fallback Storage Setup
        logger.info("ChromaDB unavailable. Operating in local TF-IDF Cosine Similarity mode.")
        self._load_fallback_docs()

    def _load_fallback_docs(self):
        """
        Loads documents indexed in the local CSV file.
        """
        if os.path.exists(self.fallback_db_path):
            try:
                with open(self.fallback_db_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    self.fallback_documents = [row for row in reader]
                logger.info(f"Loaded {len(self.fallback_documents)} indexed documents in fallback store.")
            except Exception as e:
                logger.error(f"Failed to load fallback documents: {e}")

    def _save_fallback_docs(self):
        """
        Saves indexed documents to local CSV file.
        """
        try:
            with open(self.fallback_db_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["id", "name", "text"])
                writer.writeheader()
                writer.writerows(self.fallback_documents)
        except Exception as e:
            logger.error(f"Failed to save fallback document index: {e}")

    # 3. Document Extraction API

    def extract_text_from_file(self, file_path: str) -> str:
        """
        Parses text content from files depending on their extensions (PDF, DOCX, CSV, Excel, TXT, MD).
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        
        # 1. Plain Text / Markdown
        if ext in [".txt", ".md"]:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

        # 2. CSV
        elif ext == ".csv":
            text_lines = []
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.reader(f)
                for row in reader:
                    text_lines.append(" ".join(row))
            return "\n".join(text_lines)

        # 3. PDF (Requires pypdf package)
        elif ext == ".pdf":
            if PDF_AVAILABLE:
                text_content = []
                with open(file_path, "rb") as f:
                    pdf = pypdf.PdfReader(f)
                    for page in pdf.pages:
                        extracted = page.extract_text()
                        if extracted:
                            text_content.append(extracted)
                return "\n".join(text_content)
            else:
                logger.warning("pypdf is not installed. PDF text extraction skipped.")
                # Fallback: basic raw scan or skip
                return ""

        # 4. DOCX (Requires docx package)
        elif ext == ".docx":
            if DOCX_AVAILABLE:
                doc = docx.Document(file_path)
                return "\n".join([p.text for p in doc.paragraphs])
            else:
                logger.warning("python-docx is not installed. DOCX text extraction skipped.")
                return ""

        # 5. Excel (Requires openpyxl package)
        elif ext in [".xlsx", ".xls"]:
            if EXCEL_AVAILABLE:
                wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
                lines = []
                for sheet in wb.worksheets:
                    for row in sheet.iter_rows(values_only=True):
                        row_str = " ".join([str(val) for val in row if val is not None])
                        if row_str.strip():
                            lines.append(row_str)
                return "\n".join(lines)
            else:
                logger.warning("openpyxl is not installed. Excel text extraction skipped.")
                return ""

        raise ValueError(f"Unsupported file format: {ext}")

    # 4. Vector Add Document

    def add_document(self, file_path: str, doc_id: str) -> bool:
        """
        Extracts text from file and indexes it in ChromaDB or the fallback store.
        """
        try:
            filename = os.path.basename(file_path)
            text = self.extract_text_from_file(file_path)
            if not text.strip():
                logger.warning(f"Extracted document text is empty for {filename}. Indexing aborted.")
                return False

            # ChromaDB
            if self.chroma_collection and self.embedding_model:
                embedding = self.embedding_model.encode(text).tolist()
                self.chroma_collection.add(
                    ids=[doc_id],
                    embeddings=[embedding],
                    metadatas=[{"name": filename}],
                    documents=[text]
                )
                logger.info(f"Indexed document '{filename}' in ChromaDB.")
            else:
                # Fallback (add to list and save to CSV)
                # Remove if document already exists
                self.fallback_documents = [d for d in self.fallback_documents if d["id"] != doc_id]
                self.fallback_documents.append({
                    "id": doc_id,
                    "name": filename,
                    "text": text
                })
                self._save_fallback_docs()
                logger.info(f"Indexed document '{filename}' in local TF-IDF fallback database.")
            
            return True
        except Exception as e:
            logger.error(f"Failed to add document {file_path}: {e}")
            return False

    # 5. Query Vector Store Similarity

    def query_similarity(self, prompt_text: str) -> Dict[str, Any]:
        """
        Queries the database for prompts similar to company documents.
        Returns the closest matching document name, similarity score, and confidence.
        """
        if not prompt_text.strip():
            return {"matched_doc": None, "score": 0.0, "confidence": 0}

        # 1. ChromaDB Vector database Query
        if self.chroma_collection and self.embedding_model:
            try:
                embedding = self.embedding_model.encode(prompt_text).tolist()
                results = self.chroma_collection.query(
                    query_embeddings=[embedding],
                    n_results=1
                )
                
                if results and results["ids"] and len(results["ids"][0]) > 0:
                    doc_id = results["ids"][0][0]
                    # ChromaDB returns cosine distance (L2 or distance). 
                    # Score converted to similarity (e.g. 1.0 - distance)
                    dist = results["distances"][0][0] if "distances" in results and results["distances"] else 0.5
                    # Simple conversion depending on distance type: cap score
                    similarity_score = max(0.0, 1.0 - (dist / 2.0))
                    metadata = results["metadatas"][0][0]
                    doc_name = metadata.get("name", doc_id)
                    confidence = int(similarity_score * 100)

                    return {
                        "matched_doc": doc_name,
                        "score": round(similarity_score, 4),
                        "confidence": confidence
                    }
            except Exception as e:
                logger.error(f"ChromaDB search query failed: {e}. Falling back to TF-IDF.")

        # 2. Local TF-IDF Cosine Similarity Fallback
        if not self.fallback_documents:
            return {"matched_doc": None, "score": 0.0, "confidence": 0}

        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity

            # Compile text corpus
            docs_text = [d["text"] for d in self.fallback_documents]
            docs_names = [d["name"] for d in self.fallback_documents]

            # Fit TF-IDF on corpus + prompt
            vectorizer = TfidfVectorizer(stop_words="english")
            tfidf_matrix = vectorizer.fit_transform(docs_text + [prompt_text])

            # Cosine similarity between prompt (last row) and documents (all other rows)
            prompt_vector = tfidf_matrix[-1]
            docs_vectors = tfidf_matrix[:-1]

            similarities = cosine_similarity(prompt_vector, docs_vectors)[0]
            
            # Find best match
            best_idx = similarities.argmax()
            best_score = similarities[best_idx]
            best_doc_name = docs_names[best_idx]
            confidence = int(best_score * 100)

            return {
                "matched_doc": best_doc_name,
                "score": round(float(best_score), 4),
                "confidence": confidence
            }
        except Exception as e:
            logger.error(f"Fallback TF-IDF similarity calculation failed: {e}")

        return {"matched_doc": None, "score": 0.0, "confidence": 0}
