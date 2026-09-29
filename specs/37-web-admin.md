# Specification: Module 37 - WebAdmin

## 1. Overview
- **Module Name**: `WebAdmin`
- **Legacy Source**: `legacy/avantfax/admin/*.php`
- **Target Implementation**: `src/avantfax/web/views/admin.py`
- **Primary Role**: AvantFAX 관리자 전용 설정 및 통합 관리 인터페이스. 사용자 계정 CRUD, 모뎀 장치 설정, DID/바코드 라우팅 규칙, DynConf 수신 거부 목록, 팩스 카테고리 및 표지 템플릿 관리.

---

## 2. Interface Specification
- **AdminHandler**:
  - `list_users() -> List[Dict[str, Any]]`: 등록된 사용자 목록 조회
  - `save_user(user_data) -> bool`: 사용자 생성 또는 정보 갱신
  - `delete_user(uid) -> bool`: 사용자 계정 삭제
  - `list_modems() -> List[Dict[str, Any]]`: 모뎀 장치 및 상태 목록 조회
  - `save_modem(device, alias, contact, printer, faxcatid) -> bool`: 모뎀 설정 저장
  - `list_did_routes() -> List[Dict[str, Any]]`: DID 라우팅 규칙 목록
  - `save_did_route(routecode, alias, contact, printer, faxcatid) -> bool`: DID 라우팅 저장
  - `list_dynconf() -> List[Dict[str, Any]]`: DynConf 수신 거부 목록
  - `add_dynconf(device, callid) -> bool`: 수신 거부 규칙 추가
  - `list_categories() -> List[Dict[str, Any]]`: 팩스 카테고리 목록
  - `save_category(catid, name) -> bool`: 카테고리 생성/수정

---

## 3. Verification & Testing Strategy
- **Unit Tests (`tests/unit/test_web_admin.py`)**:
  - 관리자 권한 검증 및 사용자/장치/라우팅 설정 조회 및 생성 검증
  - DynConf 블랙리스트 및 카테고리 CRUD 검증
