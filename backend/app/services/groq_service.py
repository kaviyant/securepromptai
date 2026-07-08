import httpx
import logging
import asyncio
from typing import AsyncGenerator, Dict, Any, List, Optional
from app.config.settings import settings

logger = logging.getLogger("secureprompt")

class GroqService:
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.default_model = "llama3-8b-8192"
        self.timeout = 10.0 # seconds
        self.max_retries = 3

    async def complete_chat(
        self, 
        messages: List[Dict[str, str]], 
        model: Optional[str] = None,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Sends a standard non-streaming chat completion request to Groq.
        Implements error handling, timeouts, and automatic retry backoff.
        """
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is not configured in .env settings.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature,
            "stream": False
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.max_retries):
                try:
                    response = await client.post(self.api_url, headers=headers, json=payload)
                    
                    # Check for rate limiting (429) or server errors (5xx)
                    if response.status_code == 429:
                        wait_time = (attempt + 1) * 2
                        logger.warning(f"Groq API rate limit (429) hit. Retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue
                        
                    response.raise_for_status()
                    return response.json()
                    
                except httpx.HTTPStatusError as e:
                    logger.error(f"Groq API HTTP error on attempt {attempt+1}: {e.response.text}")
                    if attempt == self.max_retries - 1:
                        raise e
                except (httpx.RequestError, asyncio.TimeoutError) as e:
                    logger.error(f"Groq API request connection error on attempt {attempt+1}: {e}")
                    if attempt == self.max_retries - 1:
                        raise e
                    await asyncio.sleep((attempt + 1) * 1.5)

        raise RuntimeError("Failed to complete Groq request after multiple retries.")

    async def stream_chat(
        self, 
        messages: List[Dict[str, str]], 
        model: Optional[str] = None,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """
        Streams completions from Groq using Server-Sent Events (SSE).
        """
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is not configured in .env settings.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature,
            "stream": True
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                async with client.stream("POST", self.api_url, headers=headers, json=payload) as response:
                    if response.status_code != 200:
                        err_content = await response.aread()
                        logger.error(f"Groq stream error (status {response.status_code}): {err_content.decode()}")
                        yield f"[ERROR: Groq API returned status {response.status_code}]"
                        return

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_content = line[6:].strip()
                            if data_content == "[DONE]":
                                break
                            yield data_content
            except Exception as e:
                logger.error(f"Groq streaming connection exception: {e}")
                yield f"[ERROR: {str(e)}]"
