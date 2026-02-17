from anthropic import Anthropic

from .base_processor import BaseProcessor


class ClaudeProcessor(BaseProcessor):
    """Anthropic Claude API processor for spine survey data extraction."""

    def __init__(self, api_key: str, model: str = None):
        super().__init__(api_key, model)
        self.client = Anthropic(api_key=api_key)

    def _default_model(self) -> str:
        return "claude-haiku-4-5-20251001"

    def _call_api(self, encoded_image: str, page_num: int) -> str:
        """Send image to Claude API and return the text response."""
        user_message = f"page_index:{page_num}\n\n{self.page_instructions[str(page_num)]}"

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_message,
                    },
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": encoded_image,
                        },
                    },
                ],
            }
        ]

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=self.system_prompt,
            messages=messages,
        )

        if isinstance(response.content, list):
            return response.content[0].text
        return response.content

