# Module Specification: 17. DistributionList

## 1. Overview
- **레거시 모듈**: `legacy/avantfax/includes/DistributionList.php`
- **신규 타깃 모듈**: `src/avantfax/services/distro.py`
- **역할**: 다수의 수신자에게 팩스를 동시 전송하기 위한 배포/동보 전송 그룹 목록(`DistroList` 테이블) 및 그룹 내 수신 대상(콜론 `:` 구분) 엔트리 관리 서비스.
- **주요 의존성**:
  - `src/avantfax/models/entities.py` (`DistroList`)
  - `src/avantfax/db/repository.py` (`MDBOData` / `Repository`)
  - `src/avantfax/db/engine.py` (`DatabaseEngine`)

---

## 2. Legacy API Analysis & Behavior

### 상수
- `DL_SEPARATOR = ":"`

### 속성(Attributes)
- `dl_id`: 배포 목록 ID (PK)
- `listname`: 배포 목록명
- `listdata`: 콜론으로 구분된 엔트리 문자열 (예: `"101:102:103"`)
- `lastmod_date`: 최근 수정 시각
- `lastmod_user`: 최근 수정한 사용자 ID (uid)
- `error`: 최근 발생한 에러 메시지
- `distrolist`: `DistroList` 레포지토리

### 메서드(Methods)
1. `__init__(db: Optional[DatabaseEngine] = None, repo: Optional[MDBOData] = None, lang: Optional[dict[str, str]] = None)`
2. `get_dl_id() -> Optional[int]`
3. `get_listname() -> Optional[str]`
4. `get_lastmod() -> dict[str, Any]`
   - `{"date": self.lastmod_date, "user": self.lastmod_user}` 반환
5. `set_moduser(uid: int)`
   - 최근 수정 사용자 ID 설정
6. `create(listname: str) -> bool`
   - `listname`이 비어있으면 실패 (`DISTROLIST_ENTER_LISTNAME`)
   - 이미 동일한 `listname`이 존재하면 실패 (`DISTROLIST_EXISTS`)
   - DB에 신규 저장 후 `dl_id` 갱신. 성공 시 `True`, 실패 시 `False` (`DISTROLIST_NOT_CREATED`)
7. `delete_list(list_id: int) -> bool`
   - 지정된 ID의 배포 목록 삭제
8. `get_distrolists() -> list[dict[str, Any]]`
   - 등록된 모든 배포 목록 조회 (`SELECT dl_id, listname FROM DistroList ORDER BY listname`)
9. `load_list(list_id: int) -> bool`
   - ID로 목록 로드 후 속성 바인딩. 실패 시 `False`
10. `set_listname(listname: str) -> bool`
    - 목록이 로드된 상태에서 이름 변경 및 DB 저장
11. `list_entries() -> list[str]`
    - 로드된 `listdata`를 콜론(`:`)으로 분리한 리스트 반환
12. `add_entries(entries: list[str]) -> bool`
    - 기존 목록에 중복 없이 항목 추가 후 DB 저장
13. `remove_entries(entries: list[str]) -> bool`
    - 기존 목록에서 지정된 항목 제거 후 DB 저장

---

## 3. Error Messages / Localization Constants
- `DISTROLIST_ENTER_LISTNAME`: "Please enter a list name"
- `DISTROLIST_EXISTS`: "A distribution list by that name already exists"
- `DISTROLIST_NOT_CREATED`: "Distribution list could not be created"
- 기타 에러 문자열:
  - "DList not selected"
  - "List %s doesn't exist."
  - "No list loaded"

---

## 4. Modern Python Design (Idiomatic)
- `DistributionListService` 및 `DistributionList` 클래스명 별칭 제공
- Python `set` 연산을 활용한 안전하고 빠른 엔트리 추가/제거 및 순서 유지
- CLI/IPC 브리지: `bridge_cli.py`의 `distro` 액션을 통해 레거시 PHP `DistributionListBridge.php`와 통신 가능
