# Specification: Web Route 17 - Admin Configure Cover Pages (W25_admin_covers)

## 1. Overview
관리자가 팩스 발송 시 사용되는 커버페이지(표지) 템플릿 파일 목록을 조회하고 신규 커버페이지를 등록하거나 수정/삭제하는 화면입니다.
레거시 `legacy/avantfax/admin/conf_covers.php`, `conf_covers.tpl`, `conf_covers_edit.tpl`에 대응합니다.

## 2. Route Definition
- **Route Name**: `admin_covers`
- **URL Pattern**: `/admin/covers`
- **HTTP Methods**: `GET`, `POST`
- **ACL Permission**: `admin`
- **Template**: `admin_covers.jinja2`

## 3. UI Layout & Visual Contract
- **Master-Detail Layout**:
  - 좌측: 등록된 표지 파일 셀렉트 목록 (`files`)
  - 우측: 표지 등록/수정 폼 (`#cover-form`)
  - 하단: 도움말 패널 (`#explain-me`)
- **Form Controls (`#cover-form`)**:
  - `title` (text, required): 표지 타이틀 명칭
  - `file` (text, required): 템플릿 파일명 (예: `standard.ps`, `custom.html`)
  - `cover_id` (hidden): 수정 시 식별자
  - `_submit_check` (hidden, value="1")
  - `submit` (button): Create 또는 Save

## 4. Golden Master Contract (`W25_admin_covers`)
- **Status Code**: `200`
- **Required Text**: `["Configure Cover Pages", "Title", "File"]`
- **Required Form**: `method="post"`, `action="/admin/covers"`
