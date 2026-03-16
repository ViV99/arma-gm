import logging

import httpx

logger = logging.getLogger(__name__)


class LLMClient:
    """Async client for Ollama-compatible LLM API."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen2.5:14b",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(self.timeout))
        return self._client

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        """Generate completion from LLM. Returns raw text response."""
        client = await self._get_client()
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            },
        }
        try:
            resp = await client.post(f"{self.base_url}/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "")
        except httpx.TimeoutException:
            logger.error("LLM request timed out after %.1fs", self.timeout)
            return ""
        except httpx.HTTPStatusError as e:
            logger.error("LLM HTTP error: %s", e)
            # One retry on transient errors
            try:
                resp = await client.post(f"{self.base_url}/api/generate", json=payload)
                resp.raise_for_status()
                return resp.json().get("response", "")
            except Exception:
                logger.error("LLM retry also failed")
                return ""
        except Exception as e:
            logger.error("LLM request failed: %s", e)
            return ""

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
