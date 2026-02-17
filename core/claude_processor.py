import json
import re
import logging
from typing import Dict

import numpy as np
from anthropic import Anthropic

from .base_processor import BaseProcessor
from .validators import SurveyValidator


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

    # ------------------------------------------------------------------
    # Single image processing (used by GUI for single-page testing)
    # ------------------------------------------------------------------

    def process_single_image(self, image_array: np.ndarray, page_index: int) -> Dict:
        """Process a single image (called directly from the GUI)."""
        try:
            if str(page_index) not in self.page_instructions:
                self.logger.error(f"Invalid page index: {page_index}")
                return {"error": f"Invalid page index: {page_index}"}

            encoded_image = self.encode_image(image_array)

            # Call the Claude API
            content = self._call_api(encoded_image, page_index)

            # JSON parsing
            try:
                page_data = json.loads(content)
            except json.JSONDecodeError:
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    try:
                        page_data = json.loads(json_match.group())
                    except json.JSONDecodeError:
                        self.logger.error("Failed to parse JSON even after regex")
                        self.logger.error(f"Extracted content: {json_match.group()}")
                        return {"error": "Failed to parse response JSON"}
                else:
                    self.logger.error("No JSON-like content found in response")
                    self.logger.error(f"Full response: {content}")
                    return {"error": "No valid JSON in response"}

            if isinstance(page_data, dict) and "error" in page_data:
                self.logger.warning(f"API returned error: {page_data['error']}")
                return page_data

            page_data = SurveyValidator.validate_page_data(
                page_index, page_data, self.logger
            )

            self.logger.info(f"Successfully processed single image. Extracted data: {page_data}")
            return page_data

        except Exception as e:
            self.logger.error(f"Error processing single image: {e}")
            return {"error": f"Processing failed: {e}"}
