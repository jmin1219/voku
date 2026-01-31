from .providers import GroqProvider, OllamaProvider, Provider

def get_provider(task: str = "vision", sensitive: bool = False) -> Provider:
    """
    Route to appropriate provider.
    
    Args:
        task: "vision" or "reasoning"
        sensitive: If True, always use local (Ollama)
    
    Returns:
        Provider instance
    """
    if sensitive:
        return OllamaProvider()
    
    # Default: use Groq for speed (free tier)
    return GroqProvider()