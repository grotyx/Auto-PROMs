import logging
from typing import Optional

from . import DATA_DIR


class SurveyValidator:
    """Spine survey page data validator.

    Validates and corrects extracted data for each page type:
      Page 0  - VAS scores, rc_id, redcap fields
      Pages 1-2 - ODI scores
      Page 3  - EQ-5D-5L scores with value lookup
      Pages 4-5 - painDETECT scores
    """

    _eq5d_table = None  # class-level cache

    @classmethod
    def _load_eq5d_table(cls):
        """Load eq5d_value_k.csv once and cache as a class variable."""
        if cls._eq5d_table is not None:
            return cls._eq5d_table

        try:
            import pandas as pd
            csv_path = DATA_DIR / 'eq5d_value_k.csv'
            if csv_path.exists():
                cls._eq5d_table = pd.read_csv(csv_path)
            else:
                logging.getLogger(__name__).warning("eq5d_value_k.csv file not found")
                cls._eq5d_table = None
        except Exception as e:
            logging.getLogger(__name__).error(f"Error loading EQ-5D table: {e}")
            cls._eq5d_table = None

        return cls._eq5d_table

    @staticmethod
    def validate_page_data(page_num: int, data: dict, logger: Optional[logging.Logger] = None) -> dict:
        """Validate and correct page data for a spine survey page.

        This is a direct extraction of the inner ``validate_page_data``
        function from the original processors. The logic is preserved
        exactly as-is.
        """
        if logger is None:
            logger = logging.getLogger(__name__)

        try:
            if page_num == 0:  # VAS page
                for key in ['lbp_vas', 'buttock_vas', 'le_vas_rt', 'le_vas_lt']:
                    if key in data and data[key] is not None:
                        try:
                            value = float(data[key])
                            if value > 100:
                                value = value / 10
                            data[key] = int(value)
                        except (ValueError, TypeError):
                            data[key] = None

                if 'rc_id' in data:
                    if data['rc_id'] is None or str(data['rc_id']).strip().lower() in ('', 'none'):
                        data['rc_id'] = None
                    else:
                        data['rc_id'] = str(data['rc_id']).zfill(8)

                if 'redcap_event_name' in data:
                    valid_events = ["preoperative_evalu_arm_1", "opd_followup_arm_1"]
                    if data['redcap_event_name'] not in valid_events:
                        event_name = str(data['redcap_event_name']).lower()
                        if 'preop' in event_name:
                            data['redcap_event_name'] = "preoperative_evalu_arm_1"
                        elif 'opd' in event_name:
                            data['redcap_event_name'] = "opd_followup_arm_1"

                if 'redcap_repeat_instance' in data:
                    try:
                        data['redcap_repeat_instance'] = int(
                            float(str(data['redcap_repeat_instance']).strip())
                        )
                    except ValueError:
                        logger.error("Invalid redcap_repeat_instance value")
                        data['redcap_repeat_instance'] = None

            elif page_num in [1, 2]:  # ODI pages
                odi_fields = [
                    'odi_pain', 'odi_personal', 'odi_lifting', 'odi_walking',
                    'odi_sitting', 'odi_standing', 'odi_sleeping', 'odi_social',
                    'odi_travelling', 'odi_sexlife',
                ]
                for key in data:
                    if key in odi_fields and data[key] is not None:
                        data[key] = max(0, min(5, int(data[key])))

                if 'odi_sexlife' in data and data['odi_sexlife'] is not None:
                    data['odi_sexlifeyn'] = 1
                else:
                    data['odi_sexlifeyn'] = 0
                    data['odi_sexlife'] = None

            elif page_num == 3:  # EQ-5D-5L page
                eq5d_fields = [
                    'eq5d_mobility', 'eq5d_selfcare', 'eq5d_activities',
                    'eq5d_pain', 'eq5d_anxiety',
                ]
                for key in data:
                    if key in eq5d_fields and data[key] is not None:
                        data[key] = max(1, min(5, int(data[key])))

                if all(key in data and data[key] is not None for key in eq5d_fields):
                    eq5d_digits = (
                        str(data['eq5d_mobility'])
                        + str(data['eq5d_selfcare'])
                        + str(data['eq5d_activities'])
                        + str(data['eq5d_pain'])
                        + str(data['eq5d_anxiety'])
                    )
                    try:
                        value_table = SurveyValidator._load_eq5d_table()
                        if value_table is not None:
                            value = value_table.loc[
                                value_table['code'] == int(eq5d_digits), 'value'
                            ].iloc[0]
                            data['eq5d_value'] = round(float(value), 3)
                        else:
                            data['eq5d_value'] = None
                    except Exception as e:
                        logger.error(f"Error calculating EQ-5D value: {e}")
                        data['eq5d_value'] = None

            elif page_num in [4, 5]:  # painDETECT pages
                pndtct_fields = [
                    'pndtct_buring', 'pndtct_tingling', 'pndtct_touching',
                    'pndtct_shock', 'pndtct_cold', 'pndtct_numbness', 'pndtct_pressure',
                ]
                for key in data:
                    if key in pndtct_fields and data[key] is not None:
                        data[key] = max(0, min(5, int(data[key])))
                    elif key == 'pndtct_pattern':
                        pattern_value = str(data[key]).strip()
                        try:
                            numeric_value = float(pattern_value.replace('+', ''))
                            if numeric_value == -1 or '-1' in pattern_value:
                                data[key] = -1
                            elif numeric_value == 1 or numeric_value == +1 or '+1' in pattern_value:
                                data[key] = 1
                            else:
                                data[key] = 0
                        except ValueError:
                            if '-1' in pattern_value or 'minus 1' in pattern_value.lower():
                                data[key] = -1
                            elif '+1' in pattern_value or 'plus 1' in pattern_value.lower() or '1' in pattern_value:
                                data[key] = 1
                            else:
                                data[key] = 0
                        logger.info(f"Processed pndtct_pattern: input='{pattern_value}', output={data[key]}")

                    elif key == 'pndtct_radiating':
                        data[key] = 2 if str(data[key]).lower() in ['예', 'yes', '2', 2] else 0

            return data

        except Exception as e:
            logger.error(f"Validation error for page {page_num}: {e}")
            return data
