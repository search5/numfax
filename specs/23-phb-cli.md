# Module Specification: 23. phb (CLI)

## 1. 개요 (Overview)
- **모듈명**: `phb` (`src/avantfax/cli/phb.py`)
- **레거시 파일**: `legacy/avantfax/includes/phb.php`
- **의존성**:
  - `AFAddressBook` (`src/avantfax/services/addressbook.py`)
- **책임**:
  - AvantFAX 주소록의 회사 및 팩스번호 데이터를 읽어 HylaFAX 호환 전화번호부(`PBOOK1.1` 포맷) 파일로 동기화/출력.
  - cron 주기 실행(예: 매시간 `0 * * * *`)을 위한 CLI 배치 엔트리포인트 제공.
  - 파일 경로를 옵션(`-o`, `--output`) 및 환경변수(`PHONEBOOK`), 기본값(`/var/spool/hylafax/etc/phonebook`)으로 유연하게 설정 가능.

---

## 2. 파일 포맷 명세 (HylaFAX PBOOK1.1)
- **헤더**: `PBOOK1.1`
- **레코드 구조**:
  - 각 회사마다: `{company}|{fax1;fax2;...}|||||||`
  - 줄바꿈 없이 단일 바이너리/텍스트 스트림 형태로 연속 기록.

---

## 3. 인터페이스 명세 (API Contract)
```bash
python3 -m avantfax.cli.phb [-o /path/to/phonebook]
```
- `generate_phonebook_content(addressbook: AFAddressBook) -> str`
- `run_phb(output_path: Optional[str] = None, addressbook: Optional[AFAddressBook] = None) -> int`
