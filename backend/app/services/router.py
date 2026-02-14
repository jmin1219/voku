import os
from dotenv import load_dotenv
from .providers import GroqProvider, OllamaProvider, Provider

load_dotenv()


def get_provider(sensitive: bool = False) -> Provider:
    """
    Route to appropriate LLM provider.

    Privacy-first: user controls where their data goes.
    - VOKU_PROVIDER=local  → all processing stays on your machine (Ollama)
    - VOKU_PROVIDER=groq   → cloud processing (faster, data leaves machine)
    - sensitive=True       → forces local regardless of setting

    Args:
        sensitive: If True, override to local provider (Ollama)

    Returns:
        Provider instance
    """
    if sensitive:
        return OllamaProvider()

    provider_setting = os.getenv("VOKU_PROVIDER", "groq").lower()

    if provider_setting == "local":
        return OllamaProvider()

    # Auto-fallback: no API key → use local (Constraint 3.11: zero-cost default)
    if not os.getenv("GROQ_API_KEY"):
        return OllamaProvider()

    return GroqProvider()
