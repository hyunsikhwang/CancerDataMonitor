#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cancer Data Monitor
주기적으로 KOSIS 사이트에서 암 데이터 모니터링
통계자료의 수록기간이 변경되었을 때 ntfy.sh/stock-info로 알림 전송
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import logging
from datetime import datetime
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


def fetch_cancer_data():
    """
    KOSIS 사이트에서 암 데이터 가져오기
    """
    url = "https://kosis.kr/common/meta_onedepth.jsp?vwcd=MT_OTITLE&listid=117_11744"
    
    try:
        # 웹 페이지 요청
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # BeautifulSoup을 사용하여 HTML 파싱
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 수록기간 추출 (사이트 구조에 따라 조정 필요)
        # 예시: 수록기간이 포함된 요소 찾기
        period_element = soup.find('div', class_='period-info')
        if not period_element:
            period_element = soup.find('span', class_='data-period')
        
        if period_element:
            current_period = period_element.get_text(strip=True)
            logger.info(f"현재 수록기간: {current_period}")
        else:
            current_period = None
            logger.warning("수록기간을 찾을 수 없습니다.")
        
        # 데이터 추출 로직 (사이트 구조에 따라 조정 필요)
        # 예시: 테이블 데이터 추출
        tables = soup.find_all('table')
        
        if not tables:
            logger.warning("테이블을 찾을 수 없습니다.")
            return None, current_period
        
        # 첫 번째 테이블을 데이터프레임으로 변환
        df = pd.read_html(str(tables[0]))[0]
        
        # 데이터 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = "data"
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"cancer_data_{timestamp}.csv")
        
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        logger.info(f"데이터가 성공적으로 저장되었습니다: {output_file}")
        
        return df, current_period
        
    except requests.exceptions.RequestException as e:
        logger.error(f"데이터 가져오기 실패: {e}")
        return None, None
    except Exception as e:
        logger.error(f"예상치 못한 오류: {e}")
        return None, None


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
        response = requests.post(
            ntfy_url,
            data=message.encode('utf-8'),
            headers={
                'Title': '암 데이터 수록기간 변경 알림',
                'Tags': 'warning,chart_with_upwards_trend',
                'Priority': 'high'
            },
            timeout=10
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
    data, current_period = fetch_cancer_data()
    
    if data is not None:
        logger.info("데이터 가져오기 성공")
        logger.info(f"데이터 크기: {data.shape}")
        
        # 수록기간 변경 감지
        if current_period:
            period_changed, _ = check_period_change(current_period)
            
            if period_changed:
                message = f"암 데이터 수록기간이 변경되었습니다: {current_period}"
                send_ntfy_notification(message)
    else:
        logger.error("데이터 가져오기 실패")
    
    logger.info("암 데이터 모니터링 완료")


if __name__ == "__main__":
    main()