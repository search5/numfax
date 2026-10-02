# Spec 42: Network Printer Direct Management & Print-to-Fax Inbound Pipeline

## 1. 개요 및 목적
- **목적**: 
  1. 수신 팩스를 실물 네트워크 프린터(RAW 9100, LPD, IPP)로 즉시 자동 출력하는 직접 연동 엔진 제공.
  2. ERP/PC에서 NamiFAX 가상 프린터로 인쇄 시 본문 내 `[[FAX: 번호]]` 태그를 자동 인식하여 즉시 팩스로 발송하는 Print-to-Fax 인바운드 파이프라인 구축.
- **연동 대상**:
  - `NetworkPrinterService` (`src/namifax/services/printer.py`)
  - `print-in` CLI 파이프라인 (`src/namifax/cli/print_in.py`)
  - `NetworkPrinters` DB 테이블 (`src/namifax/db/schema.py`)

---

## 2. 데이터 모델 명세 (`NetworkPrinters`)

| 필드명 | 타입 | 기본값 | 설명 |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PK Auto-Inc | 고유 식별자 |
| `name` | TEXT NOT NULL | - | 프린터 표시 이름 |
| `protocol` | TEXT | 'RAW' | 프로토콜: `RAW` (9100), `LPD` (515), `IPP` (631) |
| `host` | TEXT NOT NULL | - | 프린터 IP 또는 호스트명 |
| `port` | INTEGER | 9100 | 포트 번호 |
| `queue_name`| TEXT | NULL | LPD 큐 이름 또는 IPP 프린터 경로 |
| `description`| TEXT | NULL | 설명 |

---

## 3. 핵심 비즈니스 로직

### 3.1 아웃바운드 인쇄 (`NetworkPrinterService`)
- RAW 소켓(포트 9100) 직접 연결 및 바이너리 전송 (OS CUPS 의존성 없이 초고속 다이렉트 출력).
- LPD / IPP 프로토콜 전송 어댑터 지원.
- 테스트 페이지 인쇄 진단 (`test_print`).

### 3.2 인바운드 Print-to-Fax 파이프라인 (`parse_fax_tags` & `process_print_job`)
- 정규식 `\[\[FAX:\s*([\d\-\+\(\)\s]+)\]\]` 패턴 파싱.
- 태그가 발견되면 해당 번호로 `FaxQueue`를 통해 자동 발송 큐 등록.
- 태그가 없으면 "임시보관함(Draft)" 상태로 등록.

---

## 4. 검증 기준
1. 단위 테스트:
   - `tests/unit/test_network_printer.py`:
     - 프린터 CRUD 동작 및 유효성 검사.
     - Mock Socket을 통한 RAW 9100 인쇄 데이터 전송 및 테스트 페이지 검증.
     - `parse_fax_tags` 텍스트 태그 추출 정규식 검증.
2. 무회귀 검증:
   - 기존 319개 테스트 및 88개 골든 마스터 E2E 100% 통과.
