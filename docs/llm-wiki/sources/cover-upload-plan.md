---
title: 팩스 표지 업로드 계획
type: source
updated: 2026-10-03
sources: ["docs/COVER_UPLOAD_PLAN.md"]
verified: false
---

> 원본은 `docs/COVER_UPLOAD_PLAN.md`(2026-10-03 작성, 계획 문서이며 구현 전)다. 이 요약은 그 문서가 주장하는 바이고, 현재 코드와의 대조는 [[known-gaps-and-decisions]] §3 에 있다.

## 요약

- 목적: 관리자 화면 `/admin/covers` 에서 표지 파일을 올리고(새 표지 추가·편집 모드 모두), 이미 올라간 파일을 찾아보아 고른다. [[new-features-plan]] §3.5 가 약속하고 구현하지 못한 부분이다.
- 현재 상태(작성 시점에 코드와 원본 `git show 9408385:legacy/avantfax/admin/conf_covers_edit.php` 등을 읽어 확인): `services/cover_studio.py` 의 `CoverStudioService` 는 있으나 호출하는 곳이 없고, 화면에는 업로드 입력이 없다. 원본도 업로드가 없고 파일 이름을 글자로 입력하며 파일 존재를 확인하지 않는다.
- 발견한 어긋남 두 가지: (1) 서비스의 기본 저장 위치 `/var/spool/hylafax/covers` 는 발송이 읽는 `AVANTFAX_INSTALLDIR/images` 와 다르다. (2) 서비스는 `.ps`, `.pdf`, `.html`, `.jinja2` 를 받지만 표지 생성기(`cli/faxcover.py`)가 쓰는 것은 `.ps`, `.html`(`USE_HTML_COVERPAGE` 필요)뿐이다.
- 설계: 폼 계약(`title`, `file`, `cover_id`, `_submit_check`, 버튼 `create`/`save`/`delete`)은 유지하고 업로드·찾아보기를 선택 기능으로 더한다. 저장 위치는 `images/` 로 통일한다. 허용 형식은 `.ps`, `.html` 로 줄인다. 이름 검사, 크기 상한, 내용 확인, 같은 이름 처리를 서비스에 더한다.
- 범위 밖: 썸네일 미리보기, `.pdf`·`.jinja2` 표지, 파일 삭제.
- 결정 대기 3건(`[NEEDS_CLARIFICATION]`): D1 같은 이름 파일 처리(거절 또는 덮어쓰기 체크), D2 허용 형식 축소, D3 편집 화면의 파일 이름 변경 유지 여부(원본은 제목만 바뀜).
- 순서: 서비스 시험, 뷰 연결, 찾아보기와 폼, 발송 계획 확인, 문서와 위키.
