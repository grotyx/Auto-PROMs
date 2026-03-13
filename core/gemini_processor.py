import base64

from google import genai
from google.genai import types

from .base_processor import BaseProcessor


class GeminiProcessor(BaseProcessor):
    """Google Gemini API processor for spine survey data extraction."""

    def __init__(self, api_key: str, model: str = None):
        super().__init__(api_key, model)
        self.client = genai.Client(api_key=api_key)

    def _default_model(self) -> str:
        return "gemini-3.1-flash-lite-preview"

    def _call_api(self, encoded_image: str, page_num: int) -> str:
        """Send image to Gemini API and return the text response."""
        user_message = f"page_index:{page_num}\n\n{self.page_instructions[str(page_num)]}"

        image_bytes = base64.b64decode(encoded_image)

        response = self.client.models.generate_content(
            model=self.model,
            contents=[
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type="image/jpeg",
                ),
                user_message,
            ],
            config=types.GenerateContentConfig(
                system_instruction=self.system_prompt,
                temperature=0,
                max_output_tokens=4096,
                response_mime_type="application/json",
            ),
        )

        return response.text
