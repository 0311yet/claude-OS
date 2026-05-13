from abc import ABC, abstractmethod

class VisionProvider(ABC):
    def __init__(self, api_key: str, model: str = None):
        self.api_key = api_key
        self.model = model or self.default_model

    @abstractmethod
    def analyze(self, image_base64: str, mime_type: str, prompt: str) -> str:
        """Analyze a single image."""
        pass

    @abstractmethod
    def compare(self, image1_base64: str, mime_type1: str, image2_base64: str, mime_type2: str, prompt: str) -> str:
        """Compare two images."""
        pass
