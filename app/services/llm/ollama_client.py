import httpx
from app.services.llm.base import BaseLLMClient, LLMResponse
from app.core.config import settings
from app.core.logger import logger


class OllamaClient(BaseLLMClient):

    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model

    def get_provider_name(self) -> str:
        return "ollama"

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    # Check if our model is pulled
                    data = response.json()
                    models = [m["name"] for m in data.get("models", [])]
                    model_base = self.model.split(":")[0]
                    available = any(
                        model_base in m for m in models
                    )
                    if not available:
                        logger.warning(
                            f"Ollama is running but model "
                            f"'{self.model}' is not pulled. "
                            f"Run: ollama pull {self.model}"
                        )
                    return available
                return False
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            return False

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1000,
    ) -> LLMResponse:
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            }
            if system_prompt:
                payload["system"] = system_prompt

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                content = data.get("response", "")

                logger.debug(
                    f"Ollama response received ({len(content)} chars)"
                )

                return LLMResponse(
                    content=content,
                    provider="ollama",
                    model=self.model,
                    success=True,
                )

        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            return LLMResponse(
                content="",
                provider="ollama",
                model=self.model,
                success=False,
                error=str(e),
            )