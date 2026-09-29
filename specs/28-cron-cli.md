# Module Specification: 28. avantfaxcron (CLI)

## 1. 개요 (Overview)
- **모듈명**: `cron` (`src/avantfax/cli/cron.py`)
- **레거시 파일**: `legacy/avantfax/includes/avantfaxcron.php`
- **의존성**:
  - `ArchiveIn` (`src/avantfax/services/archive_in.py`)
  - `FaxPDFArchive` (`src/avantfax/services/archive_base.py`)
- **책임**:
  - 일일 정기 크론 배치 작업 실행.
  - `-i num-days`: 수신함(`Inbox`)에서 지정 일수 이상 경과한 팩스를 일반 아카이브로 이동.
  - `-d num-days`: 수신함 및 아카이브에서 지정 일수 이상 경과한 팩스 메타데이터 및 파일 영구 삭제.
  - `-t num-days` (필수): AvantFAX 임시 디렉터리 내 지정 일수 이상 경과한 임시 파일/폴더 정리.
  - 필수 인자 `-t` 누락 시 사용법 출력 후 정상 종료 (`code 0`).

---

## 2. 인터페이스 명세 (API Contract)
```bash
python3 -m avantfax.cli.cron [-i num-days] [-d num-days] -t num-days
```
- `run_cron(argv: Sequence[str], archive_in=None, archive_base=None, tmp_dir=None) -> int`

---

## 3. 검증 시나리오 (Golden Master 연동)
- **시나리오 04**: 인자 없음 -> Usage 출력 및 code 0
- **시나리오 05**: `-z` 잘못된 옵션 -> Usage 출력 및 code 0
- **추가 단위 테스트**: `-t`, `-i`, `-d` 플래그 정상 전달 시 prune 및 파일 정리 실행 검증.
