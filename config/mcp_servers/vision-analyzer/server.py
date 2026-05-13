#!/usr/bin/env python3
import os
import base64
import mimetypes
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from providers import get_provider

VISION_PROVIDER = os.getenv("VISION_PROVIDER", "openai")
VISION_API_KEY = os.getenv("VISION_API_KEY")
VISION_MODEL = os.getenv("VISION_MODEL")
WORKSPACE_DIR = os.getenv("WORKSPACE_DIR", os.getcwd())

if not VISION_API_KEY:
    raise ValueError("VISION_API_KEY environment variable is required")

mcp = FastMCP("vision-analyzer")
provider = get_provider(VISION_PROVIDER, VISION_API_KEY, VISION_MODEL)

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_PROMPT_LENGTH = 2000

def read_image_as_base64(image_path: str) -> tuple[str, str]:
    """Read an image file and return (base64_data, mime_type)."""
    try:
        # Resolve to absolute path
        abs_path = Path(image_path).resolve()

        # Check path is within workspace directory
        workspace_path = Path(WORKSPACE_DIR).resolve()
        try:
            abs_path.relative_to(workspace_path)
        except ValueError:
            raise ValueError(f"Path is outside workspace directory: {image_path}")

        # Check file extension
        if abs_path.suffix.lower() not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Invalid file type: {abs_path.suffix}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")

        # Check file exists and is a file
        if not abs_path.is_file():
            raise ValueError(f"Not a valid file: {image_path}")

        # Check file size before reading
        file_size = abs_path.stat().st_size
        if file_size > MAX_FILE_SIZE:
            raise ValueError(f"File too large: {file_size / 1024 / 1024:.1f}MB (max {MAX_FILE_SIZE / 1024 / 1024}MB)")

        with open(abs_path, "rb") as f:
            image_data = f.read()
        base64_data = base64.b64encode(image_data).decode("utf-8")

        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type or not mime_type.startswith("image/"):
            mime_type = "image/png"

        return base64_data, mime_type
    except FileNotFoundError:
        raise ValueError(f"Image file not found: {image_path}")
    except Exception as e:
        raise ValueError(f"Failed to read image file: {str(e)}")

@mcp.tool()
def analyze_image(image_path: str, prompt: str) -> str:
    """Analyze an image using a vision model.

    Args:
        image_path: Path to the image file
        prompt: Text prompt describing what to analyze or look for
    """
    # Validate prompt
    if not isinstance(prompt, str):
        raise ValueError("Prompt must be a string")
    if not prompt.strip():
        raise ValueError("Prompt cannot be empty")
    if len(prompt) > MAX_PROMPT_LENGTH:
        raise ValueError(f"Prompt too long: {len(prompt)} chars (max {MAX_PROMPT_LENGTH})")

    image_base64, mime_type = read_image_as_base64(image_path)
    return provider.analyze(image_base64, mime_type, prompt)

@mcp.tool()
def compare_images(image_path_1: str, image_path_2: str, prompt: str) -> str:
    """Compare two images using a vision model.

    Args:
        image_path_1: Path to the first image file
        image_path_2: Path to the second image file
        prompt: Text prompt describing what to compare or look for
    """
    # Validate prompt
    if not isinstance(prompt, str):
        raise ValueError("Prompt must be a string")
    if not prompt.strip():
        raise ValueError("Prompt cannot be empty")
    if len(prompt) > MAX_PROMPT_LENGTH:
        raise ValueError(f"Prompt too long: {len(prompt)} chars (max {MAX_PROMPT_LENGTH})")

    image1_base64, mime_type1 = read_image_as_base64(image_path_1)
    image2_base64, mime_type2 = read_image_as_base64(image_path_2)
    return provider.compare(image1_base64, mime_type1, image2_base64, mime_type2, prompt)

if __name__ == "__main__":
    mcp.run()
