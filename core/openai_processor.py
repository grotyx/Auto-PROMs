import openai

from .base_processor import BaseProcessor


class OpenAIProcessor(BaseProcessor):
    """OpenAI GPT API processor for spine survey data extraction."""

    def __init__(self, api_key: str, model: str = None):
        super().__init__(api_key, model)
        self.client = openai.OpenAI(api_key=api_key)

    def _default_model(self) -> str:
        return "gpt-5-mini"

    def _call_api(self, encoded_image: str, page_num: int) -> str:
        """Send image to OpenAI API and return the text response."""
        user_message = f"page_index:{page_num}\n\n{self.page_instructions[str(page_num)]}"

        messages = [
            {
                "role": "system",
                "content": self.system_prompt,
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_message,
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{encoded_image}",
                        },
                    },
                ],
            },
        ]

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_completion_tokens=4096,
            response_format={"type": "json_object"},
        )

        return response.choices[0].message.content
