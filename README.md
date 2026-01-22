# Cancer Data Monitor

암 데이터 모니터링 시스템

## 개요

이 프로젝트는 KOSIS(통계청 국가통계포털) 사이트에서 암 데이터의 수록기간을 주기적으로 모니터링하고, 변경 사항이 감지되면 알림을 전송하는 시스템입니다.

## 기능

- KOSIS 사이트에서 암 데이터 수록기간 정보 가져오기
- 이전 수록기간과 비교하여 변경 사항 감지
- 변경 사항 발생 시 ntfy.sh 서비스를 통해 알림 전송
- 모니터링 과정 로깅

## 설치 방법

### 전제 조건

- Python 3.x
- pip 패키지 관리자

### 의존성 설치

```bash
pip install requests urllib3
```

## 사용 방법

### 스크립트 실행

```bash
python CancerDataMonitor.py
```

### 설정

프로그램은 `period_config.json` 파일에 이전 수록기간 정보를 저장합니다. 이 파일은 자동으로 생성되며, 수동으로 수정할 필요는 없습니다.

### 로깅

모니터링 과정은 `cancer_data_monitor.log` 파일에 기록됩니다. 로그 레벨은 INFO로 설정되어 있으며, 콘솔에도 출력됩니다.

## 알림 설정

알림은 ntfy.sh 서비스를 통해 전송됩니다. 기본적으로 `stock-info` 토픽으로 알림이 전송됩니다. 알림 설정을 변경하려면 스크립트의 `send_ntfy_notification` 함수를 수정하세요.

## 파일 구조

```
CancerDataMonitor/
├── CancerDataMonitor.py  # 메인 스크립트
├── period_config.json    # 수록기간 정보 저장 (자동 생성)
└── cancer_data_monitor.log # 로그 파일 (자동 생성)
```

## 주의 사항

- KOSIS 사이트의 API 구조가 변경될 경우 스크립트가 정상적으로 동작하지 않을 수 있습니다.
- 알림 전송을 위해서는 인터넷 연결이 필요합니다.
- SSL 인증서 검증을 비활성화하고 있으므로, 보안상 주의가 필요합니다.

## 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다.
