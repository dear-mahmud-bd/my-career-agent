from app.services.llm.base import BaseLLMClient, LLMResponse
from app.services.llm.groq_client import GroqClient
from app.services.llm.ollama_client import OllamaClient
from app.core.config import settings
from app.core.logger import logger


class LLMRouter:
    """
    Smart LLM router with auto fallback.

    Modes:
      groq  → use Groq only
      ollama → use Ollama only
      auto  → try Groq first, fall back to Ollama silently
    """

    def __init__(self):
        self.groq = GroqClient()
        self.ollama = OllamaClient()
        self.provider = settings.llm_provider

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1000,
    ) -> LLMResponse:

        if self.provider == "groq":
            return await self._use_groq(
                prompt, system_prompt, temperature, max_tokens
            )

        elif self.provider == "ollama":
            return await self._use_ollama(
                prompt, system_prompt, temperature, max_tokens
            )

        else:
            # auto mode — Groq first, Ollama fallback
            return await self._auto(
                prompt, system_prompt, temperature, max_tokens
            )

    async def _use_groq(
        self, prompt, system_prompt, temperature, max_tokens
    ) -> LLMResponse:
        logger.debug("Using Groq as LLM provider")
        response = await self.groq.generate(
            prompt, system_prompt, temperature, max_tokens
        )
        if not response.success:
            logger.error(
                f"Groq failed: {response.error}. "
                f"Switch LLM_PROVIDER=ollama or LLM_PROVIDER=auto"
            )
        return response

    async def _use_ollama(
        self, prompt, system_prompt, temperature, max_tokens
    ) -> LLMResponse:
        logger.debug("Using Ollama as LLM provider")

        # Check if Ollama is running
        if not await self.ollama.is_available():
            logger.error(
                "Ollama is not running or model not pulled. "
                f"Please run: ollama serve && ollama pull {settings.ollama_model}"
            )
            return LLMResponse(
                content="",
                provider="ollama",
                model=settings.ollama_model,
                success=False,
                error=(
                    f"Ollama not available. "
                    f"Run: ollama serve && ollama pull {settings.ollama_model}"
                ),
            )

        return await self.ollama.generate(
            prompt, system_prompt, temperature, max_tokens
        )

    async def _auto(
        self, prompt, system_prompt, temperature, max_tokens
    ) -> LLMResponse:
        """Try Groq first. If it fails, silently fall back to Ollama."""

        # Try Groq first
        if settings.groq_api_key:
            logger.debug("Auto mode: trying Groq first")
            response = await self.groq.generate(
                prompt, system_prompt, temperature, max_tokens
            )
            if response.success:
                return response
            logger.warning(
                f"Groq failed ({response.error}), "
                f"falling back to Ollama..."
            )

        # Fall back to Ollama
        logger.debug("Auto mode: switching to Ollama")
        if not await self.ollama.is_available():
            logger.error(
                "Both Groq and Ollama are unavailable. "
                f"To use Ollama: ollama serve && ollama pull {settings.ollama_model}"
            )
            return LLMResponse(
                content="",
                provider="none",
                model="none",
                success=False,
                error=(
                    "Both Groq and Ollama are unavailable. "
                    "Check your GROQ_API_KEY or start Ollama."
                ),
            )

        return await self.ollama.generate(
            prompt, system_prompt, temperature, max_tokens
        )

    async def get_active_provider(self) -> str:
        """Returns which provider is currently active."""
        if self.provider == "groq":
            return "groq"
        elif self.provider == "ollama":
            return "ollama"
        else:
            if settings.groq_api_key and await self.groq.is_available():
                return "groq"
            elif await self.ollama.is_available():
                return "ollama"
            return "none"


# Single instance used everywhere
llm_router = LLMRouter()