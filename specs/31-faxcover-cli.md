# Specification: Module 31 - faxcover (CLI)

## 1. Overview
- **Module Name**: `faxcover`
- **Legacy Source**: `legacy/avantfax/includes/faxcover.php`
- **Target Implementation**: `src/avantfax/cli/faxcover.py`
- **Primary Role**: HylaFAX 팩스 표지(Cover Page) 생성 CLI 프로그램. EPS/PS 또는 HTML 템플릿 파일 내의 토큰(`XXXX-to`, `XXXX-from` 등)을 커맨드라인 옵션 및 DB 사용자 정보와 매핑하여 최종 표지 출력 스트림을 생성.

---

## 2. CLI Interface & Exit Semantics
- **Command Signature**:
  ```bash
  faxcover [-t to] [-c comments] [-p #pages] [-l to-location] [-m maxcomments] [-z maxlencomments] [-r regarding] [-v to-voice-number] [-x to-company] [-C template-file] [-D date-format] [-L from-location] [-M from-mail-address] [-N from-fax-number] [-V from-voice-number] [-X from-company] [-s pagesize] -f from -n fax-number
  ```
- **Option Flags**:
  - `-f from` (required): 발신자 이름 또는 이메일
  - `-n fax-number` (required): 수신 팩스 번호
  - `-t to` (optional): 수신인 이름
  - `-c comments` (optional): 비고/코멘트 내용
  - `-p #pages` (optional): 페이지 수
  - `-l to-location` (optional): 수신처 위치
  - `-m maxcomments` (optional): 최대 코멘트 줄 수
  - `-z maxlencomments` (optional): 한 줄당 최대 코멘트 길이
  - `-r regarding` (optional): 제목/건명
  - `-v to-voice-number` (optional): 수신처 전화번호
  - `-x to-company` (optional): 수신 회사명
  - `-C template-file` (optional): 템플릿 파일 경로 또는 파일명
  - `-D date-format` (optional): 날짜 포맷
  - `-L from-location` (optional): 발신처 위치
  - `-M from-mail-address` (optional): 발신자 이메일
  - `-N from-fax-number` (optional): 발신 팩스번호
  - `-V from-voice-number` (optional): 발신 전화번호
  - `-X from-company` (optional): 발신 회사명
  - `-s pagesize` (optional): 페이지 크기 (예: a4, letter)
- **Exit & Output Codes**:
  - `-f` 또는 `-n` 플래그 누락 시:
    - stdout: `Usage: faxcover [-t to] [-c comments] [-p #pages] [-l to-location] [-m maxcomments] [-z maxlencomments] [-r regarding] [-v to-voice-number] [-x to-company] [-C template-file] [-D date-format] [-L from-location] [-M from-mail-address] [-N from-fax-number] [-V from-voice-number] [-X from-company] [-s pagesize] -f from -n fax-number\n`
    - exit code: `0`
  - 정상 처리 시:
    - stdout: 생성된 PostScript/템플릿 내용 출력
    - exit code: `0`

---

## 3. Core Business Logic & Template Substitution
1. **User Account Lookup**:
   - `from_name`(`-f`) 또는 `from_email`(`-M`)을 기준으로 DB(`UserAccount`) 조회
   - 일치하는 사용자 존재 시 이름/이메일 자동 보완
2. **Template File Selection**:
   - `-C` 옵션 지정 시 해당 템플릿 사용 (HTML 또는 PS)
   - 미지정 시 시스템 기본 템플릿(`COVERPAGE_FILE`) 사용
3. **Value Mapping & Comment Wrapping**:
   - `to`, `from`, `to-company`, `regarding`, `todays-date` 등 매핑
   - 코멘트 내 커스텀 중괄호 문법(`{key:val}`) 추출 및 치환
   - `wordwrap`을 통해 줄바꿈 분할 후 `comments0`, `comments1`, ... 토큰 바인딩
4. **Output Rendering**:
   - HTML 템플릿일 경우 `process_html_template` 후 `html2ps` 변환
   - PS 템플릿일 경우 `process_template` 후 결과 stdout 출력

---

## 4. Verification & Testing Strategy
- **Unit Tests (`tests/unit/test_cli_faxcover.py`)**:
  - 옵션 누락(`no_args`, `missing_number`, `missing_from`) 시 Usage 출력 및 반환코드 검증
  - 필수 옵션 충족 시 정상 포스트스크립트/텍스트 렌더링 검증
- **Golden Master Differential Tests**:
  - `06_faxcover_no_args`: 100% PASS
  - `07_faxcover_missing_number`: 100% PASS
  - `08_faxcover_missing_from`: 100% PASS
