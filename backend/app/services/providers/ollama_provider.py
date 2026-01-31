import httpx
from .base import Provider

class OllamaProvider(Provider):
  """Local Ollama inference. Private, free, but slower."""
  def __init__(self, base_url: str = "http://localhost:11434"):
    self.base_url = base_url

  async def vision(self, image_base64: str, prompt: str) -> str:
    async with httpx.AsyncClient(timeout=60.0) as client:
      response = await client.post(
        f"{self.base_url}/api/generate",
        json={
          "model": "llama3.2-vision",
          "prompt": prompt,
          "images": [image_base64],
          "stream": False
        }
      )
    return response.json().get("response", "")
  
  async def complete(self, prompt: str) -> str:
    async with httpx.AsyncClient(timeout=60.0) as client:
      response = await client.post(
        f"{self.base_url}/api/generate",
        json={
          "model": "llama3.2",
          "prompt": prompt,
          "stream": False
        }
      )
    return response.json().get("response", "")