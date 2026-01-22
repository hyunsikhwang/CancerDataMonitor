#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cancer Data Monitor
주기적으로 KOSIS 사이트에서 암 데이터 모니터링
통계자료의 수록기간이 변경되었을 때 ntfy.sh/stock-info로 알림 전송
"""

import requests
import urllib3
import logging
import os
import json

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cancer_data_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# SSL 경고 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def fetch_cancer_data():
    """
    KOSIS 사이트에서 암 데이터 수록기간 가져오기 (JSON API 사용)
    """
    url = "https://kosis.kr/statisticsList/selectMetaTreeData.do?vwcd=MT_OTITLE&rootId=117_11744"
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://kosis.kr/"
        }

        response = requests.get(url, headers=headers, timeout=10, verify=False)
        response.raise_for_status()
        
        data = response.json()
        result_tree_list = data.get('resultTreeList', [])
        
        if not result_tree_list:
            logger.warning("JSON 결과에서 resultTreeList를 찾을 수 없거나 비어 있습니다.")
            return None

        # 모든 항목의 name과 prdInfo를 추출하여 딕셔너리로 반환
        periods = {}
        for item in result_tree_list:
            name = item.get('name')
            prd_info = item.get('prdInfo')
            if name and prd_info:
                periods[name] = prd_info

        if periods:
            logger.info(f"{len(periods)}개의 수록기간 정보를 가져왔습니다.")
            return periods
        else:
            logger.warning("수록기간 정보를 찾을 수 없습니다.")
            return None
        
    except requests.exceptions.RequestException as e:
        logger.error(f"데이터 가져오기 실패: {e}")
        return None
    except Exception as e:
        logger.error(f"예상치 못한 오류: {e}")
        return None


def check_period_change(current_periods):
    """
    이전 수록기간과 비교하여 변경 사항 감지
    """
    config_file = "period_config.json"
    
    # 이전 수록기간 불러오기
    previous_periods = {}
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 이전 버전 호환성 유지 (문자열인 경우 처리)
                last_period = config.get('last_period')
                if isinstance(last_period, dict):
                    previous_periods = last_period
                else:
                    # 이전 포맷인 경우 비어있는 것으로 간주하여 갱신 유도
                    previous_periods = {}
        except Exception as e:
            logger.warning(f"설정 파일 읽기 오류: {e}")
            previous_periods = {}

    # 변경된 항목 찾기
    changes = []
    for name, prd_info in current_periods.items():
        prev_info = previous_periods.get(name)
        if prd_info != prev_info:
            changes.append(f"[{name}] {prev_info} -> {prd_info}")
    
    # 변경 사항 감지
    if changes:
        logger.info(f"수록기간 변경 감지: {len(changes)}개 항목")
        for change in changes:
            logger.info(change)
        
        # 새로운 수록기간 저장
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump({'last_period': current_periods}, f, ensure_ascii=False, indent=4)
        
        return True, "\n".join(changes)
    
    return False, None


def send_ntfy_notification(message):
    """
    ntfy.sh로 알림 전송
    """
    ntfy_topic = "stock-info"
    ntfy_url = f"https://ntfy.sh/{ntfy_topic}"
    
    try:
        # ntfy.sh 헤더에는 아스키 문자만 권장되므로 제목은 영문으로 설정
        response = requests.post(
            ntfy_url,
            data=message.encode('utf-8'),
            headers={
                'Title': 'Cancer Data Period Updated',
                'Tags': 'warning,chart_with_upwards_trend',
                'Priority': 'high'
            },
            timeout=10,
            verify=False
        )
        response.raise_for_status()
        logger.info("ntfy.sh로 알림 전송 성공")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"ntfy.sh 알림 전송 실패: {e}")
        return False


def main():
    """
    메인 함수
    """
    logger.info("암 데이터 모니터링 시작")
    current_periods = fetch_cancer_data()
    
    if current_periods:
        # 수록기간 변경 감지
        period_changed, changes_text = check_period_change(current_periods)

        if period_changed:
            message = f"암 데이터 수록기간이 변경되었습니다:\n{changes_text}"
            send_ntfy_notification(message)
        else:
            logger.info("수록기간 변경 없음")
    else:
        logger.error("수록기간 정보를 가져오는 데 실패했습니다.")
    
    logger.info("암 데이터 모니터링 완료")


if __name__ == "__main__":
    main()