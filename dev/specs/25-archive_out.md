# Module Specification: 25. ArchiveOut

## 1. 개요 (Overview)
- **모듈명**: `ArchiveOut` (`src/avantfax/services/archive_out.py`)
- **레거시 파일**: `legacy/avantfax/includes/ArchiveOut.php`
- **의존성**:
  - `FaxPDFArchive` (`src/avantfax/services/archive_base.py`)
  - `DatabaseEngine` (`src/avantfax/db/engine.py`)
- **책임**:
  - 송신(Outbound) 팩스 메타데이터 생성 및 아카이브 저장 (`inbox=0`, `userid` 바인딩).
  - 설치 경로(`installdir`) 상대 경로 변환 및 팩스 수신번호 정제.

---

## 2. 인터페이스 명세 (API Contract)

### `ArchiveOut(db=None, installdir='')` (FaxPDFArchive 상속)
- `create(path: str, userid: int, cid: Optional[int], origfaxnum: str, pages: int) -> bool`
- Getters 상속: `get_fid()`, `get_userid()`, `get_companyid()`, `get_origfaxnum()`, `get_pages()`, `get_pdfpath()` 등.

---

## 3. 검증 시나리오 (Test Scenarios)
1. `create`: 송신 팩스 생성 후 `inbox=0`, `userid`, `companyid`, `origfaxnum`, `pages` 정상 저장 검증.
2. `load_fax`: 생성된 송신 팩스를 `load_fax`로 다시 불러와 필드 일치 확인.
