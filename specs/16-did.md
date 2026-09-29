# Module Specification: 16. DIDRouting

## 1. Overview
- **레거시 모듈**: `legacy/avantfax/includes/DIDRouting.php`
- **신규 타깃 모듈**: `src/avantfax/services/did.py`
- **역할**: 수신된 팩스의 착신 번호(DID / Direct Inward Dialing)를 기준으로 담당자 이메일(`contact`), 프린터(`printer`), 카테고리(`faxcatid`), 별칭(`alias`)으로 자동 분류/전달하는 라우팅 규칙 관리 서비스.
- **주요 의존성**:
  - `src/avantfax/models/entities.py` (`DIDRoute`)
  - `src/avantfax/db/repository.py` (`MDBOData` / `Repository`)
  - `src/avantfax/common/validators.py` (`is_valid_email`)
  - `src/avantfax/db/engine.py` (`DatabaseEngine`)

---

## 2. Legacy API Analysis & Behavior

### 속성(Attributes)
- `didr_id`: DID 라우팅 규칙 ID (PK)
- `routecode`: DID 착신 번호 / 라우팅 코드
- `alias`: 규칙 별칭/설명
- `contact`: 대상 이메일 주소
- `printer`: 인쇄할 프린터명
- `faxcatid`: 연결할 카테고리 ID
- `error`: 최근 에러 메시지
- `didroute`: `DIDRoute` 레포지토리
- `all_data`: 로드된 레코드 딕셔너리

### 메서드(Methods)
1. `__init__(db: Optional[DatabaseEngine] = None, repo: Optional[MDBOData] = None, lang: Optional[dict[str, str]] = None)`
2. `create(route: str, alias: str, contact: Optional[str] = None, printer: Optional[str] = None, faxcatid: Optional[int] = None) -> bool`
   - `contact` 제공 시 이메일 유효성 검사 실패 시 `False` 및 `REGWARN_MAIL`
   - `alias` 또는 `route`가 비어있거나 `<NONE>`인 경우 실패 및 `DIDROUTE_NOT_CREATED`
   - 이미 동일한 `routecode`가 존재하는 경우 실패 및 `DIDROUTE_EXISTS`
   - DB에 신규 저장 후 `didr_id` 갱신. 성공 시 `True`, 실패 시 `False`
3. `delete_route(didr_id: int) -> bool`
   - 지정된 ID의 라우팅 규칙 삭제
4. `get_routes() -> Optional[list[int]]`
   - 등록된 모든 라우팅 규칙 ID 목록을 반환 (`[0, id1, id2, ...]`)
   - 등록된 규칙이 없으면 `None` 및 `DIDROUTE_NO_ROUTES`
5. `list_routes_step() -> Optional[tuple[int, str, str]]`
   - `SELECT * FROM DIDRoute ORDER BY alias` 순회
   - `(didr_id, alias, routecode)` 반환
6. `load_route(routecode: str) -> bool`
   - `routecode`로 규칙 조회 및 로드
   - 없으면 `False` 및 `DIDROUTE_DOESNT_EXIST`
7. `loadbyid(didr_id: int) -> bool`
   - `didr_id`로 규칙 조회 및 로드
8. 게터: `get_alias()`, `get_contact()`, `get_printer()`, `get_faxcatid()`, `get_didr_id()`, `get_route()`, `get_error()`
9. 세터: `set_alias(alias)`, `set_routecode(routecode)`, `set_contact(contact)`, `set_printer(printer)`, `set_faxcatid(faxcatid)`
   - 로드 안 되었으면 "No entry loaded" 에러
   - 로드되었으면 DB에 변경 사항 반영

---

## 3. Error Messages / Localization Constants
- `REGWARN_MAIL`: "Please enter a valid e-mail address."
- `DIDROUTE_NOT_CREATED`: "Route could not be created"
- `DIDROUTE_EXISTS`: "DID route already exists"
- `DIDROUTE_NO_ROUTES`: "No DID routes configured"
- `DIDROUTE_DOESNT_EXIST`: "DID route '%s' doesn't exist"

---

## 4. Modern Python Design (Idiomatic)
- `DIDRoutingService` 및 `DIDRouting` 클래스명 별칭 제공
- `list_all()` 모던 딕셔너리 리스트 반환 헬퍼 제공
- CLI/IPC 브리지: `bridge_cli.py`의 `did` 액션을 통해 레거시 PHP `DIDRoutingBridge.php`와 통신 가능
