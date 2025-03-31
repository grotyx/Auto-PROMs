from anthropic import Anthropic
import base64
import json
import numpy as np
import cv2
import logging
from typing import List, Dict, Tuple
from page_instructions import page_instructions  # page_instructions 임포트 추가


class ClaudeProcessor:
    def __init__(self, api_key: str):        
        self.client = Anthropic(api_key=api_key)
        self.logger = logging.getLogger(__name__)

    #Claude
    def encode_image(self, image_array: np.ndarray) -> str:
        """이미지를 base64로 인코딩"""
        success, encoded_image = cv2.imencode('.jpg', image_array)
        if not success:
            raise ValueError("Image encoding failed")
        return base64.b64encode(encoded_image.tobytes()).decode('utf-8')

    def process_images(self, processed_images: List[Tuple[int, np.ndarray]], progress_callback=None) -> List[Dict]:
            """모든 이미지 처리 - 6페이지씩 그룹화하여 각각의 설문으로 처리"""
            survey_data = []
            
            # 전체 페이지 수가 6의 배수인지 확인
            total_pages = len(processed_images)
            self.logger.info(f"Total number of pages: {total_pages}")
            if total_pages % 6 != 0:
                self.logger.warning(f"Total number of pages ({total_pages}) is not divisible by 6")
            
            total_surveys = total_pages // 6
            self.logger.info(f"Found {total_surveys} potential surveys in the PDF")
            
            # 진행률 초기화 - PDF 처리가 10%, 각 설문지 처리가 60%, CSV 생성이 30%
            current_progress = 10  # PDF 처리는 이미 완료된 상태
            survey_progress_per_unit = 60.0 / total_surveys if total_surveys > 0 else 0
            
            # 6페이지씩 그룹화하여 처리
            for i in range(0, total_pages, 6):
                if i + 6 <= total_pages:  # 완전한 6페이지 세트인지 확인
                    visit_images = processed_images[i:i+6]
                    current_survey = i//6 + 1
                    self.logger.info(f"Processing survey {current_survey} of {total_surveys} (pages {i+1}-{i+6})")
                    
                    # 진행 상태 업데이트
                    if progress_callback:
                        this_survey_progress = int(current_progress + (current_survey-1) * survey_progress_per_unit)
                        progress_callback(this_survey_progress, f"설문지 {current_survey}/{total_surveys} 처리 중... ({i+1}-{i+6}페이지)")
                    
                    try:
                        # 페이지 번호를 0부터 5까지로 재설정하여 전달
                        normalized_images = [(idx % 6, img) for idx, img in visit_images]
                        
                        # 진행률 콜백 전달하며 처리
                        visit_data = self.process_single_visit(normalized_images, progress_callback)
                        
                        if visit_data and isinstance(visit_data, dict) and 'rc_id' in visit_data and visit_data['rc_id']:
                            survey_data.append(visit_data)
                            self.logger.info(f"Successfully processed survey {current_survey} with rc_id: {visit_data['rc_id']}")
                            
                            # 설문지 완료 진행률 업데이트
                            if progress_callback:
                                this_survey_complete_progress = int(current_progress + current_survey * survey_progress_per_unit)
                                progress_callback(this_survey_complete_progress, 
                                                f"설문지 {current_survey}/{total_surveys} 처리 완료")
                        else:
                            self.logger.warning(f"Invalid or missing data for survey {current_survey}")
                            
                    except Exception as e:
                        self.logger.error(f"Error processing survey at pages {i+1}-{i+6}: {str(e)}")
                        continue
                else:
                    remaining_pages = total_pages - i
                    self.logger.warning(f"Skipping incomplete survey at the end: {remaining_pages} pages remaining")
            
            # 최종 처리 완료 - 70% 진행 상태 (CSV 생성 전)
            if progress_callback:
                progress_callback(70, "모든 설문지 처리 완료, CSV 파일 생성 중...")
                        
            # 최종 결과 확인 및 반환
            if survey_data:
                self.logger.info(f"Successfully processed {len(survey_data)} surveys")
                return survey_data
            else:
                self.logger.warning(f"No valid surveys were processed in {total_surveys} attempts")
                return []

    def process_single_visit(self, visit_images: List[Tuple[int, np.ndarray]], progress_callback=None) -> Dict:
        """한 번의 방문에 대한 6페이지 처리"""

        def validate_page_data(page_num: int, data: dict) -> dict:
            """페이지별 데이터 검증 및 보정"""
            try:
                if page_num == 0:  # VAS 점수 페이지
                    # VAS 점수는 0-100 사이여야 함
                    for key in ['lbp_vas', 'buttock_vas', 'le_vas_rt', 'le_vas_lt']:
                        if key in data and data[key] is not None:  # None 체크 추가
                            try:
                                value = float(data[key])
                                if value > 100:  # 100 초과시 10으로 나눔 (예: 600 -> 60)
                                    value = value / 10
                                data[key] = int(value)
                            except (ValueError, TypeError):
                                data[key] = None  # 변환 실패시 None으로 설정
                        else:
                            data[key] = None  # 키가 없거나 None인 경우 None으로 설정
                    
                    
                    # rc_id는 8자리 숫자여야 함
                    if 'rc_id' in data:
                        data['rc_id'] = str(data['rc_id']).zfill(8)

                    # redcap 관련 필드 검증
                    if 'redcap_event_name' in data:
                        valid_events = ["preoperative_evalu_arm_1", "opd_followup_arm_1"]
                        if data['redcap_event_name'] not in valid_events:
                            # 입력값에서 preop/opd 확인
                            event_name = data['redcap_event_name'].lower()
                            if 'preop' in event_name:
                                data['redcap_event_name'] = "preoperative_evalu_arm_1"
                            elif 'opd' in event_name:
                                data['redcap_event_name'] = "opd_followup_arm_1"

                    if 'redcap_repeat_instance' in data:
                        # 문자열이나 float으로 들어왔을 수 있으므로 정수로 변환
                        try:
                            data['redcap_repeat_instance'] = int(float(str(data['redcap_repeat_instance']).strip()))
                        except ValueError:
                            self.logger.error("Invalid redcap_repeat_instance value")
                            data['redcap_repeat_instance'] = None

                    return data
                
                elif page_num in [1, 2]:  # ODI 페이지
                    # ODI 점수는 0-5 사이여야 함
                    odi_fields = ['odi_pain', 'odi_personal', 'odi_lifting', 'odi_walking',
                                'odi_sitting', 'odi_standing', 'odi_sleeping', 'odi_social',
                                'odi_travelling', 'odi_sexlife']
                    for key in data:
                        if key in odi_fields:
                            data[key] = max(0, min(5, int(data[key]))) if data[key] is not None else None

                    # odi_sexlifeyn 설정
                    if 'odi_sexlife' in data and data['odi_sexlife'] is not None:
                        data['odi_sexlifeyn'] = 1
                    else:
                        data['odi_sexlifeyn'] = 0
                        data['odi_sexlife'] = None        
                
 
                if page_num == 3:  # EQ-5D-5L 페이지
                    # 기존 검증
                    eq5d_fields = ['eq5d_mobility', 'eq5d_selfcare', 'eq5d_activities',
                                'eq5d_pain', 'eq5d_anxiety']
                    for key in data:
                        if key in eq5d_fields:
                            if data[key] is not None:
                                data[key] = max(1, min(5, int(data[key])))
                    
                    # 모든 EQ-5D 필드가 있는지 확인
                    if all(key in data for key in eq5d_fields):
                        # 5자리 숫자 생성
                        eq5d_digits = str(data['eq5d_mobility']) + \
                                    str(data['eq5d_selfcare']) + \
                                    str(data['eq5d_activities']) + \
                                    str(data['eq5d_pain']) + \
                                    str(data['eq5d_anxiety'])
                        
                        try:
                            # eq5d_value_k.csv 파일 읽기
                            import pandas as pd
                            from config import EQ5D_CSV_PATH
                            value_table = pd.read_csv(EQ5D_CSV_PATH)
                            
                            # 5자리 숫자에 해당하는 value 찾기
                            value = value_table.loc[value_table['code'] == int(eq5d_digits), 'value'].iloc[0]
                            data['eq5d_value'] = round(float(value), 3)
                            
                        except Exception as e:
                            self.logger.error(f"Error calculating EQ-5D value: {str(e)}")
                            data['eq5d_value'] = None
                    
                    return data
                
                elif page_num in [4, 5]:  # painDETECT 페이지
                    # painDETECT 점수는 0-5 사이여야 함
                    pndtct_fields = ['pndtct_buring', 'pndtct_tingling', 'pndtct_touching',
                                    'pndtct_shock', 'pndtct_cold', 'pndtct_numbness', 'pndtct_pressure']
                    for key in data:
                        if key in pndtct_fields:
                            data[key] = max(0, min(5, int(data[key])))
                        # elif key == 'pndtct_pattern':
                        #     pattern_value = str(data[key]).strip()
                        #     # +1, 1, 1.0 등의 값을 모두 1로 변환
                        #     if any(val in pattern_value for val in ['+1', '1']) or float(pattern_value.replace('+','') or 0) == 1:
                        #         data[key] = 1
                        #     elif '-1' in pattern_value or float(pattern_value or 0) == -1:
                        #         data[key] = -1
                        #     else:
                        #         data[key] = 0
                        elif key == 'pndtct_pattern':
                            pattern_value = str(data[key]).strip()
                            try:
                                # 먼저 숫자로 변환 시도
                                numeric_value = float(pattern_value.replace('+', ''))
                                if numeric_value == -1 or '-1' in pattern_value:
                                    data[key] = -1
                                elif numeric_value == 1 or numeric_value == +1 or '+1' in pattern_value:
                                    data[key] = 1
                                else:
                                    data[key] = 0
                            except ValueError:
                                # 숫자 변환이 실패한 경우 문자열 기반으로 처리
                                if '-1' in pattern_value or 'minus 1' in pattern_value.lower():
                                    data[key] = -1
                                elif '+1' in pattern_value or 'plus 1' in pattern_value.lower() or '1' in pattern_value:
                                    data[key] = 1
                                else:
                                    data[key] = 0
                            self.logger.info(f"Processed pndtct_pattern: input='{pattern_value}', output={data[key]}")

                        elif key == 'pndtct_radiating':
                            data[key] = 2 if str(data[key]).lower() in ['예', 'yes', '2', 2] else 0

                return data
    
            except Exception as e:
                self.logger.error(f"Validation error for page {page_num}: {str(e)}")
                return data
       

        try:
            all_data = {}
            
            for page_num, image in visit_images:
                # 여기에 새로운 예외 처리 코드 추가
                if page_num not in page_instructions:
                    self.logger.error(f"Invalid page number: {page_num}")
                    continue

                self.logger.info(f"Processing page {page_num + 1} (internal index: {page_num})")
                
                # 진행률 업데이트 - 각 페이지 시작할 때
                if progress_callback:
                    progress_value = 10 + ((page_num + 1) * 10)  # API 호출마다 10%씩 증가 (10% ~ 70%)
                    progress_callback(progress_value, f"페이지 {page_num + 1}/6 처리 중...")
                
                try:
                    encoded_image = self.encode_image(image)
                except Exception as e:
                    self.logger.error(f"Error encoding image for page {page_num + 1}: {str(e)}")
                    continue
                
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": page_instructions[page_num]
                            },
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": encoded_image
                                }
                            }
                        ]
                    }
                ]

                response = self.client.messages.create(
                    model="claude-3-7-sonnet-latest",
                    max_tokens=2000,
                    messages=messages
                )

                try:
                    # Claude code
                    if isinstance(response.content, list):
                        content = response.content[0].text
                    else:
                        content = response.content


                    try:
                        page_data = json.loads(content)
                        # 데이터 검증 및 보정
                        page_data = validate_page_data(page_num, page_data)
                        self.logger.info(f"Validated data for page {page_num + 1}: {page_data}")
                        all_data.update(page_data)
                        
                        # 페이지 처리 완료 후 진행률 다시 업데이트
                        if progress_callback:
                            # API 호출 완료 후 진행률 업데이트 (각 페이지 완료 시)
                            progress_value = 10 + ((page_num + 1) * 10)  
                            progress_callback(progress_value, f"페이지 {page_num + 1}/6 처리 완료")
                    except json.JSONDecodeError:
                        # JSON 파싱 실패 시 응답 내용에서 중괄호 안의 내용만 추출
                        import re
                        json_match = re.search(r'\{.*\}', content, re.DOTALL)
                        if json_match:
                            try:
                                page_data = json.loads(json_match.group())
                                page_data = validate_page_data(page_num, page_data)
                                self.logger.info(f"Validated data for page {page_num + 1} (regex): {page_data}")
                                all_data.update(page_data)
                                
                                # 페이지 처리 완료 후 진행률 다시 업데이트
                                if progress_callback:
                                    progress_value = 10 + ((page_num + 1) * 10)
                                    progress_callback(progress_value, f"페이지 {page_num + 1}/6 처리 완료")
                            except json.JSONDecodeError as e:
                                self.logger.error(f"Failed to parse JSON even after regex on page {page_num + 1}")
                                self.logger.error(f"Extracted content: {json_match.group()}")
                                raise
                        else:
                            self.logger.error(f"No JSON-like content found in response for page {page_num + 1}")
                            self.logger.error(f"Full response: {content}")
                            
                except Exception as e:
                    self.logger.error(f"Error processing page {page_num + 1}: {str(e)}")
                    self.logger.error(f"Full response: {response.content}")
                    raise
            
            # Complete flags 추가
            all_data.update({
                'visit_day_complete': 1,
                'vas_complete': 1,
                'owestry_disability_index_complete': 1,
                'eq5d5l_complete': 1,
                'paindetect_complete': 1
            })
            
            self.logger.info(f"Final processed data: {all_data}")
            return all_data
            
        except Exception as e:
            self.logger.error(f"Error processing visit: {str(e)}")
            raise