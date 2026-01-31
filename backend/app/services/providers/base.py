from abc import ABC, abstractmethod

class Provider(ABC):
  """Abstract base class for all AI providers."""

  @abstractmethod
  async def vision(self, image_base64: str, prompt: str) -> str:
    """Send image + prompt, return raw text response."""
    pass

  @abstractmethod
  async def complete(self, prompt: str) -> str:
    """Text completion. For future reasoning tasks."""
    pass