import pandas as pd
from typing import List, Dict
import logging

class CSVGenerator:
    def __init__(self, output_path: str):
        self.output_path = output_path
        self.logger = logging.getLogger(__name__)
        
        # 모든 필요한 열 정의 (spine survey)
        self.columns = [
            'rc_id', 'redcap_event_name', 'redcap_repeat_instance', 'visit_day', 'visit_day_complete',
            'lbp_vas', 'buttock_vas', 'le_vas_rt', 'le_vas_lt', 'vas_complete',
            'odi_pain', 'odi_personal', 'odi_lifting', 'odi_walking',
            'odi_sitting', 'odi_standing', 'odi_sleeping', 'odi_social',
            'odi_travelling', 'odi_sexlifeyn', 'odi_sexlife',
            'owestry_disability_index_complete',
            'eq5d_mobility', 'eq5d_selfcare', 'eq5d_activities',
            'eq5d_pain', 'eq5d_anxiety', 'eq5d_value', 'eq5d5l_complete',
            'pndtct_buring', 'pndtct_tingling', 'pndtct_touching',
            'pndtct_shock', 'pndtct_cold', 'pndtct_numbness',
            'pndtct_pressure', 'pndtct_pattern', 'pndtct_radiating',
            'paindetect_complete'
        ]

    def generate_csv(self, survey_data: List[Dict]):
        """설문 데이터를 CSV 파일로 변환"""
        try:
            # None 체크
            if survey_data is None:
                self.logger.error("Survey data is None")
                return None

            # 데이터가 리스트가 아니면 리스트로 변환
            if not isinstance(survey_data, list):
                survey_data = [survey_data]

            # 빈 리스트 체크
            if len(survey_data) == 0:
                self.logger.warning("No survey data to process")
                return None

            self.logger.info(f"Processing {len(survey_data)} records")
            
            # 빈 데이터 필터링하고 데이터프레임 생성
            valid_data = [data for data in survey_data if data and isinstance(data, dict) and 'rc_id' in data]
            df = pd.DataFrame(valid_data)
            
            # 누락된 열 추가
            for col in self.columns:
                if col not in df.columns:
                    df[col] = None

            # 열 순서 조정
            df = df[self.columns]
            
            # 데이터 타입 변환
            # rc_id: 숫자만 Int64로, '0000None' 같이 변환 불가한 값은 NA로 (다른 컬럼 데이터는 보존)
            df['rc_id'] = pd.to_numeric(df['rc_id'], errors='coerce').astype('Int64')
            df['visit_day'] = pd.to_datetime(df['visit_day'], format='mixed', errors='coerce').dt.strftime('%Y-%m-%d')

            # CSV 저장
            df.to_csv(self.output_path, index=False)
            
            # 결과 출력
            print("\nProcessed data summary:")
            print(f"Total records processed: {len(df)}")
            print("\nMissing values summary:")
            print(df.isnull().sum())
            
            self.logger.info(f"CSV file successfully generated at {self.output_path}")
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error generating CSV: {str(e)}")
            raise