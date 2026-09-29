# Contract Specification: Module 06 - FileUpload

## 1. Overview
- **레거시 모듈**: `legacy/avantfax/includes/FileUpload.php` (클래스 `FileUpload`)
- **타깃 모듈**: `src/avantfax/common/upload.py` (클래스 `FileUpload`)
- **의존 관계**: Leaf (독립 파일 처리 모듈)

---

## 2. Interface Contract (인터페이스 명세)

### 2.1 Error Codes
- `FU_NO_FILE = 201`
- `FU_INVALIDMIME = 202`
- `FU_OVER_SIZE = 203`
- `FU_INI_SIZE = 204`
- `FU_FORM_SIZE = 205`
- `FU_PARTIAL = 206`
- `FU_NO_TMPDIR = 207`
- `FU_CANT_WRITE = 208`

### 2.2 Configuration & Constraints
- `limit_mimetype(mimetypes: list[str] | str) -> None`
  - 허용할 MIME 타입 화이트리스트 등록.
- `limit_size(size_bytes: int) -> None`
  - 최대 허용 파일 크기(바이트) 설정.
- `sanitize_filename(name: str) -> str`
  - 파일명에 포함된 비알파벳/숫자/특수기호(`[^\w\.-_]`)를 `_`로 치환 및 디렉터리 순회(`../`) 방어.

### 2.3 File Ingestion & Persistence
- `load_file(file_info: dict | str | Path) -> bool`
  - **선행 조건**: 업로드된 파일 정보(dict: `name`, `tmp_name`, `size`, `type`, `error`) 또는 로컬 임시 파일 경로.
  - **후행 조건**: 파일명 정제, 크기 제한, MIME 타입 유효성 검사 수행 후 성공 시 `True`, 실패 시 적절한 `FU_*` 에러 코드 설정 및 `False` 반환.
- `set_randname(n: int = 9) -> str`
  - 고유한 랜덤 접두사를 파일명 앞에 부착하여 파일명 충돌 방지.
- `movefile(dest_dir: str | Path) -> bool`
  - **선행 조건**: 대상 디렉터리 경로.
  - **후행 조건**: 대상 디렉터리가 없으면 생성(`0o770`)하고 임시 파일을 대상 경로로 원자적(Atomic) 또는 안전하게 이동/복사.

---

## 3. Idiomatic Transformation Rules
1. **Path Traversal Security**: `os.path.basename` 및 정규식을 철저히 적용하여 `../../` 공격을 원천 차단.
2. **Pathlib Integration**: 문자열 경로뿐 아니라 `pathlib.Path` 객체 지원.
3. **MIME Detection**: `mimetypes` 및 파일 매직 넘버를 통한 정확한 MIME 분석.
