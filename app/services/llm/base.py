from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    content: str
    provider: str
    model: str
    success: bool
    error: str | None = None


class BaseLLMClient(ABC):
    """Abstract base class for all LLM providers."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1000,
    ) -> LLMResponse:
        """Generate a response from the LLM."""
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if this LLM provider is available."""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return provider name."""
        pass