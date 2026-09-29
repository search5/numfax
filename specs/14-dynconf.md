# Module Specification: 14. DynamicConfig

## 1. Overview
- **레거시 모듈**: `legacy/avantfax/includes/DynamicConfig.php`
- **신규 타깃 모듈**: `src/avantfax/services/dynconf.py`
- **역할**: HylaFAX Dynamic Configuration 연동을 위한 발신번호(CallID) 및 디바이스(device) 기반 수신 거부(RejectCall) 블랙리스트 규칙 CRUD 및 조회 서비스.
- **주요 의존성**:
  - `src/avantfax/models/entities.py` (`DynConf`)
  - `src/avantfax/db/repository.py` (`MDBOData` / `Repository`)
  - `src/avantfax/db/engine.py` (`DatabaseEngine`)

---

## 2. Legacy API Analysis & Behavior

### 속성(Attributes)
- `dynconf_id` (int | None): 로드된 규칙의 식별자
- `device` (str | None): 모뎀 디바이스명 (None 또는 빈 문자열인 경우 모든 디바이스에 적용)
- `callid` (str | None): 발신번호 또는 CallID 패턴
- `error` (str | None): 최근 에러 메시지
- `dynamicconfig`: `DynConf` 엔티티를 제어하는 `MDBOData` 레포지토리

### 메서드(Methods)
1. `__init__(db: Optional[DatabaseEngine] = None, repo: Optional[MDBOData] = None, lang: Optional[dict[str, str]] = None)`
   - `DynConf` 레포지토리 초기화 및 언어 사전 바인딩.
2. `get_dynconf_id() -> Optional[int]`
3. `get_device() -> Optional[str]`
4. `get_callid() -> Optional[str]`
5. `lookup(device: Optional[str], callid: str) -> bool`
   - `callid`로 등록된 모든 규칙을 조회.
   - 규칙 중 `device`가 비어있거나(전체 디바이스 적용), 요청된 `device`와 일치하는 규칙이 하나라도 있으면 `True`(차단 대상) 반환.
   - 일치하는 규칙이 없으면 `False` 반환.
6. `list_rules() -> list[dict[str, Any]]`
   - 등록된 모든 규칙을 `ORDER BY callid` 순으로 정렬하여 반환 (`dynconf_id`, `device`, `callid`).
7. `remove(dynconf_id: int) -> bool`
   - 지정된 ID의 규칙을 삭제.
8. `get_error() -> Optional[str]`
   - 최근 에러 메시지 반환.
9. `create(device: Optional[str], callid: str) -> bool`
   - 중복 규칙(`device`와 `callid` 쌍) 검사: 이미 존재할 경우 실패 (`DYNCONF_EXISTS`).
   - 새 규칙 저장 및 `dynconf_id` 속성 업데이트. 성공 시 `True`, 실패 시 `False` (`DYNCONF_NOT_CREATED`).
10. `load_rule(dynconf_id: int) -> bool`
    - ID로 규칙을 로드하여 내부 속성(`dynconf_id`, `device`, `callid`) 설정.
    - ID가 없거나 레코드가 없으면 에러 설정 후 `False` 반환.
11. `save_rule(device: Optional[str], callid: str) -> bool`
    - 로드된 상태에서 `device`와 `callid`를 수정하여 DB에 저장.
    - 로드되지 않은 상태인 경우 실패 ("DynConf not loaded").

---

## 3. Error Messages / Localization Constants
- `DYNCONF_EXISTS`: "Rule already exists"
- `DYNCONF_NOT_CREATED`: "Rule could not be created"
- 기타 에러 문자열:
  - "DynConf not selected"
  - "Rule %d doesn't exist"
  - "DynConf not loaded"

---

## 4. Modern Python Design (Idiomatic)
- `DynamicConfigService` 및 `DynamicConfig` 클래스명 별칭 제공
- 레거시 PHP의 reduce_array로 인한 lookup 버그를 방지하고 `find(..., reduce_single=False)`를 사용하여 항상 안전한 리스트 순회 보장
- CLI/IPC 브리지: `bridge_cli.py`의 `dynconf` 액션을 통해 레거시 PHP `DynamicConfigBridge.php`와 통신 가능
