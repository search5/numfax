# Module Specification: 15. BarcodeRouting

## 1. Overview
- **레거시 모듈**: `legacy/avantfax/includes/BarcodeRouting.php`
- **신규 타깃 모듈**: `src/avantfax/services/barcode.py`
- **역할**: 수신된 팩스에서 감지된 바코드(Barcode)를 기준으로 지정된 이메일(`contact`), 프린터(`printer`), 카테고리(`faxcatid`), 별칭(`alias`)으로 자동 분류/전달하는 라우팅 규칙 관리 서비스.
- **주요 의존성**:
  - `src/avantfax/models/entities.py` (`BarcodeRoute`)
  - `src/avantfax/db/repository.py` (`MDBOData` / `Repository`)
  - `src/avantfax/common/validators.py` (`is_valid_email`)
  - `src/avantfax/db/engine.py` (`DatabaseEngine`)

---

## 2. Legacy API Analysis & Behavior

### 속성(Attributes)
- `barcode_id`: 규칙 ID (PK)
- `barcode`: 매칭할 바코드 문자열
- `alias`: 규칙 별칭/설명
- `contact`: 라우팅 대상 이메일 주소
- `printer`: 인쇄할 프린터명
- `faxcatid`: 지정할 카테고리 ID
- `error`: 최근 오류 메시지
- `barcoderoute`: `BarcodeRoute` 레포지토리

### 메서드(Methods)
1. `__init__(db: Optional[DatabaseEngine] = None, repo: Optional[MDBOData] = None, lang: Optional[dict[str, str]] = None)`
2. `create(barcode: str, alias: str, contact: Optional[str] = None, printer: Optional[str] = None, faxcatid: Optional[int] = None) -> bool`
   - `contact`가 제공되었을 때 올바르지 않은 이메일 형식인 경우 실패 (`REGWARN_MAIL`)
   - `alias` 또는 `barcode`가 비어있거나, `barcode == "<NONE>"`인 경우 실패 (`BARCODEROUTE_NOT_CREATED`)
   - 이미 동일한 `barcode`가 존재하는 경우 실패 (`BARCODEROUTE_EXISTS`)
   - DB에 신규 저장 후 `barcode_id` 속성 업데이트. 성공 시 `True`, 실패 시 `False`
3. `delete_route(barcode_id: int) -> bool`
   - 주어진 `barcode_id`를 가진 라우팅 규칙 삭제
4. `get_routes() -> Optional[list[int]]`
   - 등록된 모든 라우팅 규칙의 ID 목록 반환 (레거시 동작상 `[0, id1, id2, ...]` 반환)
   - 등록된 규칙이 없으면 `None` 반환 및 에러 설정 (`BARCODEROUTE_NO_ROUTES`)
5. `list_routes_step() -> Optional[tuple[int, str, str]]`
   - `SELECT * FROM BarcodeRoute ORDER BY alias` 순회 (legacy `list_routes(&$barcode_id, &$alias, &$barcode)`)
   - 순차적으로 `(barcode_id, alias, barcode)` 반환
6. `load_route(barcode: str) -> bool`
   - 바코드 문자열로 규칙을 찾아 속성 로드
   - 없으면 `False` 및 에러 (`BARCODEROUTE_DOESNT_EXIST`)
7. `loadbyid(barcode_id: int) -> bool`
   - ID로 규칙을 찾아 속성 로드
8. 게터 메서드: `get_alias()`, `get_contact()`, `get_printer()`, `get_faxcatid()`, `get_barcode_id()`, `get_barcode()`, `get_error()`
9. 세터 메서드: `set_alias(alias)`, `set_barcode(barcode)`, `set_contact(contact)`, `set_printer(printer)`, `set_faxcatid(faxcatid)`
   - 엔트리가 로드되지 않은 상태에서 호출 시 `False` 및 에러 ("No entry loaded")
   - 로드된 상태에서 필드 수정 및 DB 업데이트

---

## 3. Error Messages / Localization Constants
- `REGWARN_MAIL`: "Please enter a valid e-mail address."
- `BARCODEROUTE_NOT_CREATED`: "Route could not be created"
- `BARCODEROUTE_EXISTS`: "Barcode route already exists"
- `BARCODEROUTE_NO_ROUTES`: "No barcode routes configured"
- `BARCODEROUTE_DOESNT_EXIST`: "Barcode route '%s' doesn't exist"

---

## 4. Modern Python Design (Idiomatic)
- `BarcodeRoutingService` 및 `BarcodeRouting` 클래스명 별칭 제공
- Pydantic/dataclass 스타일의 규칙 정보 딕셔너리 및 객체 반환 헬퍼 (`list_all()`)
- CLI/IPC 브리지: `bridge_cli.py`의 `barcode` 액션을 통해 레거시 PHP `BarcodeRoutingBridge.php`와 통신 가능
