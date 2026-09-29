# Specification: Web Route 19 - Admin Configure Barcode Routing (W27_admin_barcodes)

## 1. Overview
관리자가 바코드 인식 기반 팩스 착신 라우팅 규칙(바코드 값별 담당자 이메일, 프린터, 카테고리 매핑)을 설정하는 화면입니다.
레거시 `legacy/avantfax/admin/conf_barcoderoute.php`, `conf_barcoderoute.tpl`, `conf_barcoderoute_edit.tpl`에 대응합니다.

## 2. Route Definition
- **Route Name**: `admin_barcodes`
- **URL Pattern**: `/admin/barcodes`
- **HTTP Methods**: `GET`, `POST`
- **ACL Permission**: `admin`
- **Template**: `admin_barcodes.jinja2`

## 3. UI Layout & Visual Contract
- **Master-Detail Layout**:
  - 좌측: 등록된 바코드 라우팅 규칙 테이블 (`barcodes`)
  - 우측: 바코드 규칙 등록/수정 폼 (`#barcode-form`)
- **Form Controls (`#barcode-form`)**:
  - `barcode` (text, required): 인식할 바코드 문자열
  - `alias` (text, required): 라우트 별칭
  - `contact` (text): 담당자 알림 이메일
  - `printer` (text): 자동 출력 프린터 명칭
  - `faxcatid` (select): 자동 분류 카테고리
  - `barcode_id` (hidden): 수정 시 식별자
  - `_submit_check` (hidden, value="1")
  - `submit` (button): Save

## 4. Golden Master Contract (`W27_admin_barcodes`)
- **Status Code**: `200`
- **Required Text**: `["Configure Barcode Routing", "Barcode", "Alias"]`
- **Required Form**: `method="post"`, `action="/admin/barcodes"`
