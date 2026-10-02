# 로그 (추가만 한다)

`grep "^## \[" log.md | tail -5` 로 최근 항목을 본다.

## [2026-10-02] schema | 위키 시작
Karpathy 의 LLM Wiki gist(2026-04-04)를 읽고 [[CLAUDE]] 를 만들었다. 원본 자료는 현재 코드·문서와 git 의 삭제된 파일(커밋 01f2f64, 72a7324, 9408385)로 하고, 복사하지 않는다.

## [2026-10-02] ingest | 원본 문서 요약 17개 (하이쿠 6개 에이전트)
ARCHITECTURE.md(앞·뒤 절반), 결함 보고서(종합과 1~5라운드), 감사 보고서, 설계·계획·이력 문서, 운영·이전 가이드, AGENTS.md 를 `sources/` 로 요약했다. 모두 `verified: false`(문서가 주장하는 바이며 코드 확인 없음).

## [2026-10-02] topic | 주제 종합 11개 (소넷 4개 에이전트, 코드 대조)
`topics/` 를 코드를 읽어 확인하며 썼다. 문서와 코드가 달랐던 곳은 각 페이지에 `> 모순:` 으로 남겼다.

## [2026-10-02] lint | 첫 점검
형식(frontmatter)·링크·고아 페이지·비밀 값 점검: 문제 없음(HylaFAX 문법 `[[FAX: 번호]]` 는 코드 표기로 바꿔 링크로 오인되지 않게 함).
에이전트 주장 4건을 코드로 직접 확인: systemd 단위에 `EnvironmentFile` 없음, `upload_file` 의 바깥 호출처 없음, `export_phonebook` 이 개수가 아니라 0 을 반환, `namifax serve` 가 `wsgiref` 로 `create_app` 을 설정 없이 호출. 모두 일치.
코드 쪽 결함 후보(위키에는 `> 모순:` 으로 기록, 아직 고치지 않음): 전화번호부 작업 요약이 항상 "0 entries", 정기 실행이 프로세스 간 동시 실행을 막지 않음, 환경 파일이 서비스에 전달되지 않음, `namifax serve` 가 ini 설정을 읽지 못함.

## [2026-10-02] topic | 코드 수정 반영과 [코드] 전체 재검증
직전 두 커밋 `740e12e`, `26fcf82` 의 변경을 현재 코드로 확인해 topics 에 반영했다.
로그인 쿠키 `Secure` 가 `session.secure`/`NAMIFAX_SESSION_SECURE` 를 따름(authentication), 시스템 기능 데몬 상태가 `pgrep` 실제 값(known-gaps), 숫자 판정 `isdecimal`·비밀 화면 superuser 한정·가상 프린터 `sendfax` 연결을 known-gaps 새 행으로 기록.
hylafax-integration 의 "sendfax 를 호출하지 않는다"와 scheduler-and-storage 의 "일반 관리자도 `/admin/storage` 가능"을 정정, operations 3.1 의 환경 파일 따옴표 경고를 문서화·시험됨으로 갱신.
`cli/print_in.py` 가 `pyproject.toml`·`main.py`·`deploy/` 어디에도 연결돼 있지 않다는 점은 다시 확인해 그대로 남김. 시험은 읽기만 했다.

## [2026-10-02] topic | 마무리: 추가 수정과 푸시
`[코드]` 재검증 뒤에 더 고친 것: 로그인 쿠키 `Secure`(`NAMIFAX_SESSION_SECURE`), 시스템 기능 화면의 데몬 상태를 `pgrep` 실제 값으로, 숫자 판정 `isdigit`→`isdecimal`(위첨자 숫자 500), 가상 프린터가 실제로 `sendfax` 에 넘김과 `namifax print-in`·CUPS 백엔드 연결, 환경 파일 값에 `&`·공백이 있으면 큰따옴표, SMTP·프린터·스토리지·SAML 화면은 슈퍼유저만.
위키 반영: [[authentication-and-security]], [[known-gaps-and-decisions]], [[hylafax-integration]], [[operations-and-deployment]], [[scheduler-and-storage]]. 일반 시험 2274개 통과, 서버 DB 시험은 미실행. 커밋 `9408385..21a56e2` 푸시.
알고도 고치지 않은 것과 이유는 [[known-gaps-and-decisions]] 5절에 모았다.

## [2026-10-02] ingest | 원본 문서 2개 삭제(PORTING_GAPS, NEW_FEATURES_PLAN)
`docs/PORTING_GAPS.md` 는 [[known-gaps-and-decisions]] 로, `docs/NEW_FEATURES_PLAN.md` 는 `topics/` 의 코드 기준 서술로 대체되어 삭제했다. 두 `sources/` 요약의 원본 경로는 `git show 61c3663:...` 로 바꿨다.


## [2026-10-02] topic | hylafax-operations-notes 추가, 설계 문서 삭제
`docs/hylafax_avantfax_integration_architecture.md` 에서 위키에 없던 내용(원문 3장 수신 스풀 이동, 4.2·5장 `faxqclean`·팩스 한 통의 파일 구조, 10장 발송 첨부 형식, 11장 print-to-fax)을 [[hylafax-operations-notes]] 로 옮기고 문서를 삭제했다. 아카이브 단계 파일 이름과 보관 폴더 설정(`AVANTFAX_ARCHIVE`), 업로드 형식 검사는 코드로 직접 확인했다. 나머지 장은 [[hylafax-integration]]·[[scheduler-and-storage]] 에 이미 있거나 설계안(미구현)이라 옮기지 않았다.
