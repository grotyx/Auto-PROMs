import os
import logging
from pdf2image import convert_from_path
import cv2
import numpy as np
from typing import List, Tuple

class PDFProcessor:
    def __init__(self, pdf_path: str, temp_folder: str):
        self.pdf_path = pdf_path
        self.temp_folder = temp_folder
        os.makedirs(temp_folder, exist_ok=True)
        self.logger = logging.getLogger(__name__)
    
    def convert_pdf_to_images(self) -> List[str]:
        """PDF를 이미지로 변환"""
        self.logger.info("Starting PDF conversion...")
        
        try:
            # PDF 정보 먼저 확인
            from pdf2image.pdf2image import pdfinfo_from_path
            info = pdfinfo_from_path(self.pdf_path)
            self.logger.info(f"PDF has {info['Pages']} pages")

            # 성능 최적화 옵션 추가
            pages = convert_from_path(
                self.pdf_path,
                dpi=300,  # 높은 DPI 설정으로 텍스트 선명도 향상
                thread_count=4,  # 멀티스레딩 사용
                fmt='jpeg',
                grayscale=False,  # 컬러 정보 유지
                size=(2000, None)  # 큰 해상도 유지
            )
            
            image_paths = []
            self.logger.info(f"Converting {len(pages)} pages to images...")
            
            for i, page in enumerate(pages):
                image_path = os.path.join(self.temp_folder, f'page_{i}.jpg')
                page.save(image_path, 'JPEG', quality=95)  # 높은 품질 설정
                image_paths.append(image_path)
                self.logger.info(f"Saved page {i+1}/{len(pages)}")
            
            return image_paths
            
        except Exception as e:
            self.logger.error(f"Error in PDF conversion: {str(e)}")
            raise
    
    def preprocess_image(self, image_path: str) -> np.ndarray:
        """이미지 전처리 개선"""
        self.logger.info(f"Preprocessing image: {image_path}")
        
        try:
            # 이미지 읽기
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError(f"Failed to load image: {image_path}")

            # 이미지 크기 정규화
            height, width = img.shape[:2]
            if width > 2000:
                scale = 2000 / width
                width = 2000
                height = int(height * scale)
                img = cv2.resize(img, (width, height))

            # 그레이스케일 변환
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # 노이즈 제거
            denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)

            # 대비 향상
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(denoised)

            # 이진화
            _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # 모폴로지 연산으로 텍스트 선명도 향상
            kernel = np.ones((2,2), np.uint8)
            cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

            return cleaned
            
        except Exception as e:
            self.logger.error(f"Error preprocessing image: {str(e)}")
            raise
    
    def process_pdf(self) -> List[Tuple[int, np.ndarray]]:
        """전체 PDF 처리"""
        try:
            self.logger.info("Starting PDF processing...")
            image_paths = self.convert_pdf_to_images()
            processed_images = []
            
            self.logger.info("Processing converted images...")
            for i, image_path in enumerate(image_paths):
                self.logger.info(f"Processing image {i+1}/{len(image_paths)}")
                processed = self.preprocess_image(image_path)
                processed_images.append((i, processed))
                
                # 중간 결과 저장 (디버깅용)
                debug_path = os.path.join(self.temp_folder, f'processed_{i}.jpg')
                cv2.imwrite(debug_path, processed)
            
            self.logger.info(f"Successfully processed {len(processed_images)} images")
            return processed_images
            
        except Exception as e:
            self.logger.error(f"Error in PDF processing: {str(e)}")
            raise