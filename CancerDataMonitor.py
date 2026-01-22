#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cancer Data Monitor
주기적으로 KOSIS 사이트에서 암 데이터 모니터링
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import logging
from datetime import datetime
import os

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
        
        # 데이터 추출 로직 (사이트 구조에 따라 조정 필요)
        # 예시: 테이블 데이터 추출
        tables = soup.find_all('table')
        
        if not tables:
            logger.warning("테이블을 찾을 수 없습니다.")
            return None
        
        # 첫 번째 테이블을 데이터프레임으로 변환
        df = pd.read_html(str(tables[0]))[0]
        
        # 데이터 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = "data"
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"cancer_data_{timestamp}.csv")
        
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        logger.info(f"데이터가 성공적으로 저장되었습니다: {output_file}")
        
        return df
        
    except requests.exceptions.RequestException as e:
        logger.error(f"데이터 가져오기 실패: {e}")
        return None
    except Exception as e:
        logger.error(f"예상치 못한 오류: {e}")
        return None


def main():
    """
    메인 함수
    """
    logger.info("암 데이터 모니터링 시작")
    data = fetch_cancer_data()
    
    if data is not None:
        logger.info("데이터 가져오기 성공")
        logger.info(f"데이터 크기: {data.shape}")
    else:
        logger.error("데이터 가져오기 실패")
    
    logger.info("암 데이터 모니터링 완료")


if __name__ == "__main__":
    main()