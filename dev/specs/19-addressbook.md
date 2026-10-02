# Module Specification: 19. AFAddressBook

## 1. Overview
- **레거시 모듈**: `legacy/avantfax/includes/AFAddressBook.php`
- **신규 타깃 모듈**: `src/avantfax/services/addressbook.py`
- **역할**: 고객사(Company), 팩스 번호 및 라우팅 설정(AddressBookFAX), 이메일 연락처(AddressBookEmail)를 통합 관리하는 AvantFAX 중앙 주소록 서비스.
- **주요 의존성**:
  - `src/avantfax/models/entities.py` (`AddressBook`, `AddressBookFAX`, `AddressBookEmail`)
  - `src/avantfax/db/repository.py` (`MDBOData` / `Repository`)
  - `src/avantfax/common/validators.py` (`is_valid_email`)
  - `src/avantfax/db/engine.py` (`DatabaseEngine`)

---

## 2. Legacy API Analysis & Behavior

### 엔티티 구조
1. `AddressBook`: `abook_id` (PK), `company`
2. `AddressBookFAX`: `abookfax_id` (PK), `abook_id`, `faxnumber`, `email`, `description`, `to_person`, `to_address`, `to_zip`, `to_city`, `to_location`, `to_voicenumber`, `faxcatid`, `printer`, `faxfrom`, `faxto`
3. `AddressBookEmail`: `abookemail_id` (PK), `abook_id`, `contact_name`, `contact_email`

### 메서드(Methods)
1. **회사(Company) 관리**
   - `create(companyname: str) -> bool`: 회사 생성
   - `loadbycid(cid: int) -> bool`: 회사 ID로 로드
   - `get_companies(with_reserved: bool = False) -> list[dict]`: 전체 회사 목록 반환
   - `search_companies(query: str) -> list[dict]`: 회사명 검색
   - `set_company(companyname: str) -> bool`: 회사명 변경
   - `delete_cid(cid: int) -> bool`: 회사 삭제
   - `has_fax2email() -> bool`: 이메일 착신 전달(fax2email) 설정 여부 확인
   - `get_company() -> Optional[str]`
   - `get_companyid() -> Optional[int]`

2. **팩스 번호(Fax) 관리**
   - `create_faxnumid(faxnumber: str) -> bool`: 현재 회사에 팩스 번호 추가
   - `delete_companyfaxids(cid: int) -> bool`: 회사의 모든 팩스 번호 삭제
   - `delete_faxnumid(abookfax_id: int) -> bool`: 팩스 번호 엔트리 삭제
   - `loadbyfaxnumid(abookfax_id: int) -> bool`: 팩스 번호 ID로 로드
   - `loadbyfaxnum(faxnumber: str) -> tuple[bool, bool]`: 팩스 번호로 조회 (성공 여부, 복수 회사 매칭 여부)
   - `reassign(newcid: int) -> bool`: 팩스 번호를 새 회사 ID로 재배정하고 이전 회사 삭제
   - `save_settings(data: dict) -> bool`: 팩스 번호 메타데이터 업데이트
   - `inc_faxfrom() -> bool` / `inc_faxto() -> bool`: 송수신 카운터 1 증가
   - 팩스 게터들: `get_faxnumber()`, `get_description()`, `get_category()`, `get_printer()`, `get_faxnumid()`, `get_email()`, `get_faxfrom()`, `get_faxto()`, `get_to_person()`, `get_to_address()`, `get_to_zip()`, `get_to_city()`, `get_to_location()`, `get_to_voicenumber()`

3. **이메일 연락처(Contact) 관리**
   - `create_contact(name: str, email: str) -> bool`: 단일 연락처 추가
   - `create_contacts(string: str)`: 쉼표/세미콜론으로 구분된 다중 연락처 문자열 파싱 및 추가
   - `get_contacts() -> dict[int, str]`: `"이름" <이메일>` 형식의 연락처 맵 반환
   - `make_contact_list_step() -> Optional[tuple[int, str, str]]`: 순차 순회
   - `remove_contact(abookemail_id: int) -> bool`: 연락처 삭제
   - `load_contact_by_id(abookemail_id: int) -> bool`: 연락처 ID로 로드
   - `update_contact(name: str, email: str) -> bool`: 연락처 수정
   - `get_contact_name() -> Optional[str]`, `get_contact_email() -> Optional[str]`

---

## 3. Error Messages / Localization Constants
- `ASSIGN_MISSING`: "Please enter a company name"
- `COMPANY_EXISTS`: "Company already exists"
- `FAXNUMID_NOT_CREATED`: "Fax number could not be created"
- `NO_COMPANY_FOR_FAXNUM`: "No company configured for fax number"
- `REGWARN_MAIL`: "Please enter a valid e-mail address."
- `NAME_MISSING`: "Please enter a name"
- `REGWARN_MAIL_EXISTS`: "A contact with that e-mail address already exists"

---

## 4. Modern Python Design (Idiomatic)
- `AddressBookService` 및 `AFAddressBook` 클래스명 별칭 제공
- `clean_faxnum(faxnum: str)` 함수를 분리하여 전화번호 정제 표준화
- CLI/IPC 브리지: `bridge_cli.py`의 `abook` 액션을 통해 레거시 PHP `AFAddressBookBridge.php`와 통신 가능
