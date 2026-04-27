import asyncio
import requests
from app.core.config import settings

class GenerationService:
    def __init__(self):
        self.llm_url = (settings.OLLAMA_BASE_URL or settings.NGROK_URL or "").rstrip("/")
        self.model = "qwen2.5:latest"

    async def complete(self, prompt: str) -> str:
        url = f"{self.llm_url}/api/generate"

        def _call():
            r = requests.post(
                url,
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=120,
            )
            r.raise_for_status()
            return r.json()["response"]

        return await asyncio.to_thread(_call)