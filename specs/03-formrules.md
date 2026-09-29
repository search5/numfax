# Contract Specification: Module 03 - FormRules

## 1. Overview
- **레거시 모듈**: `legacy/avantfax/includes/FormRules.php` (클래스 `FormRules`)
- **타깃 모듈**: `src/avantfax/common/validators.py` (클래스 `FormRules`, 검증 유틸 함수들)
- **의존 관계**: Leaf (독립 유틸리티 모듈)

---

## 2. Interface Contract (인터페이스 명세)

### 2.1 Types & Constants
- `FR_ARRAY = 10`
- `FR_STRING = 11`
- `FR_NUMBER = 12`
- `FR_DATE = 13`
- `FR_EMAIL = 14`

### 2.2 Rules Registration & Processing
- `new_rule(varname: str, defaultval: Any = None, vartype: int = FR_STRING, minlen: int = None, maxlen: int = None, error_str: str = None, required: bool = False, sanitize: bool = True, execfunc: Callable = None) -> bool`
  - **선행 조건**: 유효한 변수명(`varname`). 중복 등록 불가.
  - **후행 조건**: 폼 유효성 검사 규칙 테이블에 등록.
- `process_form(data: dict[str, Any]) -> bool`
  - **선행 조건**: 검증 대상 입력 딕셔너리.
  - **후행 조건**:
    - 모든 필수 필드 존재 여부 확인.
    - 타입(문자열, 숫자, 날짜, 이메일, 배열) 및 길이/크기 검증.
    - 커스텀 검증 함수(`execfunc`)가 있을 경우 실행.
    - 모든 규칙 통과 시 `True`, 위반 시 `False` 반환 및 에러 리스트에 기록.
- `get_form_errors() -> list[str]`
  - 발생한 에러 메시지 목록 반환.
- `get_css_error_ids() -> str | None`
  - 에러가 발생한 필드명의 CSS 선택자 문자열 반환 (예: `"#username, #email"`).
- `html_ready() -> dict[str, Any]`
  - HTML 렌더링에 적합하도록 이스케이프된 값 딕셔너리 반환.
- `db_ready() -> dict[str, Any]`
  - DB 저장에 적합한 데이터 딕셔너리 반환.

### 2.3 Standalone Validators
- `is_valid_email(email: str) -> bool`
  - RFC 5322 규격 및 레거시 호환 이메일 형식 검증.
- `is_valid_date(date_str: str, fmt: str = "ymd", delim: str = "/") -> bool`
  - 특정 구분자 및 포맷의 유효한 날짜 여부 검증.

---

## 3. Idiomatic Transformation Rules
1. **Pydantic / Dataclass 호환**: 단순 폼 규칙뿐만 아니라 Python 딕셔너리 및 Pydantic 모델과 매핑 가능하도록 설계.
2. **Magic Quotes 제거**: PHP의 레거시 `get_magic_quotes_gpc()` 및 `stripslashes`를 제거하고 순수 파이썬 문자열 처리 적용.
3. **Callable Support**: `execfunc`에 문자열 함수명뿐 아니라 실제 파이썬 함수/람다 직접 전달 지원.
