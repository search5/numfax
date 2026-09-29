# Module Specification: 11. Covers

## 1. Overview
- **레거시 모듈**: `legacy/avantfax/includes/Covers.php`
- **신규 타깃 모듈**: `src/avantfax/services/covers.py`
- **역할**: 팩스 발송 시 사용할 표지(Cover Page) 템플릿(PostScript/PDF 파일 및 제목)에 대한 데이터베이스 CRUD 및 조회 관리 서비스.
- **주요 의존성**:
  - `src/avantfax/models/entities.py` (`CoverPages`)
  - `src/avantfax/db/repository.py` (`MDBOData`)
  - `src/avantfax/db/base.py` (`afDB` / `SQLSession`)

---

## 2. Legacy API Analysis & Behavior

### 속성(Attributes)
- `cover_id` (int | None): 현재 로드된 표지의 ID
- `title` (str | None): 현재 로드된 표지의 제목
- `file` (str | None): 현재 로드된 표지의 파일명
- `all_data` (dict): 로드된 표지의 레코드 데이터 딕셔너리
- `error` (str | None): 최근 발생한 오류 메시지

### 메서드(Methods)
1. `__init__(repo: Optional[MDBOData] = None, session: Optional[Session] = None)`
   - `CoverPages` 엔티티를 관리하는 `MDBOData` 레포지토리를 내부적으로 초기화하거나 주입받음.
2. `create(title: str, file: str) -> bool`
   - `title` 또는 `file`이 누락되거나 빈 문자열인 경우 실패 (`COVER_NOT_CREATED`)
   - `file`이 이미 데이터베이스에 존재하는 경우 실패 (`COVER_EXISTS`)
   - 신규 표지 생성 및 `cover_id`, `title`, `file` 속성 갱신 후 `True` 반환
3. `delete_cover(id: int) -> bool`
   - 지정된 `id` (cover_id)를 가진 표지 레코드를 삭제
4. `get_covers() -> Optional[list[str]]`
   - 등록된 모든 표지의 파일명 목록(`file`)을 파일명 알파벳 오름차순(`ORDER BY file`)으로 반환
   - 등록된 표지가 없으면 `None` 반환 및 에러(`NO_COVERS_CONFIGURED`) 설정
5. `list_covers() -> list[dict[str, Any]]` (또는 iterator)
   - 제목 오름차순(`ORDER BY title`)으로 정렬된 표지 목록 반환
   - 각 항목은 `{'cover_id': ..., 'title': ..., 'file': ...}` 형태
   - 레거시의 `list_covers(&$title, &$file)` 호출 방식과 100% 호환되는 인터페이스 제공
6. `load_cover(file: str) -> bool`
   - 파일명으로 표지를 검색하여 내부 상태(`cover_id`, `title`, `file`, `all_data`) 로드
   - 파일명이 비어있거나 존재하지 않으면 `False` 반환 및 에러 메시지 설정
7. `load_by_id(cover_id: int) -> bool` (확장 메서드)
   - ID로 표지를 검색하여 내부 상태 로드
8. `get_cover_id() -> Optional[int]`
9. `get_title() -> Optional[str]`
10. `get_file() -> Optional[str]`
11. `set_title(title: str) -> bool`
    - 표지가 로드되지 않은 상태면 실패 ("No cover page loaded")
    - 제목 수정 후 DB에 반영
12. `set_file(file: str) -> bool`
    - 표지가 로드되지 않은 상태면 실패 ("No cover page loaded")
    - 파일명 수정 후 DB에 반영

---

## 3. Error Messages / Localization Constants
- `COVER_NOT_CREATED`: "Cover page could not be created"
- `COVER_EXISTS`: "Cover page already exists"
- `COVER_DOESNT_EXIST`: "Cover page '%s' doesn't exist"
- `NO_COVERS_CONFIGURED`: "No cover pages configured"

---

## 4. Modern Python Design (Idiomatic)
- SQLAlchemy 세션 및 MDBOData를 수용하는 깔끔한 서비스 클래스 `CoverService` (또는 `Covers`)
- Pydantic 또는 `CoverPages` 엔티티와의 유연한 상호 운용
- IPC/CLI 브리지 지원: `bridge_cli.py`에서 `covers` 서브커맨드로 `create`, `delete`, `list`, `get_all`, `load` 기능 노출
- PHP 브리지: `CoversBridge.php`를 통해 레거시 AvantFAX PHP 코드가 동일한 인터페이스로 투명하게 동작하도록 함
