#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cancer Data Monitor
주기적으로 KOSIS 사이트에서 암 데이터 모니터링
통계자료의 수록기간이 변경되었을 때 ntfy.sh/stock-info로 알림 전송
"""

import requests
import urllib3
import re
import logging
import os
import json
from lxml import html

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
    KOSIS 사이트에서 암 데이터 수록기간 가져오기
    """
    url = "https://kosis.kr/common/meta_onedepth.jsp?vwcd=MT_OTITLE&listid=117_11744"
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://kosis.kr/"
        }

        response = requests.get(url, headers=headers, timeout=10, verify=False)
        response.raise_for_status()
        
        # lxml을 사용하여 XPath로 데이터 추출
        tree = html.fromstring(response.text)
        xpath = '//*[@id="117_11744.2"]/ul/li[7]/a'
        elements = tree.xpath(xpath)
        
        current_period = None
        if elements:
            current_period = elements[0].text_content().strip()
            logger.info(f"XPath를 통해 수록기간 발견: {current_period}")
        else:
            logger.warning(f"XPath '{xpath}'로 수록기간을 찾을 수 없습니다.")
            # 만약 XPath로 못찾는다면, 텍스트에서 직접 찾기 시도 (보험용)
            period_match = re.search(r'(\d{4}\s*~\s*\d{4})', response.text)
            if period_match:
                current_period = period_match.group(1)
                logger.info(f"정규표현식을 통해 수록기간 발견: {current_period}")

        return current_period
        
    except requests.exceptions.RequestException as e:
        logger.error(f"데이터 가져오기 실패: {e}")
        return None
    except Exception as e:
        logger.error(f"예상치 못한 오류: {e}")
        return None


def check_period_change(current_period):
    """
    이전 수록기간과 비교하여 변경 사항 감지
    """
    config_file = "period_config.json"
    
    # 이전 수록기간 불러오기
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        previous_period = config.get('last_period')
    else:
        previous_period = None
    
    # 변경 사항 감지
    if current_period and current_period != previous_period:
        logger.info(f"수록기간 변경 감지: {previous_period} -> {current_period}")
        
        # 새로운 수록기간 저장
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump({'last_period': current_period}, f, ensure_ascii=False, indent=4)
        
        return True, current_period
    
    return False, current_period


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
    current_period = fetch_cancer_data()
    
    if current_period:
        # 수록기간 변경 감지
        period_changed, _ = check_period_change(current_period)

        if period_changed:
            message = f"암 데이터 수록기간이 변경되었습니다: {current_period}"
            send_ntfy_notification(message)
        else:
            logger.info("수록기간 변경 없음")
    else:
        logger.error("수록기간 정보를 가져오는 데 실패했습니다.")
    
    logger.info("암 데이터 모니터링 완료")


if __name__ == "__main__":
    main()