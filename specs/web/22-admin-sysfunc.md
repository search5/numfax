# Specification: Web Route 22 - Admin System Functions (W30_admin_sysfunc)

## 1. Overview
관리자가 HylaFAX/NamiFAX 데몬 재시작(Reboot), 서비스 정지(Shutdown), 아카이브 백업 다운로드 및 데이터베이스 덤프 다운로드를 수행하는 관리 인터페이스입니다.
레거시 `legacy/avantfax/admin/system_func.php`, `system_func.tpl`에 대응합니다.

## 2. Route Definition
- **Route Name**: `admin_system_func`
- **URL Pattern**: `/admin/system_func`
- **HTTP Methods**: `GET`, `POST`
- **ACL Permission**: `admin`
- **Template**: `admin_sysfunc.jinja2`

## 3. UI Layout & Visual Contract
- **Control Panels**:
  - 시스템 제어 패널: `Reboot Service`, `Shutdown Service`
  - 데이터 백업 패널: `Download Archive Backup`, `Download Database Backup`
- **Form Controls (`#sysfunc-form`)**:
  - `reboot` (submit button): 서비스 재시작
  - `shutdown` (submit button): 서비스 정지
  - `download_ar` (submit button): 아카이브 tarball 다운로드
  - `download_db` (submit button): SQL 데이터베이스 덤프 다운로드
  - `_submit_check` (hidden, value="1")

## 4. Golden Master Contract (`W30_admin_sysfunc`)
- **Status Code**: `200`
- **Required Text**: `["System Functions", "Reboot", "Shutdown", "Download"]`
- **Required Form**: `method="post"`, `action="/admin/system_func"`
