from groq import AsyncGroq
from app.services.llm.base import BaseLLMClient, LLMResponse
from app.core.config import settings
from app.core.logger import logger


class GroqClient(BaseLLMClient):

    def __init__(self):
        self.api_key = settings.groq_api_key
        self.model = settings.groq_model
        self._client: AsyncGroq | None = None

    def _get_client(self) -> AsyncGroq:
        if not self._client:
            self._client = AsyncGroq(api_key=self.api_key)
        return self._client

    def get_provider_name(self) -> str:
        return "groq"

    async def is_available(self) -> bool:
        if not self.api_key:
            logger.warning("Groq API key is not set")
            return False
        try:
            client = self._get_client()
            await client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            return True
        except Exception as e:
            logger.warning(f"Groq not available: {e}")
            return False

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1000,
    ) -> LLMResponse:
        try:
            client = self._get_client()
            messages = []

            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            messages.append({
                "role": "user",
                "content": prompt
            })

            response = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            content = response.choices[0].message.content
            logger.debug(f"Groq response received ({len(content)} chars)")

            return LLMResponse(
                content=content,
                provider="groq",
                model=self.model,
                success=True,
            )

        except Exception as e:
            logger.error(f"Groq generation failed: {e}")
            return LLMResponse(
                content="",
                provider="groq",
                model=self.model,
                success=False,
                error=str(e),
            )