# Module Specification: 24. ArchiveIn

## 1. 개요 (Overview)
- **모듈명**: `ArchiveIn` (`src/avantfax/services/archive_in.py`)
- **레거시 파일**: `legacy/avantfax/includes/ArchiveIn.php`
- **의존성**:
  - `FaxPDFArchive` (`src/avantfax/services/archive_base.py`)
  - `DatabaseEngine` (`src/avantfax/db/engine.py`)
- **책임**:
  - 수신 팩스 메타데이터 생성 (`create`: `modemdev` 지정 및 `inbox=1` 설정).
  - 수신함에서 일반 아카이브함으로 이동 (`set_archivebox`: `inbox=0`).
  - 수신함 팩스 180도 회전 처리 (`rotate_fax`).
  - 오래된 수신 팩스 일괄 아카이빙 배치 (`prune_inbox`).

---

## 2. 인터페이스 명세 (API Contract)

### `ArchiveIn(db=None, installdir='')` (FaxPDFArchive 상속)
- `create(path: str, faxnid: int, faxnumber: str, modem: str, pages: int, date: Optional[str] = None, didr_id: Optional[int] = None) -> bool`
- `set_archivebox(faxid: int) -> bool`
- `rotate_fax() -> bool`
- `prune_inbox(days: int) -> int` (아카이빙된 건수 반환)
- `set_modemdev(modemdev: str) -> bool`

---

## 3. 검증 시나리오 (Test Scenarios)
1. `create`: 수신 팩스 생성 후 `inbox=1`, `modemdev` 설정 확인.
2. `set_archivebox`: 특정 `faxid`의 `inbox=0` 업데이트 확인.
3. `prune_inbox`: 지정일수 이전의 `inbox=1` 팩스들을 자동으로 `set_archivebox` 처리하는지 확인.
4. `rotate_fax`: 인박스에 위치한 팩스에 대한 회전 동작 및 에러 조건(`inbox=0`인 경우 실패) 검증.
