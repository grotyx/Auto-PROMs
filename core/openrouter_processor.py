import openai

from .openai_processor import OpenAIProcessor


class OpenRouterProcessor(OpenAIProcessor):
    """OpenRouter processor: any multimodal model behind one key.

    OpenRouter speaks the OpenAI chat/completions dialect, so the request
    building in :class:`OpenAIProcessor` is reused as-is; only the endpoint,
    the attribution headers and the default model differ. Models are named
    ``vendor/model`` (e.g. ``openai/gpt-5.6-luna``, ``qwen/qwen3-vl-235b-a22b-instruct``).
    """

    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self, api_key: str, model: str = None):
        super().__init__(api_key, model)
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=self.BASE_URL,
            default_headers={
                "HTTP-Referer": "https://github.com/grotyx/Auto-PROMs",
                "X-Title": "Auto-PROMs",
            },
        )

    def _default_model(self) -> str:
        return "openai/gpt-5.6-luna"
