from abc import ABC, abstractmethod
from typing import Optional


class Provider(ABC):
    """Abstract base class for all AI providers."""

    @abstractmethod  # Means if a subclass doesn't implement this method, it will raise a TypeError at instantiation, not just at call time.
    async def vision(self, image_base64: str, prompt: str) -> str:
        """Send image + prompt, return raw text response."""
        pass

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        *,  # Everything after this must be a keyword argument (ie. caller must explicitly name parameters)
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
    ) -> str:
        """Text completion. For future reasoning tasks."""
        pass


class ProviderError(Exception):
    """Custom exception for LLM provider errors."""

    pass
