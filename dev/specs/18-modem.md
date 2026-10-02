# Module Specification: 18. FaxModem

## 1. Overview
- **레거시 모듈**: `legacy/avantfax/includes/FaxModem.php`
- **신규 타깃 모듈**: `src/avantfax/services/modem.py`
- **역할**: HylaFAX 모뎀 장치(`Modems` 테이블: `devid`, `device`, `alias`, `contact`, `printer`, `faxcatid`) CRUD 관리 및 HylaFAX `faxstat` 출력을 분석한 실시간 모뎀 상태(유휴/전송중/수신중) 조회 서비스.
- **주요 의존성**:
  - `src/avantfax/models/entities.py` (`Modems`)
  - `src/avantfax/db/repository.py` (`MDBOData` / `Repository`)
  - `src/avantfax/db/engine.py` (`DatabaseEngine`)

---

## 2. Legacy API Analysis & Behavior

### 속성(Attributes)
- `devid`: 모뎀 ID (PK)
- `device`: 모뎀 디바이스명 (예: `ttyS0`)
- `alias`: 모뎀 별칭 (예: `Line 1`)
- `contact`: 담당자 이메일 주소
- `printer`: 기본 출력 프린터
- `faxcatid`: 연결 카테고리 ID
- `error`: 최근 에러 메시지
- `status`: 디바이스별 상태 캐시 딕셔너리
- `modems`: `Modems` 레포지토리

### 메서드(Methods)
1. `__init__(db: Optional[DatabaseEngine] = None, repo: Optional[MDBOData] = None, faxstat_cmd: str = "faxstat", lang: Optional[dict[str, str]] = None)`
2. `create(device: str, alias: str, contact: Optional[str] = None, printer: Optional[str] = None, faxcatid: Optional[int] = None) -> bool`
   - `alias` 또는 `device`가 비어있으면 실패 (`MODEM_NOT_CREATED`)
   - `device`가 이미 존재하는 경우 실패 (`MODEM_EXISTS`)
   - DB에 신규 저장 후 `devid` 갱신. 성공 시 `True`, 실패 시 `False`
3. `delete_device(devid_or_device: Union[int, str]) -> bool`
   - 모뎀 레코드 삭제
4. `get_modems() -> Optional[list[str]]`
   - 등록된 모든 모뎀의 디바이스명 목록 반환 (`SELECT device FROM Modems ORDER BY alias`)
   - 등록된 모뎀이 없으면 `None` 및 `NO_MODEMS_CONFIGURED`
5. `list_modems_step() -> Optional[tuple[int, str, str]]`
   - `SELECT * FROM Modems ORDER BY device` 순회
   - `(devid, alias, device)` 반환
6. `load_device(device: str) -> bool`
   - 디바이스명으로 레코드 로드
7. `loadbyid(devid: int) -> bool`
   - ID로 레코드 로드
8. `get_status(raw_output: Optional[str] = None) -> dict[str, Any]`
   - `faxstat` 출력 문자열(또는 실행 결과)을 파싱하여 현재 모뎀 상태 반환
   - `{"class": "modem-free" | "modem-send" | "modem-recv" | "modem-wait", "status": str}`
9. 게터: `get_alias()`, `get_contact()`, `get_printer()`, `get_faxcatid()`, `get_devid()`, `get_device()`, `get_error()`
10. 세터: `set_alias(alias)`, `set_contact(contact)`, `set_printer(printer)`, `set_faxcatid(faxcatid)`
    - 미로드 시 에러 ("No modem loaded")
    - 로드 시 DB 업데이트

---

## 3. Error Messages / Localization Constants
- `MODEM_NOT_CREATED`: "Modem could not be created"
- `MODEM_EXISTS`: "Modem already exists"
- `NO_MODEMS_CONFIGURED`: "No modems configured"
- `MODEM_DOESNT_EXIST`: "Modem '%s' doesn't exist"
- `FAXFREE`: "Running and idle"
- `FAXSEND`: "Sending fax"
- `FAXRECV`: "Receiving facsimile"
- `FAXRECVFROM`: "Receiving from"
- `PLSWAIT`: "Please wait"

---

## 4. Modern Python Design (Idiomatic)
- `FaxModemService` 및 `FaxModem` 클래스명 별칭 제공
- `faxstat` 출력을 안전하게 파싱하는 순수 파서 함수 `parse_faxstat_output` 분리
- CLI/IPC 브리지: `bridge_cli.py`의 `modem` 액션을 통해 레거시 PHP `FaxModemBridge.php`와 통신 가능
