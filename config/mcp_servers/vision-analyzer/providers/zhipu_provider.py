import httpx
from .base import VisionProvider

class ZhiPuProvider(VisionProvider):
    default_model = "glm-4v-flash"

    def analyze(self, image_base64: str, mime_type: str, prompt: str) -> str:
        url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_base64}"}}
        ]

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": content}]
        }

        try:
            response = httpx.post(url, json=payload, headers=headers, timeout=60.0)
            response.raise_for_status()
            result = response.json()
            try:
                return result["choices"][0]["message"]["content"]
            except (KeyError, IndexError) as e:
                raise ValueError(f"Unexpected API response structure: {str(e)}")
        except httpx.TimeoutException:
            raise ValueError("ZhiPu API request timed out")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise ValueError("ZhiPu API key is invalid or missing")
            elif e.response.status_code == 429:
                raise ValueError("ZhiPu API rate limit exceeded")
            else:
                raise ValueError(f"ZhiPu API error: {e.response.status_code}")
        except Exception as e:
            raise ValueError(f"Failed to analyze image with ZhiPu: {str(e)}")

    def compare(self, image1_base64: str, mime_type1: str, image2_base64: str, mime_type2: str, prompt: str) -> str:
        url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:{mime_type1};base64,{image1_base64}"}},
            {"type": "image_url", "image_url": {"url": f"data:{mime_type2};base64,{image2_base64}"}}
        ]

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": content}]
        }

        try:
            response = httpx.post(url, json=payload, headers=headers, timeout=60.0)
            response.raise_for_status()
            result = response.json()
            try:
                return result["choices"][0]["message"]["content"]
            except (KeyError, IndexError) as e:
                raise ValueError(f"Unexpected API response structure: {str(e)}")
        except httpx.TimeoutException:
            raise ValueError("ZhiPu API request timed out")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise ValueError("ZhiPu API key is invalid or missing")
            elif e.response.status_code == 429:
                raise ValueError("ZhiPu API rate limit exceeded")
            else:
                raise ValueError(f"ZhiPu API error: {e.response.status_code}")
        except Exception as e:
            raise ValueError(f"Failed to compare images with ZhiPu: {str(e)}")
