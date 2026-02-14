import asyncio
import os
from typing import Optional

import httpx
from dotenv import load_dotenv

from .base import Provider, ProviderError

load_dotenv()

# Retry config for rate limits (429)
MAX_RETRIES = 3
BASE_DELAY = 20.0  # 20s, 40s, 80s — long enough to actually clear TPM window


class GroqProvider(Provider):
    """Groq cloud inference. Fast, free tier, data leaves machine."""

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.base_url = "https://api.groq.com/openai/v1"

    async def vision(self, image_base64: str, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "meta-llama/llama-4-scout-17b-16e-instruct",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            },
                        },
                    ],
                }
            ],
            "max_tokens": 1024,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions", headers=headers, json=payload
            )
        data = response.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "")

    async def complete(
        self,
        prompt: str,
        *,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
    ) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        # Conditionally prepend a system prompt if provided
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": model or "llama-3.3-70b-versatile",
            "messages": messages,
            "max_tokens": 1024,
            "response_format": {
                "type": "json_object"
            },  # Ensure Groq returns a valid JSON object but does NOT guarantee JSON matches schema
        }

        # --- Boundary 1: Network call to Groq API (with retry for rate limits) ---
        last_error = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions", headers=headers, json=payload
                    )
                response.raise_for_status()
                break  # Success — exit retry loop
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and attempt < MAX_RETRIES:
                    delay = BASE_DELAY * (2 ** attempt)  # 15, 30, 60, 120, 240
                    print(f"  ⏳ Rate limited (attempt {attempt + 1}/{MAX_RETRIES}), waiting {delay:.0f}s...")
                    await asyncio.sleep(delay)
                    last_error = e
                    continue
                raise ProviderError(
                    f"Groq API returned an error: {e.response.status_code} - {e.response.text[:200]}..."
                )
            except httpx.TimeoutException:
                raise ProviderError("Request to Groq API timed out after 60s.")
            except httpx.RequestError as e:
                raise ProviderError(
                    f"An error occurred while requesting Groq API: {str(e)}"
                )
        else:
            # Exhausted all retries
            raise ProviderError(
                f"Groq API rate limit exceeded after {MAX_RETRIES} retries. Last error: {last_error}"
            )

        # --- Boundary 2: Parsing Groq response ---
        try:
            data = response.json()
        except ValueError:
            raise ProviderError(
                f"Groq API did not return valid JSON: {response.text[:200]}..."
            )  # Show first 200 chars of response for debugging

        # --- Boundary 3: Extracting content from Groq response (fail loud) ---
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

        if not content:
            raise ProviderError(
                f"Groq API response is missing expected content field: {data}"
            )

        return content
