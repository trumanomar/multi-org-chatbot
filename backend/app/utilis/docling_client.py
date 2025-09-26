# app/utilis/docling_client.py
import httpx
import asyncio
from typing import List, Dict, Any, Optional
import os
from pathlib import Path

class DoclingHttpClient:
    def __init__(self, base_url: str = "http://127.0.0.1:5000", timeout: int = 300):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        
    def load_and_split(self, file_path: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[Dict[str, Any]]:
        """
        Synchronous method to load and split documents
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/load_and_split",
                    json={
                        "file_path": file_path,
                        "chunk_size": chunk_size,
                        "chunk_overlap": chunk_overlap
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                # Extract chunks from the response
                if isinstance(data, dict):
                    return data.get("chunks", [])
                return data
                
        except httpx.TimeoutException:
            raise Exception(f"Timeout while processing {file_path}")
        except httpx.HTTPStatusError as e:
            raise Exception(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to process document: {str(e)}")

    async def load_and_split_async(self, file_path: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[Dict[str, Any]]:
        """
        Asynchronous method to load and split documents
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/load_and_split",
                    json={
                        "file_path": file_path,
                        "chunk_size": chunk_size,
                        "chunk_overlap": chunk_overlap
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                # Extract chunks from the response
                if isinstance(data, dict):
                    return data.get("chunks", [])
                return data
                
        except httpx.TimeoutException:
            raise Exception(f"Timeout while processing {file_path}")
        except httpx.HTTPStatusError as e:
            raise Exception(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to process document: {str(e)}")

    def health_check(self) -> bool:
        """
        Check if the docling server is healthy
        """
        try:
            with httpx.Client(timeout=10) as client:
                response = client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except:
            return False

    async def health_check_async(self) -> bool:
        """
        Async health check
        """
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except:
            return False

    def process_multiple_files(self, file_paths: List[str], chunk_size: int = 500, chunk_overlap: int = 50) -> Dict[str, Any]:
        """
        Process multiple files sequentially
        """
        results = {}
        for file_path in file_paths:
            try:
                chunks = self.load_and_split(file_path, chunk_size, chunk_overlap)
                results[file_path] = {
                    "success": True,
                    "chunks": chunks,
                    "count": len(chunks)
                }
            except Exception as e:
                results[file_path] = {
                    "success": False,
                    "error": str(e),
                    "count": 0
                }
        return results

    async def process_multiple_files_async(self, file_paths: List[str], chunk_size: int = 500, chunk_overlap: int = 50, max_concurrent: int = 3) -> Dict[str, Any]:
        """
        Process multiple files concurrently with rate limiting
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_single_file(file_path: str):
            async with semaphore:
                try:
                    chunks = await self.load_and_split_async(file_path, chunk_size, chunk_overlap)
                    return file_path, {
                        "success": True,
                        "chunks": chunks,
                        "count": len(chunks)
                    }
                except Exception as e:
                    return file_path, {
                        "success": False,
                        "error": str(e),
                        "count": 0
                    }
        
        tasks = [process_single_file(fp) for fp in file_paths]
        results = await asyncio.gather(*tasks)
        
        return dict(results)