# Specification: Web Route 18 - Admin Fax Categories (W26_admin_categories)

## 1. Overview
관리자가 송/수신 팩스를 분류하고 라우팅 규칙 및 주소록에서 태그로 사용할 카테고리 목록을 관리하는 화면입니다.
레거시 `legacy/avantfax/admin/fax_categories.php`, `fax_categories.tpl`, `fax_cat_edit.tpl`에 대응합니다.

## 2. Route Definition
- **Route Name**: `admin_categories`
- **URL Pattern**: `/admin/categories`
- **HTTP Methods**: `GET`, `POST`
- **ACL Permission**: `admin`
- **Template**: `admin_categories.jinja2`

## 3. UI Layout & Visual Contract
- **Master-Detail Layout**:
  - 좌측: 등록된 카테고리 목록 테이블 (`categories`)
  - 우측: 카테고리 추가/편집 폼 (`#category-form`)
- **Form Controls (`#category-form`)**:
  - `name` (text, required): 카테고리 명칭 (예: `Invoices`, `Legal`, `Orders`)
  - `catid` (hidden): 수정 시 식별자
  - `_submit_check` (hidden, value="1")
  - `submit` (button): Create 또는 Save

## 4. Golden Master Contract (`W26_admin_categories`)
- **Status Code**: `200`
- **Required Text**: `["Fax Categories", "Category Name"]`
- **Required Form**: `method="post"`, `action="/admin/categories"`
