import os
import logging
import fitz  # PyMuPDF
import cv2
import numpy as np
from typing import List, Tuple
from PIL import Image
import io

class PDFProcessor:
    def __init__(self, pdf_path: str, temp_folder: str):
        self.pdf_path = pdf_path
        self.temp_folder = temp_folder
        os.makedirs(temp_folder, exist_ok=True)
        self.logger = logging.getLogger(__name__)
    
    def convert_pdf_to_images(self) -> List[str]:
        """PDF를 이미지로 변환 (PyMuPDF 사용)"""
        self.logger.info("Starting PDF conversion with PyMuPDF...")
        
        try:
            # PDF 문서 열기
            doc = fitz.open(self.pdf_path)
            self.logger.info(f"PDF has {len(doc)} pages")
            
            image_paths = []
            
            # 각 페이지를 이미지로 변환
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # 해상도 매트릭스 설정 (300 DPI 상당)
                # 기본 72 DPI에서 300 DPI로 변환하려면 약 4.17배 확대
                zoom_matrix = fitz.Matrix(4.17, 4.17)
                
                # 페이지를 픽셀맵으로 렌더링
                pix = page.get_pixmap(matrix=zoom_matrix, alpha=False)
                
                # 이미지 저장
                image_path = os.path.join(self.temp_folder, f'page_{page_num}.jpg')
                pix.save(image_path)
                image_paths.append(image_path)
                
                self.logger.info(f"Saved high-quality page {page_num + 1}/{len(doc)} (300 DPI)")
                
                # 메모리 정리
                pix = None
            
            # 문서 닫기
            doc.close()
            
            self.logger.info(f"Successfully converted {len(image_paths)} pages to 300 DPI")
            return image_paths
            
        except Exception as e:
            self.logger.error(f"Error in PDF conversion: {str(e)}")
            raise
    
    def preprocess_image(self, image_path: str) -> np.ndarray:
        """이미지 전처리 (컬러 유지)"""
        self.logger.info(f"Preprocessing image: {image_path}")
        
        try:
            # 이미지 읽기
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError(f"Failed to load image: {image_path}")

            # 이미지 크기 정규화 (너무 크면 축소)
            height, width = img.shape[:2]
            if width > 2000:
                scale = 2000 / width
                width = 2000
                height = int(height * scale)
                img = cv2.resize(img, (width, height), interpolation=cv2.INTER_LANCZOS4)

            # 노이즈 제거 (가우시안 블러 적용) - 컬러 이미지에 적용
            denoised = cv2.GaussianBlur(img, (3, 3), 0)

            # 컬러 이미지 대비 향상 (각 채널별로 CLAHE 적용)
            lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB)
            l_channel, a_channel, b_channel = cv2.split(lab)
            
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            l_channel = clahe.apply(l_channel)
            
            enhanced = cv2.merge([l_channel, a_channel, b_channel])
            enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)

            # 샤프닝 필터 적용 (텍스트 선명도 향상)
            kernel = np.array([[0, -1, 0],
                             [-1, 5, -1],
                             [0, -1, 0]])
            sharpened = cv2.filter2D(enhanced, -1, kernel)

            return sharpened
            
        except Exception as e:
            self.logger.error(f"Error preprocessing image: {str(e)}")
            raise
    
    def convert_pdf_to_images_high_quality(self) -> List[str]:
        """고품질 PDF to 이미지 변환 (300 DPI)"""
        self.logger.info("Starting high-quality PDF conversion...")
        
        try:
            doc = fitz.open(self.pdf_path)
            self.logger.info(f"PDF has {len(doc)} pages")
            
            image_paths = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # 고품질 설정 (300 DPI)
                # 기본 72 DPI에서 300 DPI로 변환하려면 약 4.17배 확대
                zoom_matrix = fitz.Matrix(4.17, 4.17)
                
                # 안티앨리어싱 활성화
                pix = page.get_pixmap(
                    matrix=zoom_matrix, 
                    alpha=False,
                    annots=True,  # 주석 포함
                    clip=None
                )
                
                # PIL Image로 변환하여 품질 최적화
                img_data = pix.tobytes("ppm")
                pil_image = Image.open(io.BytesIO(img_data))
                
                # JPEG 품질 98%로 저장 (더 높은 품질)
                image_path = os.path.join(self.temp_folder, f'page_{page_num}.jpg')
                pil_image.save(image_path, 'JPEG', quality=98, optimize=True)
                image_paths.append(image_path)
                
                self.logger.info(f"Saved page {page_num + 1}/{len(doc)} (300 DPI)")
                
                # 메모리 정리
                pix = None
                pil_image = None
            
            doc.close()
            
            self.logger.info(f"Successfully converted {len(image_paths)} pages to 300 DPI")
            return image_paths
            
        except Exception as e:
            self.logger.error(f"Error in high-quality PDF conversion: {str(e)}")
            # 실패 시 일반 변환으로 폴백
            return self.convert_pdf_to_images()
    
    def process_pdf(self) -> List[Tuple[int, np.ndarray]]:
        """전체 PDF 처리"""
        try:
            self.logger.info("Starting PDF processing with PyMuPDF...")
            
            # 고품질 변환 시도, 실패 시 일반 변환
            try:
                image_paths = self.convert_pdf_to_images_high_quality()
            except Exception as e:
                self.logger.warning(f"High-quality conversion failed: {str(e)}")
                self.logger.info("Falling back to standard conversion...")
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
    
    def get_page_count(self) -> int:
        """PDF의 총 페이지 수 반환"""
        try:
            doc = fitz.open(self.pdf_path)
            page_count = len(doc)
            doc.close()
            return page_count
        except Exception as e:
            self.logger.error(f"Error getting page count: {str(e)}")
            return 0
    
