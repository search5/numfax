# Specification: Web Route 21 - Admin Fax-to-Email Routing (W29_admin_fax2email)

## 1. Overview
관리자가 특정 회사 또는 수신 팩스 번호별로 이메일 직접 포워딩 규칙 및 프린터, 카테고리 매핑을 설정하는 화면입니다.
레거시 `legacy/avantfax/admin/fax2email.php`, `fax2email.tpl`, `fax2email_edit.tpl`에 대응합니다.

## 2. Route Definition
- **Route Name**: `admin_fax2email`
- **URL Pattern**: `/admin/fax2email`
- **HTTP Methods**: `GET`, `POST`
- **ACL Permission**: `admin`
- **Template**: `admin_fax2email.jinja2`

## 3. UI Layout & Visual Contract
- **Master-Detail Layout**:
  - 좌측: 등록된 주소록 회사 목록 테이블
  - 우측: 해당 회사의 팩스 번호별 이메일 전달 설정 폼 (`#fax2email-form`)
- **Form Controls (`#fax2email-form`)**:
  - `company` (text, required): 회사명
  - `email` (text): 포워딩할 수신 이메일 주소
  - `printer` (text): 자동 출력 프린터
  - `faxcatid` (select): 자동 분류 카테고리
  - `_submit_check` (hidden, value="1")
  - `submit` (button): Save

## 4. Golden Master Contract (`W29_admin_fax2email`)
- **Status Code**: `200`
- **Required Text**: `["Fax to Email", "Company", "Email"]`
- **Required Form**: `method="post"`, `action="/admin/fax2email"`
