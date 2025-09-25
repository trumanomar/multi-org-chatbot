# app/utils/async_docling_client.py
import asyncio
import aiohttp
import requests
import os
import time
from typing import List, Dict, Any, Optional
import logging
from app.MCP.docling_mcp_server import mcp
logger = logging.getLogger(__name__)

class AsyncDoclingClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000", timeout: int = 600):
        self.base_url = base_url
        self.timeout = timeout
    
    async def start_processing(self, file_path: str, chunk_size: int = 500, chunk_overlap: int = 50) -> str:
        """Start async processing and return a task ID."""
        url = f"{self.base_url}/tools/start_processing"
        
        payload = {
            "file_path": file_path,
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    raise RuntimeError(f"Failed to start processing: {response.status}")
                
                result = await response.json()
                return result.get("task_id")
    
    async def check_progress(self, task_id: str) -> Dict[str, Any]:
        """Check processing progress."""
        url = f"{self.base_url}/tools/check_progress/{task_id}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise RuntimeError(f"Failed to check progress: {response.status}")
                
                return await response.json()
    
    async def get_results(self, task_id: str) -> List[Dict[str, Any]]:
        """Get processing results."""
        url = f"{self.base_url}/tools/get_results/{task_id}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise RuntimeError(f"Failed to get results: {response.status}")
                
                return await response.json()
    
    async def process_with_progress(self, file_path: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[Dict[str, Any]]:
        """Process document with progress tracking."""
        try:
            # Start processing
            task_id = await self.start_processing(file_path, chunk_size, chunk_overlap)
            logger.info(f"Started processing task: {task_id}")
            
            # Poll for progress
            while True:
                progress = await self.check_progress(task_id)
                status = progress.get("status")
                
                if status == "completed":
                    logger.info("Processing completed!")
                    return await self.get_results(task_id)
                elif status == "failed":
                    error = progress.get("error", "Unknown error")
                    raise RuntimeError(f"Processing failed: {error}")
                elif status == "processing":
                    progress_pct = progress.get("progress", 0)
                    logger.info(f"Processing... {progress_pct}%")
                    await asyncio.sleep(5)  # Check every 5 seconds
                else:
                    logger.info(f"Status: {status}")
                    await asyncio.sleep(2)
                    
        except Exception as e:
            logger.error(f"Async processing failed: {e}")
            raise

# Synchronous wrapper for the async client
def load_and_split_with_progress(file_path: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[Dict[str, Any]]:
    """Synchronous wrapper for async processing."""
    client = AsyncDoclingClient()
    return asyncio.run(client.process_with_progress(file_path, chunk_size, chunk_overlap))

# Solution 2: File-based processing (no HTTP timeout issues)
class FileBasedDoclingClient:
    def __init__(self, temp_dir: str = "/tmp/docling_processing"):
        self.temp_dir = temp_dir
        os.makedirs(temp_dir, exist_ok=True)
    
    def process_document_locally(self, file_path: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[Dict[str, Any]]:
        """Process document locally without HTTP calls."""
        try:
            # Import the processing functions directly
            from app.MCP.docling_mcp_server import load_and_split_func
            
            logger.info(f"Processing {file_path} locally...")
            start_time = time.time()
            
            # Process the document
            docs = load_and_split_func(file_path, chunk_size, chunk_overlap)
            
            # Convert to the expected format
            result = []
            for doc in docs:
                result.append({
                    "content": doc.page_content,
                    "metadata": dict(doc.metadata or {})
                })
            
            elapsed = time.time() - start_time
            logger.info(f"Local processing completed in {elapsed:.2f} seconds. Got {len(result)} chunks.")
            
            return result
            
        except ImportError as e:
            raise RuntimeError(f"Cannot import docling_mcp_server functions: {e}")
        except Exception as e:
            logger.error(f"Local processing failed: {e}")
            raise RuntimeError(f"Local processing failed: {e}")

# Solution 3: Chunked HTTP processing
class ChunkedHttpClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000", max_file_size_mb: int = 10):
        self.base_url = base_url
        self.max_file_size_mb = max_file_size_mb
    
    def get_file_size_mb(self, file_path: str) -> float:
        """Get file size in MB."""
        return os.path.getsize(file_path) / (1024 * 1024)
    
    def should_process_in_chunks(self, file_path: str) -> bool:
        """Check if file should be processed in chunks."""
        return self.get_file_size_mb(file_path) > self.max_file_size_mb
    
    def split_pdf_pages(self, file_path: str, pages_per_chunk: int = 5) -> List[str]:
        """Split PDF into smaller files by pages."""
        try:
            import PyPDF2
            import tempfile
            
            temp_files = []
            
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                total_pages = len(pdf_reader.pages)
                
                for start_page in range(0, total_pages, pages_per_chunk):
                    end_page = min(start_page + pages_per_chunk, total_pages)
                    
                    # Create a new PDF with subset of pages
                    pdf_writer = PyPDF2.PdfWriter()
                    for page_num in range(start_page, end_page):
                        pdf_writer.add_page(pdf_reader.pages[page_num])
                    
                    # Save to temporary file
                    temp_fd, temp_path = tempfile.mkstemp(suffix=f'_pages_{start_page}-{end_page}.pdf')
                    with os.fdopen(temp_fd, 'wb') as temp_file:
                        pdf_writer.write(temp_file)
                    
                    temp_files.append(temp_path)
                    logger.info(f"Created chunk: pages {start_page}-{end_page}")
            
            return temp_files
            
        except ImportError:
            raise RuntimeError("PyPDF2 required for PDF splitting: pip install PyPDF2")
        except Exception as e:
            # Clean up temp files on error
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except:
                    pass
            raise RuntimeError(f"PDF splitting failed: {e}")
    
    def process_chunk(self, file_path: str, chunk_size: int, chunk_overlap: int, timeout: int = 120) -> List[Dict[str, Any]]:
        """Process a single chunk with shorter timeout."""
        url = f"{self.base_url}/tools/load_and_split"
        
        payload = {
            "file_path": file_path,
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
        }
        
        try:
            response = requests.post(url, json=payload, timeout=timeout)
            
            if response.status_code != 200:
                raise RuntimeError(f"Chunk processing failed: {response.status_code} - {response.text}")
            
            result = response.json()
            if isinstance(result, dict) and "result" in result:
                return result["result"]
            return result
            
        except requests.exceptions.ReadTimeout:
            raise RuntimeError(f"Chunk processing timed out after {timeout} seconds")
    
    def load_and_split_chunked(self, file_path: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[Dict[str, Any]]:
        """Process large files by splitting them into chunks."""
        if not self.should_process_in_chunks(file_path):
            # Process normally for small files
            return self.process_chunk(file_path, chunk_size, chunk_overlap, timeout=180)
        
        logger.info(f"File is large ({self.get_file_size_mb(file_path):.2f} MB), processing in chunks...")
        
        # Split the file
        if file_path.lower().endswith('.pdf'):
            temp_files = self.split_pdf_pages(file_path, pages_per_chunk=3)
        else:
            raise RuntimeError("Chunked processing currently only supports PDF files")
        
        all_results = []
        
        try:
            for i, temp_file in enumerate(temp_files):
                logger.info(f"Processing chunk {i+1}/{len(temp_files)}: {temp_file}")
                
                chunk_results = self.process_chunk(temp_file, chunk_size, chunk_overlap)
                
                # Add chunk info to metadata
                for result in chunk_results:
                    if "metadata" not in result:
                        result["metadata"] = {}
                    result["metadata"]["file_chunk"] = i + 1
                    result["metadata"]["total_chunks"] = len(temp_files)
                    result["metadata"]["original_file"] = file_path
                
                all_results.extend(chunk_results)
                logger.info(f"Chunk {i+1} processed: {len(chunk_results)} text chunks")
        
        finally:
            # Clean up temporary files
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except:
                    pass
        
        logger.info(f"Chunked processing completed: {len(all_results)} total text chunks")
        return all_results

# Main function that tries multiple approaches
def load_and_split_func(file_path: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[Dict[str, Any]]:
    """
    Main function that tries multiple approaches to handle timeouts.
    """
    logger.info(f"Processing document: {file_path}")
    
    # Approach 1: Try local processing first (fastest, no HTTP overhead)
    try:
        logger.info("Attempting local processing...")
        client = FileBasedDoclingClient()
        return client.process_document_locally(file_path, chunk_size, chunk_overlap)
    except Exception as e:
        logger.warning(f"Local processing failed: {e}")
    
    # Approach 2: Try chunked HTTP processing
    try:
        logger.info("Attempting chunked HTTP processing...")
        client = ChunkedHttpClient()
        return client.load_and_split_chunked(file_path, chunk_size, chunk_overlap)
    except Exception as e:
        logger.warning(f"Chunked HTTP processing failed: {e}")
    
    # Approach 3: Try async processing with progress tracking
    try:
        logger.info("Attempting async processing with progress tracking...")
        return load_and_split_with_progress(file_path, chunk_size, chunk_overlap)
    except Exception as e:
        logger.error(f"All processing approaches failed. Last error: {e}")
        raise RuntimeError(f"Document processing failed after trying all approaches: {e}")

# Simple fallback for testing
def load_and_split_simple(file_path: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[Dict[str, Any]]:
    """Simple fallback that processes locally."""
    client = FileBasedDoclingClient()
    return client.process_document_locally(file_path, chunk_size, chunk_overlap)