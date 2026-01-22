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
import urllib3
import re
from urllib.parse import quote
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

# SSL 경고 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def fetch_cancer_data():
    """
    KOSIS 사이트에서 암 데이터 가져오기
    """
    url = "https://kosis.kr/common/meta_onedepth.jsp?vwcd=MT_OTITLE&listid=117_11744"
    
    try:
        session = requests.Session()
        session.verify = False
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://kosis.kr/"
        })

        # 1. AJAX를 통한 수록기간 추출 시도
        tree_url = "https://kosis.kr/statisticsList/selectTreeData.do"
        params = {
            "vwcd": "MT_OTITLE",
            "parentId": "117_11744",
            "type": "undefined"
        }

        current_period = None
        try:
            # orgId를 명시적으로 추가하여 시도
            params["orgId"] = "117"
            res = session.post(tree_url, data=params, timeout=10)
            if res.status_code == 200:
                data = res.json()
                tree_list = data.get('resultTreeList', [])
                for item in tree_list:
                    prd_info = item.get('prdInfo', '')
                    if prd_info and prd_info.strip() and prd_info.strip() != "~":
                        current_period = prd_info.strip()
                        logger.info(f"AJAX를 통해 수록기간 발견: {current_period}")
                        break
        except Exception as e:
            logger.warning(f"AJAX 수록기간 추출 실패: {e}")

        # 2. 웹 페이지 직접 요청 (스크래핑용)
        response = session.get(url, timeout=10)
        response.raise_for_status()
        
        # BeautifulSoup을 사용하여 HTML 파싱
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 수록기간이 여전히 없다면 HTML에서 검색
        if not current_period:
            period_element = soup.find('div', class_='period-info')
            if not period_element:
                period_element = soup.find('span', class_='data-period')

            if period_element:
                current_period = period_element.get_text(strip=True)
                logger.info(f"HTML을 통해 수록기간 발견: {current_period}")
            else:
                # 더 넓은 범위의 텍스트 검색 (정규표현식 활용 가능)
                period_match = re.search(r'\d{4}\s*~\s*\d{4}', response.text)
                if period_match:
                    current_period = period_match.group()
                    logger.info(f"정규표현식을 통해 수록기간 발견: {current_period}")

        # 3. 추가 시도: selectStatisticsInfo.do 호출 (목록 정보)
        if not current_period:
            try:
                info_url = "https://kosis.kr/statisticsList/selectStatisticsInfo.do"
                info_params = {
                    "division": "list",
                    "vwCd": "MT_OTITLE",
                    "id": "117_11744",
                    "lvl": "2"
                }
                res = session.post(info_url, data=info_params, timeout=10)
                if res.status_code == 200:
                    info_data = res.json()
                    desc = info_data.get('resultListDesc', '')
                    # desc HTML 내에서 수록기간 혹은 유사한 텍스트 찾기
                    if desc:
                        info_soup = BeautifulSoup(desc, 'html.parser')
                        # 테이블 내의 텍스트 확인
                        for th in info_soup.find_all('th'):
                            if '기간' in th.get_text() or '시점' in th.get_text():
                                td = th.find_next_sibling('td')
                                if td:
                                    current_period = td.get_text(strip=True)
                                    logger.info(f"목록 정보를 통해 수록기간 발견: {current_period}")
                                    break
            except Exception as e:
                logger.warning(f"목록 정보 추출 실패: {e}")

        if current_period:
            logger.info(f"현재 수록기간: {current_period}")
        else:
            # 최종 수단: 이전 수록기간이 있으면 그것을 유지하거나, 알 수 없음으로 표시
            logger.warning("수록기간을 찾을 수 없습니다. 사이트 구조가 변경되었을 수 있습니다.")
        
        # 데이터 추출 로직 (사이트 구조에 따라 조정 필요)
        tables = soup.find_all('table')
        
        if not tables:
            logger.warning("HTML 내에서 테이블을 찾을 수 없습니다. (동적 로딩 가능성)")
            # 테이블이 없더라도 수록기간만 있으면 모니터링은 가능하므로 빈 데이터프레임 반환
            return pd.DataFrame(), current_period
        
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