import base64

from google import genai
from google.genai import types

from .base_processor import BaseProcessor


class GeminiProcessor(BaseProcessor):
    """Google Gemini API processor for spine survey data extraction."""

    def __init__(self, api_key: str, model: str = None):
        super().__init__(api_key, model)
        self.client = genai.Client(api_key=api_key)
        self.thinking_level = self._load_thinking_level()

    def _default_model(self) -> str:
        return "gemini-3.5-flash"

    def _load_thinking_level(self) -> str:
        """config.json에서 gemini thinking_level 로드 (실패 시 'minimal')."""
        try:
            from .config import load_config
            return load_config().get_gemini_thinking_level()
        except Exception:
            return "minimal"

    def _build_thinking_config(self):
        """thinking_level에 맞는 ThinkingConfig 생성. 미지원 SDK/모델이면 None."""
        if not self.thinking_level:
            return None
        try:
            return types.ThinkingConfig(thinking_level=self.thinking_level)
        except Exception as e:
            self.logger.warning(
                f"ThinkingConfig(thinking_level={self.thinking_level!r}) "
                f"unsupported, skipping: {e}"
            )
            return None

    def _call_api(self, encoded_image: str, page_num: int) -> str:
        """Send image to Gemini API and return the text response."""
        user_message = f"page_index:{page_num}\n\n{self.page_instructions[str(page_num)]}"

        image_bytes = base64.b64decode(encoded_image)

        config_kwargs = dict(
            system_instruction=self.system_prompt,
            temperature=self._temperature,
            max_output_tokens=self._max_tokens,
            response_mime_type="application/json",
        )
        thinking_config = self._build_thinking_config()
        if thinking_config is not None:
            config_kwargs["thinking_config"] = thinking_config

        response = self.client.models.generate_content(
            model=self.model,
            contents=[
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type="image/jpeg",
                ),
                user_message,
            ],
            config=types.GenerateContentConfig(**config_kwargs),
        )

        return response.text
