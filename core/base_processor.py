import base64
import json
import logging
import re
import threading
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import cv2
import numpy as np

from . import DATA_DIR
from .validators import SurveyValidator


class SimpleRateLimiter:
    """Thread-safe rate limiter using semaphore."""

    def __init__(self, max_concurrent: int = 3):
        self._semaphore = threading.Semaphore(max_concurrent)

    def acquire(self):
        self._semaphore.acquire()

    def release(self):
        self._semaphore.release()


class BaseProcessor(ABC):
    """Abstract base class for AI-powered spine survey processors.

    Subclasses must implement ``_call_api`` which sends an encoded image
    and page instruction to the provider-specific API and returns the
    raw text content of the response.
    """

    def __init__(self, api_key: str, model: str = None):
        self.api_key = api_key
        self.logger = logging.getLogger(self.__class__.__name__)

        if model:
            self.model = model
        else:
            try:
                from .config import load_config
                self.model = load_config().get_model()
            except Exception:
                self.model = self._default_model()

        # Concurrency settings (loaded from config, with safe defaults)
        self._concurrent_enabled = False
        self._max_workers = 3
        self._load_concurrency_settings()

        # Rate limiter for concurrent API calls
        self._rate_limiter = SimpleRateLimiter(self._max_workers)

        self.page_instructions = self._load_instructions()
        self.system_prompt = self._load_system_prompt()

    def _load_concurrency_settings(self):
        """Load concurrency settings from config.json."""
        try:
            from .config import load_config
            processing = load_config().get_processing_config()
            self._concurrent_enabled = processing.get('concurrent_enabled', False)
            self._max_workers = max(1, min(6, processing.get('max_concurrent_requests', 3)))
        except Exception:
            pass

    def _default_model(self) -> str:
        """Return the default model name (overridden by subclasses if needed)."""
        return "gpt-5-mini"

    # ------------------------------------------------------------------
    # Instruction loading (identical in both original processors)
    # ------------------------------------------------------------------

    def _load_instructions(self) -> Dict:
        """Load page instructions from page_instruction.json."""
        try:
            instruction_path = DATA_DIR / 'page_instruction.json'
            with open(instruction_path, 'r', encoding='utf-8') as f:
                instructions_raw = json.load(f)

            instructions = {}
            for key, value in instructions_raw.items():
                if key == "system_prompt":
                    continue
                if isinstance(value, list):
                    instructions[key] = "\n".join(value)
                else:
                    instructions[key] = value

            self.logger.info("Successfully loaded page instructions from JSON file")
            return instructions

        except Exception as e:
            self.logger.error(f"Error loading page instructions: {e}")
            return {}

    def _load_system_prompt(self) -> str:
        """Load system prompt from page_instruction.json."""
        try:
            instruction_path = DATA_DIR / 'page_instruction.json'
            with open(instruction_path, 'r', encoding='utf-8') as f:
                instructions_raw = json.load(f)

            if "system_prompt" in instructions_raw:
                prompt = instructions_raw["system_prompt"]
                if isinstance(prompt, list):
                    return "\n".join(prompt)
                return prompt
            else:
                return (
                    "당신은 의료 설문지 이미지를 분석하여 데이터를 추출하는 전문가입니다.\n"
                    "각 이미지에서 요청된 정보를 정확하게 추출하여 JSON 형식으로 반환해주세요.\n"
                    "응답은 반드시 순수한 JSON 형식이어야 하며, 추가적인 설명이나 마크다운 블록을 포함하지 마세요."
                )

        except Exception as e:
            self.logger.error(f"Error loading system prompt: {e}")
            return (
                "당신은 의료 설문지 이미지를 분석하여 데이터를 추출하는 전문가입니다.\n"
                "각 이미지에서 요청된 정보를 정확하게 추출하여 JSON 형식으로 반환해주세요.\n"
                "응답은 반드시 순수한 JSON 형식이어야 하며, 추가적인 설명이나 마크다운 블록을 포함하지 마세요."
            )

    # ------------------------------------------------------------------
    # Image encoding
    # ------------------------------------------------------------------

    def encode_image(self, image_array: np.ndarray) -> str:
        """Encode a numpy image array to a base64 JPEG string."""
        success, encoded_image = cv2.imencode(
            '.jpg', image_array, [cv2.IMWRITE_JPEG_QUALITY, 98]
        )
        if not success:
            raise ValueError("Image encoding failed")
        return base64.b64encode(encoded_image.tobytes()).decode('utf-8')

    # ------------------------------------------------------------------
    # Single page processing helper (used by both paths)
    # ------------------------------------------------------------------

    def _process_single_page(
        self, page_num: int, image: np.ndarray
    ) -> Optional[Dict]:
        """Process one page: encode, call API, parse JSON, validate.

        Returns validated page_data dict, or None on failure.
        """
        if str(page_num) not in self.page_instructions:
            self.logger.error(f"Invalid page number: {page_num}")
            return None

        self.logger.info(
            f"Processing page {page_num + 1} (internal index: {page_num})"
        )

        try:
            encoded_image = self.encode_image(image)
        except Exception as e:
            self.logger.error(
                f"Error encoding image for page {page_num + 1}: {e}"
            )
            return None

        # Call provider-specific API (rate-limited, with retry)
        max_retries = 2
        content = None
        last_error = None

        for attempt in range(max_retries + 1):
            self._rate_limiter.acquire()
            try:
                content = self._call_api(encoded_image, page_num)
                break
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    wait = 2 ** attempt  # 1s, 2s
                    self.logger.warning(
                        f"Page {page_num + 1} API call failed (attempt "
                        f"{attempt + 1}/{max_retries + 1}): {e}. "
                        f"Retrying in {wait}s..."
                    )
                    time.sleep(wait)
                else:
                    self.logger.error(
                        f"Page {page_num + 1} failed after "
                        f"{max_retries + 1} attempts: {e}"
                    )
            finally:
                self._rate_limiter.release()

        if content is None:
            return None

        # Parse JSON response
        try:
            page_data = json.loads(content)
        except json.JSONDecodeError:
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                try:
                    page_data = json.loads(json_match.group())
                except json.JSONDecodeError:
                    self.logger.error(
                        f"Failed to parse JSON even after regex "
                        f"on page {page_num + 1}"
                    )
                    self.logger.error(
                        f"Extracted content: {json_match.group()}"
                    )
                    return None
            else:
                self.logger.error(
                    f"No JSON-like content found in response "
                    f"for page {page_num + 1}"
                )
                self.logger.error(f"Full response: {content}")
                return None

        # Error response check
        if isinstance(page_data, dict) and "error" in page_data:
            self.logger.warning(
                f"Page {page_num + 1} returned error: {page_data['error']}"
            )
            return None

        # Validate
        page_data = SurveyValidator.validate_page_data(
            page_num, page_data, self.logger
        )
        self.logger.info(
            f"Validated data for page {page_num + 1}: {page_data}"
        )
        return page_data

    # ------------------------------------------------------------------
    # Processing pipeline
    # ------------------------------------------------------------------

    def process_images(
        self,
        processed_images: List[Tuple[int, np.ndarray]],
        progress_callback: Optional[Callable] = None,
    ) -> List[Dict]:
        """Process all images, grouping into 6-page surveys."""
        survey_data = []
        total_pages = len(processed_images)

        for i in range(0, total_pages, 6):
            if i + 6 <= total_pages:
                visit_images = processed_images[i:i + 6]
                self.logger.info(
                    f"Processing survey {i // 6 + 1} of {total_pages // 6}"
                )

                try:
                    normalized_images = [(idx % 6, img) for idx, img in visit_images]
                    visit_data = self.process_single_visit(
                        normalized_images,
                        progress_callback=progress_callback,
                    )

                    if visit_data and isinstance(visit_data, dict):
                        survey_data.append(visit_data)
                        rc_id_display = visit_data.get('rc_id') or '(missing)'
                        self.logger.info(
                            f"Successfully processed survey {i // 6 + 1} "
                            f"with rc_id: {rc_id_display}"
                        )
                    else:
                        self.logger.warning(
                            f"Invalid or missing data for survey {i // 6 + 1}"
                        )

                except Exception as e:
                    self.logger.error(
                        f"Error processing survey at pages {i + 1}-{i + 6}: {e}"
                    )
                    continue
            else:
                remaining_pages = total_pages - i
                self.logger.warning(
                    f"Skipping incomplete survey at the end: "
                    f"{remaining_pages} pages remaining"
                )

        self.logger.info(f"Processed {len(survey_data)} complete surveys")
        return survey_data

    def process_single_visit(
        self,
        visit_images: List[Tuple[int, np.ndarray]],
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Dict:
        """Process a single visit (6 pages) and return aggregated data.

        Uses concurrent processing when enabled in config, otherwise
        falls back to sequential processing. Results are always merged
        in page order.

        Args:
            visit_images: List of (page_num, image_array) tuples.
            progress_callback: Optional callback(page_num, total_pages)
                called after each page completes.
        """
        total_pages = len(visit_images)

        if self._concurrent_enabled and total_pages > 1:
            return self._process_visit_concurrent(
                visit_images, progress_callback
            )
        return self._process_visit_sequential(
            visit_images, progress_callback
        )

    def _process_visit_sequential(
        self,
        visit_images: List[Tuple[int, np.ndarray]],
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Dict:
        """Sequential page processing (original behavior)."""
        try:
            all_data = {}
            total_pages = len(visit_images)

            for page_num, image in visit_images:
                page_data = self._process_single_page(page_num, image)
                if page_data is not None:
                    all_data.update(page_data)
                if progress_callback:
                    try:
                        progress_callback(page_num, total_pages)
                    except Exception:
                        pass

            all_data.update(self._completion_flags())
            self.logger.info(f"Final processed data: {all_data}")
            return all_data

        except Exception as e:
            self.logger.error(f"Error processing visit: {e}")
            raise

    def _process_visit_concurrent(
        self,
        visit_images: List[Tuple[int, np.ndarray]],
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Dict:
        """Concurrent page processing using ThreadPoolExecutor.

        Pages are submitted in parallel but results are merged in
        page order. A single page failure does not stop other pages.
        """
        total_pages = len(visit_images)
        results: Dict[int, Optional[Dict]] = {}

        self.logger.info(
            f"Starting concurrent processing with "
            f"max_workers={self._max_workers}"
        )

        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            future_to_page = {
                executor.submit(
                    self._process_single_page, page_num, image
                ): page_num
                for page_num, image in visit_images
            }

            for future in as_completed(future_to_page):
                page_num = future_to_page[future]
                try:
                    results[page_num] = future.result()
                except Exception as e:
                    self.logger.error(
                        f"Page {page_num + 1} failed in concurrent "
                        f"processing: {e}"
                    )
                    results[page_num] = None

                if progress_callback:
                    try:
                        progress_callback(page_num, total_pages)
                    except Exception:
                        pass

        # Merge results in page order
        all_data = {}
        for page_num in sorted(results.keys()):
            page_data = results[page_num]
            if page_data is not None:
                all_data.update(page_data)

        all_data.update(self._completion_flags())
        self.logger.info(f"Final processed data (concurrent): {all_data}")
        return all_data

    @staticmethod
    def _completion_flags() -> Dict:
        """Return the standard completion flag dict."""
        return {
            'visit_day_complete': 2,
            'vas_complete': 2,
            'owestry_disability_index_complete': 2,
            'eq5d5l_complete': 2,
            'paindetect_complete': 2,
        }

    # ------------------------------------------------------------------
    # Abstract method
    # ------------------------------------------------------------------

    @abstractmethod
    def _call_api(self, encoded_image: str, page_num: int) -> str:
        """Send an image to the AI provider and return the text response.

        Args:
            encoded_image: Base64-encoded JPEG image string.
            page_num: The page index (0-5).

        Returns:
            The raw text content from the API response.
        """
        ...
