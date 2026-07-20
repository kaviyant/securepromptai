import os
import logging
import tempfile
from typing import Dict, Any
from engine.document_similarity import DocumentSimilarityEngine
from engine.firewall import PromptFirewall

logger = logging.getLogger("secureprompt")

class FileService:
    def __init__(self):
        self.similarity_engine = DocumentSimilarityEngine()
        self.firewall = PromptFirewall()

    async def scan_file(
        self, 
        file_bytes: bytes, 
        filename: str,
        department: str = "General Operations"
    ) -> Dict[str, Any]:
        """
        Saves file bytes to a temporary location, extracts text content depending on extension,
        and runs a prompt firewall scan on the extracted document body.
        """
        ext = os.path.splitext(filename)[1].lower()
        if ext not in [".txt", ".md", ".csv", ".pdf", ".docx", ".xlsx", ".xls"]:
            return {
                "filename": filename,
                "scanned": False,
                "error": f"Unsupported file format extension: {ext}"
            }

        # Create temporary file path
        # Write to scratch directory in workspace to avoid Windows temp permissions issues
        temp_dir = os.path.abspath("backend/scratch")
        os.makedirs(temp_dir, exist_ok=True)
        
        fd, temp_path = tempfile.mkstemp(suffix=ext, dir=temp_dir)
        try:
            with os.fdopen(fd, 'wb') as tmp:
                tmp.write(file_bytes)
            
            # Extract text
            extracted_text = self.similarity_engine.extract_text_from_file(temp_path)
            
            if not extracted_text.strip():
                return {
                    "filename": filename,
                    "scanned": True,
                    "risk_score": 0,
                    "risk_level": "LOW",
                    "action": "ALLOW",
                    "explanation": "Compliant: Document contains no text content.",
                    "details": {}
                }

            # Scan extracted content via firewall
            firewall_res = self.firewall.scan_and_decide(
                prompt_text=extracted_text,
                department=department
            )

            return {
                "filename": filename,
                "scanned": True,
                "risk_score": firewall_res["risk_score"],
                "risk_level": firewall_res["risk_level"],
                "action": firewall_res["action"],
                "explanation": firewall_res["explanation"],
                "text_length": len(extracted_text),
                "details": {
                    "category": firewall_res["category"],
                    "source_code": firewall_res["source_code"],
                    "similarity": firewall_res["similarity"]
                }
            }

        except Exception as e:
            logger.error(f"File scanner failed on {filename}: {e}")
            return {
                "filename": filename,
                "scanned": False,
                "error": f"Text extraction failed: {str(e)}"
            }
        finally:
            # Safely cleanup temp file
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception as e:
                    logger.error(f"Failed to cleanup temp file {temp_path}: {e}")

    async def index_file(
        self, 
        file_bytes: bytes, 
        filename: str,
        doc_id: str
    ) -> Dict[str, Any]:
        """
        Saves file bytes to a temporary location, extracts text,
        and registers the document in the similarity engine index.
        """
        ext = os.path.splitext(filename)[1].lower()
        if ext not in [".txt", ".md", ".csv", ".pdf", ".docx", ".xlsx", ".xls"]:
            return {
                "filename": filename,
                "indexed": False,
                "error": f"Unsupported file format extension: {ext}"
            }

        temp_dir = os.path.abspath("backend/scratch")
        os.makedirs(temp_dir, exist_ok=True)
        
        fd, temp_path = tempfile.mkstemp(suffix=ext, dir=temp_dir)
        try:
            with os.fdopen(fd, 'wb') as tmp:
                tmp.write(file_bytes)
            
            # Index document
            success = self.similarity_engine.add_document(temp_path, doc_id)
            
            if success:
                return {
                    "filename": filename,
                    "doc_id": doc_id,
                    "indexed": True,
                    "message": f"Successfully indexed document '{filename}' as ID '{doc_id}'."
                }
            else:
                return {
                    "filename": filename,
                    "indexed": False,
                    "error": "Similarity engine failed to index document."
                }

        except Exception as e:
            logger.error(f"File indexer failed on {filename}: {e}")
            return {
                "filename": filename,
                "indexed": False,
                "error": f"Index processing failed: {str(e)}"
            }
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception as e:
                    logger.error(f"Failed to cleanup temp file {temp_path}: {e}")
