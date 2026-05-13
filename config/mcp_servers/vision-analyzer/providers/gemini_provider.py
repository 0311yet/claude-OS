import httpx
from .base import VisionProvider

class GeminiProvider(VisionProvider):
    default_model = "gemini-2.5-flash"

    def analyze(self, image_base64: str, mime_type: str, prompt: str) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": mime_type, "data": image_base64}}
                ]
            }]
        }

        try:
            response = httpx.post(url, json=payload, headers=headers, timeout=60.0)
            response.raise_for_status()
            result = response.json()
            try:
                return result["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError) as e:
                raise ValueError(f"Unexpected API response structure: {str(e)}")
        except httpx.TimeoutException:
            raise ValueError("Gemini API request timed out")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise ValueError("Gemini API key is invalid or missing")
            elif e.response.status_code == 429:
                raise ValueError("Gemini API rate limit exceeded")
            else:
                raise ValueError(f"Gemini API error: {e.response.status_code}")
        except Exception as e:
            raise ValueError(f"Failed to analyze image with Gemini: {str(e)}")

    def compare(self, image1_base64: str, mime_type1: str, image2_base64: str, mime_type2: str, prompt: str) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": mime_type1, "data": image1_base64}},
                    {"inline_data": {"mime_type": mime_type2, "data": image2_base64}}
                ]
            }]
        }

        try:
            response = httpx.post(url, json=payload, headers=headers, timeout=60.0)
            response.raise_for_status()
            result = response.json()
            try:
                return result["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError) as e:
                raise ValueError(f"Unexpected API response structure: {str(e)}")
        except httpx.TimeoutException:
            raise ValueError("Gemini API request timed out")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise ValueError("Gemini API key is invalid or missing")
            elif e.response.status_code == 429:
                raise ValueError("Gemini API rate limit exceeded")
            else:
                raise ValueError(f"Gemini API error: {e.response.status_code}")
        except Exception as e:
            raise ValueError(f"Failed to compare images with Gemini: {str(e)}")
