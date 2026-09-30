# Spec 44: Fax Cover Template Studio & Drag-and-Drop Management

## 1. 개요 및 목적
- **목적**: 기존 레거시의 파일 수동 서버 복사 한계를 해소하고, 관리자가 웹 UI(`/admin/covers`)에서 PostScript(`.ps`), PDF(`.pdf`), HTML/Jinja2(`.html`) 템플릿을 드래그앤드롭으로 직접 업로드하고, 썸네일 미리보기와 동적 태그 매핑을 제어할 수 있는 종합 팩스 커버 스튜디오를 제공합니다.
- **연동 대상**:
  - `Covers` 엔티티 및 서비스 (`src/namifax/services/covers.py`)
  - `CoverStudioService` (`src/namifax/services/cover_studio.py`)
  - 관리자 커버 페이지 뷰 (`src/namifax/views/admin.py`)

---

## 2. 지원 파일 형식 및 치환 태그

### 2.1 지원 템플릿 포맷
- PostScript (`.ps`): HylaFAX 네이티브 호환 팩스 커버.
- PDF (`.pdf`): 기업 표준 고품질 문서 서식.
- HTML / Jinja2 (`.html`): 모던 반응형 커버 서식 (동적 CSS 스타일링 지원).

### 2.2 표준 치환 변수 목록 (`COVER_TEMPLATE_TAGS`)
- `{{ to_person }}` / `XXXX-to`: 수신자 성명
- `{{ to_company }}` / `XXXX-to-company`: 수신 회사명
- `{{ to_fax }}` / `XXXX-to-fax-number`: 수신 팩스 번호
- `{{ from_person }}` / `XXXX-from`: 발신자 성명
- `{{ from_company }}` / `XXXX-from-company`: 발신 회사명
- `{{ regarding }}` / `XXXX-regarding`: 팩스 제목/용건
- `{{ comments }}` / `XXXX-comments`: 전달 메모 및 상세 코멘트
- `{{ pages }}` / `XXXX-page-count`: 총 페이지 수
- `{{ date }}` / `XXXX-date`: 발송 일시

---

## 3. 서비스 계층 명세 (`CoverStudioService`)

```python
class CoverStudioService:
    def __init__(self, db=None, covers_dir=None): ...

    def save_template(self, filename: str, content: bytes, title: str) -> dict:
        """Validate format, persist file to disk, and register in CoverPages database."""

    def render_template(self, cover_id: int, context: dict) -> bytes:
        """Render template with dynamic context mapping."""

    def get_supported_tags() -> list[dict]:
        """Return metadata list of available dynamic replacement tags."""
```

---

## 4. 검증 기준
1. 단위 테스트:
   - `tests/unit/test_cover_studio.py`:
     - 유효 포맷(`.ps`, `.pdf`, `.html`) 업로드 및 DB 등록 검증.
     - 지원되지 않는 확장자 거절 검증.
     - HTML/Text 템플릿 동적 태그 렌더링 검증.
2. 무회귀 검증:
   - 기존 334개 테스트 및 88개 골든 마스터 E2E 100% 통과.
