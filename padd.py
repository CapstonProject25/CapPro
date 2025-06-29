import re
import cv2
import numpy as np
from paddleocr import PaddleOCR

class UniversalReceiptProcessor:
    def __init__(self):
        # 개선된 가격 패턴 (소수점 및 다양한 화폐 단위 지원)
        self.price_pattern = re.compile(
            r'(?:\d{1,3}(?:[,\s]?\d{3})*(?:\.\d{1,2})?|\d+)\s*'
            r'(?:원|₩|￦|USD|KRW|\$)?'
        )
        
        # 공간 그룹화를 위한 임계값 설정
        self.y_threshold = 15
        self.x_threshold = 50

    def preprocess_image(self, img):
        """이미지 전처리: 조명 보정 및 이진화"""
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()
        
        # CLAHE를 통한 조명 보정
        lab = cv2.cvtColor(cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR), cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        cl = clahe.apply(l)
        limg = cv2.merge((cl, a, b))
        enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY)
        
        # 적응형 이진화
        binary = cv2.adaptiveThreshold(
            enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 31, 12
        )
        return binary

    def spatial_grouping(self, ocr_result):
        """OCR 결과를 공간 기반 그룹화"""
        elements = []
        for page in ocr_result:
            for line in page:
                box = np.array(line[0])
                text = line[1][0]
                x_coords = box[:, 0]
                y_coords = box[:, 1]
                
                elements.append({
                    'text': text,
                    'x_min': x_coords.min(),
                    'x_max': x_coords.max(),
                    'y_min': y_coords.min(),
                    'y_max': y_coords.max(),
                    'y_center': (y_coords.min() + y_coords.max()) / 2,
                    'x_center': (x_coords.min() + x_coords.max()) / 2
                })
        
        # Y 중심점 기준 정렬
        elements.sort(key=lambda x: x['y_center'])
        
        # 그룹화 수행
        groups = []
        current_group = []
        current_y_center = None
        
        for element in elements:
            if not current_group:
                current_group.append(element)
                current_y_center = element['y_center']
            else:
                y_diff = abs(element['y_center'] - current_y_center)
                if y_diff <= self.y_threshold:
                    current_group.append(element)
                else:
                    current_group.sort(key=lambda x: x['x_center'])
                    groups.append(current_group)
                    current_group = [element]
                    current_y_center = element['y_center']
        
        if current_group:
            current_group.sort(key=lambda x: x['x_center'])
            groups.append(current_group)
        
        return groups

    def extract_menu_prices(self, groups):
        """그룹화된 텍스트에서 메뉴-가격 쌍 추출"""
        menu_price_pairs = []
        for group in groups:
            line_text = " ".join(elem["text"] for elem in group)
            
            # 가격 패턴 매칭 (마지막 가격 우선)
            price_matches = list(self.price_pattern.finditer(line_text))
            if price_matches:
                last_match = price_matches[-1]
                price_str = last_match.group().strip()
                menu_str = line_text[:last_match.start()].strip()
                
                # 가격 정제 (숫자만 추출)
                price_num = re.sub(r'[^\d.]', '', price_str)
                if price_num:
                    menu_price_pairs.append((menu_str, price_num))
                    
        return menu_price_pairs

    def process_receipt(self, image_path):
        """영수증 이미지 전체 처리 파이프라인"""
        # 이미지 로드 및 전처리
        original_img = cv2.imread(image_path)
        if original_img is None:
            raise ValueError(f"이미지 로드 실패: {image_path}")
        
        processed_img = self.preprocess_image(original_img)
        
        # OCR 파라미터 동적 설정
        is_dark = np.mean(processed_img) < 100
        is_blurry = cv2.Laplacian(processed_img, cv2.CV_64F).var() < 100
        
        ocr_params = {
            'lang': 'korean',
            'use_angle_cls': True,
            'det_db_thresh': 0.4 if is_dark else 0.3,
            'det_db_box_thresh': 0.6 if is_blurry else 0.5,
            'det_db_unclip_ratio': 1.8 if is_blurry else 1.5
        }
        
        # OCR 수행
        ocr = PaddleOCR(**ocr_params)
        ocr_result = ocr.ocr(processed_img)
        
        # 공간 그룹화 및 메뉴-가격 추출
        spatial_groups = self.spatial_grouping(ocr_result)
        return self.extract_menu_prices(spatial_groups)
