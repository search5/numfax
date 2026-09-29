# Specification: Web Route 20 - Admin Dynamic Configuration / Blacklist (W28_admin_dynconf)

## 1. Overview
관리자가 HylaFAX faxgetty 동적 착신 필터링을 위한 발신번호(CallerID) 수신 거부 블랙리스트 및 장치별 규칙을 설정하는 화면입니다.
레거시 `legacy/avantfax/admin/conf_dynconf.php`, `conf_dynconf.tpl`, `conf_dynconf_edit.tpl`에 대응합니다.

## 2. Route Definition
- **Route Name**: `admin_dynconf`
- **URL Pattern**: `/admin/dynconf`
- **HTTP Methods**: `GET`, `POST`
- **ACL Permission**: `admin`
- **Template**: `admin_dynconf.jinja2`

## 3. UI Layout & Visual Contract
- **Master-Detail Layout**:
  - 좌측: 등록된 블랙리스트 CallerID 목록 (`dynconf_rules`)
  - 우측: 수신거부 규칙 추가/수정 폼 (`#dynconf-form`)
- **Form Controls (`#dynconf-form`)**:
  - `callid` (text, required): 차단할 발신번호 패턴 또는 정규표현식
  - `device` (select): 적용 대상 모뎀 장치 (`ttyS0`, `All Devices`)
  - `dynconf_id` (hidden): 수정 시 식별자
  - `_submit_check` (hidden, value="1")
  - `submit` (button): Save

## 4. Golden Master Contract (`W28_admin_dynconf`)
- **Status Code**: `200`
- **Required Text**: `["Dynamic Configuration", "Caller ID", "Modem Device"]`
- **Required Form**: `method="post"`, `action="/admin/dynconf"`
