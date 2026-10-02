---
title: HylaFAX 연동
type: topic
updated: 2026-10-02
sources: [deploy/hylafax/, deploy/sudoers.d/namifax, deploy/cron.d/namifax, deploy/postfix/setup-email2fax.md, systemd/, pyproject.toml, src/namifax/main.py, src/namifax/cli/faxrcvd.py, src/namifax/cli/notify.py, src/namifax/cli/dynconf.py, src/namifax/cli/faxcover.py, src/namifax/cli/phb.py, src/namifax/services/sendfax_command.py, src/namifax/views/sendfax.py, src/namifax/services/modem.py, src/namifax/services/faxqueue.py, src/namifax/services/hylafax_users.py, src/namifax/services/hylafax_info.py, src/namifax/services/fax_images.py, src/namifax/common/helpers.py, src/namifax/common/settings.py, tests/unit/test_sendfax_command.py, tests/unit/test_sendfax_view_commands.py, tests/unit/test_faxrcvd_flow.py, tests/unit/test_modem.py, tests/unit/test_hylafax_user_sync.py, tests/fixtures/legacy_sendfax_commands.json, [[hylafax-integration-architecture]], [[install-hylafax]], [[setup-email2fax]], [[porting-gaps]]]
verified: true
---

# HylaFAX 연동

NamiFAX 와 HylaFAX 의 접점을 코드 기준으로 정리한다. 스케줄러는 [[scheduler-and-storage]], 설치 절차는 [[operations-and-deployment]], 시험 체계는 [[testing]].

## 0. 가장 중요한 한계: 실제 HylaFAX 로 시험한 적이 없다

- [문서] `docs/INSTALL_HYLAFAX.md` 첫머리가 "이 저장소에서는 실제 HylaFAX 에 붙여 시험하지 않았다"고 밝힌다. [[install-hylafax]]
- [코드] 시험 모음에는 HylaFAX 데몬(`faxq`, `hfaxd`, `faxgetty`)이나 실제 모뎀을 쓰는 것이 없다. 이 세션에서 `tests/` 의 HylaFAX 관련 시험을 훑은 결과, 아래 방식들로 대신한다(시험을 실행하지는 않았다).

| 대체 검증 | 무엇을 보증하나 | 무엇을 보증하지 못하나 |
|---|---|---|
| **레거시 녹화 비교**: `tests/fixtures/legacy_sendfax_commands.json` 은 원본 PHP `submit_fax()` 를 가짜 `sendfax`/`faxcover` 로 돌려 인자를 녹화한 것. `tests/unit/test_sendfax_command.py` 가 `build_plan` 결과와 비교 | 웹 폼 → `sendfax`/`faxcover` **명령줄 인자**가 원본과 같다(빈 값 옵션과 빈 주소 자리표시자만 의도적으로 뺌) | 진짜 `sendfax` 가 그 인자를 받아들이는지, 큐에 들어가는지 |
| **가짜 실행 파일**: `tests/unit/test_sendfax_view_commands.py` 가 인자를 기록하는 쉘 스크립트를 `PATH` 에 두고 `request id is 80 ...` 를 출력하게 함 | 뷰가 계획대로 프로그램을 부르고 출력에서 작업 번호를 뽑는 흐름 | HylaFAX 의 실제 출력 형식, 권한, 스풀 |
| **mock 으로 외부 의존 대체**: `tests/unit/test_faxrcvd_flow.py` 는 `faxinfo`, `tiff2pdf`, `static_preview`, `send_mail`, `bardecode`, OCR 를 `patch` 하고 가짜 TIFF(`b"mock tiff"`)로 훅을 실행 | 훅 안의 DB 처리(주소록 등록, 받은 팩스함 입력, 라우팅) | 실제 수신 TIFF 의 처리, `faxrcvd` 가 HylaFAX 에서 호출되는 방식 |
| **문자열 파서 시험**: `tests/unit/test_modem.py`, `tests/unit/test_faxqueue.py` 는 `faxstat` 출력 예시 문자열을 파서에 넣는다 | 예시 출력의 해석 | 실제 `faxstat` 출력과 `JobFmt` 일치 |
| **명령 mock**: `tests/unit/test_hylafax_user_sync.py` 는 `subprocess.run` 을 mock 으로 대체 | `sudo faxadduser/faxdeluser` 인자 구성, 쉘 미사용, 실패해도 계정 변경 유지 | sudoers 규칙이 실제로 통하는지 |

- [코드] 웹의 팩스 보내기는 `sendfax` 실행 파일이 없으면(`settings.binary("sendfax")`) **모의 접수**로 성공을 돌려줄 수 있다. 조건(`_simulation_wanted`): 환경변수 `NAMIFAX_QUEUE_SIMULATION` 이 있으면 그 값, 없으면 pytest 실행 중이거나 `/var/spool/hylafax` 가 없을 때. 이때 작업 번호는 무작위 6자리이고 응답에 `simulated: True` 가 붙는다. HylaFAX 가 없는 개발 장비에서 "성공"으로 보이는 것은 실제 송신이 아니다. `views/sendfax.py`
- 따라서 이 페이지의 "연동한다"는 모두 **명령줄 계약과 파일 형식을 원본에 맞춘 것**이지 실기 검증이 아니다. 실제 서버에서 확인할 점은 [[install-hylafax]] 7단계와 [[operations-checklist]] 에 있다. [문서]

## 1. 이벤트 훅

HylaFAX 가 부르는 실행 파일 4개와 NamiFAX 모듈의 연결. [코드] `deploy/hylafax/`, `pyproject.toml`, `src/namifax/main.py`

| HylaFAX 설정 | 위치 | 쉘 래퍼 | 콘솔 명령(`pyproject.toml`) | 모듈 |
|---|---|---|---|---|
| `FaxRcvdCmd: bin/faxrcvd` | 모뎀 설정(`config.namifax`) | `deploy/hylafax/bin/faxrcvd` | `namifax-faxrcvd` | `cli/faxrcvd.py` |
| `DynamicConfig: bin/dynconf` | 모뎀 설정 | `deploy/hylafax/bin/dynconf` | `namifax-dynconf` | `cli/dynconf.py` |
| `NotifyCmd: bin/notify` | 서버 설정(`etc-faxq.snippet`) | `deploy/hylafax/bin/notify` | `namifax-notify` | `cli/notify.py` |
| `CoverCmd: bin/faxcover` | 서버 설정 | `deploy/hylafax/bin/faxcover` | `namifax-faxcover` | `cli/faxcover.py` |

- [코드] 래퍼 4개는 같은 모양이다: `/etc/namifax.env` 가 있으면 읽고 `${NAMIFAX_HOME:-/opt/namifax}/.venv/bin/namifax-<이름>` 을 `exec` 한다. `$SPOOL/bin/` 에 복사해 쓴다.
- [코드] 모뎀 설정에는 `FaxRcvdCmd`, `DynamicConfig`, `UseJobTSI: true` 세 줄이 있다. 서버 설정에는 `NotifyCmd`, `CoverCmd` 두 줄이 있다. `hfaxd.conf.snippet` 의 `JobFmt` 는 아래 4절의 열 순서 때문에 필요하다.
- [코드] 같은 기능이 `namifax faxrcvd|notify|dynconf|faxcover|cron|phb` 서브명령(`main.py`)으로도 있고, 이름은 원본 PHP 스크립트 이름(`faxrcvd.php` 등)을 `argv[0]` 로 맞춰 넘긴다.
- [코드] 모든 훅은 DB 세션을 직접 열고(`cli_session(ensure_schema=True)`) 끝나면 커밋하고 오류면 되돌린다. 훅이 웹 서비스와 **같은 DB** 를 봐야 한다(`/etc/namifax.env` 의 `DATABASE_URL`). [[database-and-migrations]]

### 1.1 `faxrcvd` (수신 완료)
- [코드] 인자: `file devID commID error-msg [CIDNumber] [CIDName] [DIDnum]`(최소 3개). 처리 순서: 모뎀 등록 확인(없으면 자동 생성) → 파일 있는지 → `faxinfo` → 보관 폴더 `<ARCHIVE>/YYYY/MM/DD/<번호>/<HylaFAX ID>/` 만들기 → `fax.tif` 복사 → PDF 변환 → 페이지 이미지·썸네일 → 주소록 조회/등록 → DID 라우팅(`ENABLE_DID_ROUTING`) → 받은 팩스함 입력 → (선택) OCR 색인 → 라우팅 우선순위(모뎀/DID → 주소록 Fax2Email → 바코드) → 메일 알림(PDF 첨부 또는 썸네일) → (선택) 프린터 출력. (`cli/faxrcvd.py`)
- [코드] 입력이 이상하면(파일 없음, `faxinfo` 실패) 로그만 남기고 종료 코드 0 으로 돌아온다: HylaFAX 쪽에서는 성공처럼 보인다.

### 1.2 `notify` (송신 결과)
- [코드] 인자: `qfile why jobtime [nextTry]`. `qfile` 은 HylaFAX 작업 파일이며 `totpages`, `status`, `external`, `jobid`, `mailaddr`, `groupid`, `owner`, `receiver`, `company`, `regarding` 등과 `postscript|pdf|tiff` 키의 파일 목록을 줄 단위로 읽는다. 작업 파일 형식에 대한 가정이므로 실제 `qfile` 과의 일치는 시험되지 않았다.
- [코드] `why` 에 따라 셋으로 나뉜다: `done`(보낸 팩스함에 `<SENT>/YYYY/MM/DD/<번호>/<HHMMSS>/<jobid>/` 로 PDF 생성·입력, 선택적으로 성공 메일), `blocked`/`requeued`(재시도 알림 메일), 그 밖(실패: PDF 를 만들어 실패 메일에 첨부). 보낸 사람은 `owner` 가 `FAXMAILUSER`/`WWWUSER` 이면 `mailaddr` 로 사용자를 찾고, 아니면 `owner` 이름으로 찾는다. 이것이 메일→팩스 사용자 식별의 기초다(§5).

### 1.3 `dynconf` (착신 거부)
- [코드] `dynconf device CallID1 ...` → SIP 접미사(`@host`)를 떼고 `DynamicConfig.lookup(device, callid)` 가 참이면 `RejectCall: true` 를 출력한다. 거부 대상이 아니면 아무것도 출력하지 않는다(설치 확인에 이 성질을 쓴다). 인자가 없으면 `EMPTY CALLID` 로 조회한다.

### 1.4 `faxcover` (표지)
- [코드] 명령줄 옵션을 읽어 사용자 계정 정보를 풀고 EPS/PS/HTML 표지 템플릿의 자리표시자를 치환해 표준 출력으로 내보낸다(`cli/faxcover.py`). HylaFAX 의 `CoverCmd` 가 이를 호출한다. 웹 폼 쪽은 표지만 보낼 때 `faxcover` 를 직접 불러 PS 를 만들고 그것을 `sendfax` 로 보낸다(§2).

## 2. 팩스 송신 계획 (`sendfax` 명령 구성)

- [코드] `services/sendfax_command.py::build_plan(request, sender, images_dir, tmp_dir, default_tsi)` 는 **무엇을 실행할지만 결정**한다(HylaFAX 불필요, 파일을 건드리지 않음). 결과 `Plan` = `steps`(실행할 `argv` 목록과 `stdout_to`), `files_to_write`, `cleanup`.
- [코드] 규칙 요약:
  - 파일도 표지도 없으면 `NothingToSend`.
  - 옵션 이름은 원본과 같다: `-o` 소유자, `-f` 보낸 메일, `-x` 받는 회사, `-c` 주석, `-r` 용건, `-y/-V` 받는 장소/전화, `-X/-Y/-U/-W` 보내는 회사/장소/전화/팩스, `-t` 재시도 횟수, `-k now + N <단위>`, `-S` TSI, `-P` 우선순위, `-a HH:MM` 예약. 값이 비면 옵션을 아예 뺀다.
  - 알림: 재큐 알림이면 `-R`, 아니면 `-D`. 표지: 있으면 `-C <images_dir>/<표지>`, 없으면 `-n`.
  - 모뎀: `-h <장치>@localhost`(`any` 이거나 비면 생략).
  - 수신처: 하나면 `-d [받는사람@]번호`; 세미콜론으로 여럿이면 문자 정화 후 임시 파일을 만들어 `-z <파일>`.
  - 표지 주소(주소·우편번호·도시)는 주석에 `{to-address:'..'}` 꼴로 실어 `faxcover` 가 다시 읽는다. `!` 는 `&#33;` 으로 바꾼다.
  - 파일 없이 표지만이면 `faxcover ... -p 0 -n <첫 번호>` 의 출력을 임시 `.ps` 로 저장하고 그것을 `sendfax -n` 으로 보낸다(`cleanup` 에 임시 파일).
- [코드] 인자는 **리스트**로 만들어 쉘을 거치지 않는다(폼 입력이 쉘 문법으로 해석되지 않음).
- [코드] 실행(`views/sendfax.py::dispatch_sendfax`): `sendfax` 는 `settings.binary("sendfax")` 로 찾고(`SENDFAX` 환경변수 → `BINARYDIR` → `PATH`), `faxcover` 는 `NAMIFAX_FAXCOVER` 가 있으면 그것, 없으면 `python -m namifax.cli.faxcover`. 하나라도 종료 코드가 0 이 아니면 출력 내용을 오류로 보여 주고, 성공이면 출력에서 `request id is <숫자>` 를 뽑아 작업 번호로 쓴다. 이 정규식은 HylaFAX 의 실제 출력에 대한 가정이다.
- [코드] 권한 규칙: 우선순위와 TSI 는 슈퍼유저만 바꿀 수 있다. 선(line) 선택은 사용자의 권한 목록과 `any_modem` 권한에 따른다. 업로드는 `upload_check` 로 크기·형식을 점검하고 임시 파일에 저장한 뒤 발송이 끝나면 지운다.
- [문서] [[hylafax-integration-architecture]] §10 의 "이미지는 PDF/PS 로 감싸고 오피스 문서는 LibreOffice 헤드리스 변환" 같은 첨부 처리는 위 코드에서 확인하지 못했다. 업로드 형식 판정은 `services/upload_check.py` 에 있으나 이 세션에서 읽지 않았다. [추정] 변환은 HylaFAX 의 `sendfax` 자체 변환(`pdf2fax` 등)에 맡긴다.

## 3. 수신 처리: TIFF→PDF, 썸네일, Ghostscript

- [코드] **TIFF→PDF**(`common/helpers.py::tiff2pdf`): 먼저 LibTIFF 의 `tiff2pdf -o` 를 10초 제한으로 시도하고, 실패하거나 없으면 Pillow 로 모든 쪽을 흑백 그대로 PDF 한 개로 저장한다. 해상도가 없으면 204x196dpi 로 가정하고, 가로세로 해상도가 10% 넘게 다르면 세로를 늘려 픽셀을 정사각형으로 만든다. 그래서 **수신 PDF 는 Ghostscript 없이도 만들어진다.**
- [코드] **썸네일/쪽 이미지**(`services/fax_images.py::render_previews`): `fax.tif` 가 있으면 Pillow 로 쪽마다 `page<N>.png`(폭 `PREV_SP`, 기본 750)와 첫 쪽의 `thumb.png`(폭 `PREV_TN`, 기본 80)를 만든다. 이것도 Ghostscript 가 필요 없다.
- [코드] **Ghostscript 가 필요한 곳**은 아래뿐이다. `settings.binary("gs")` 로 찾는다.
  1. 보낸 팩스처럼 **TIFF 가 없고 PDF 만 있는 폴더**의 쪽 이미지/썸네일(`render_pdf_previews`, `-sDEVICE=pnggray`). `gs` 가 없으면 0쪽을 돌려주고 미리보기가 없다.
  2. 송신 실패/완료 PDF 를 만들 때 **PostScript 입력**을 PDF 로 바꾸는 `convert2pdf`(`-sDEVICE=pdfwrite`). `gs` 가 없으면 `False` 를 돌려주고 notify 는 "PDF 만들기 실패" 메일로 갈음한다.
- [코드] 보관 폴더 구성: `fax.tif`, `fax.pdf`, `thumb.png`, `page0.png`...`page<N-1>.png`.

> 모순: [[hylafax-integration-architecture]] §5 는 쪽 이미지를 `preview0.png ... preview(N-1).png` 라고 적는다. 코드의 이름은 `page<N>.png` 다(`fax_images.PREVIMG = "page"`).

- [코드] 선택 기능: 바코드 해독(`bardecode`, 외부 도구 의존), OCR(`ocr_faxcontent` 와 `OcrService`, `settings.ocr_enabled()`), 팩스 번호 주석(`ENABLE_FAX_ANNOTATION`), G4 재압축(`TIFF_TO_G4`)은 설정으로 켠다. 이 세션에서 각 외부 도구의 설치 필요 조건은 `settings.binary()` 호출 지점만 확인했다.
- [코드·시험] `tests/unit/test_tiff2pdf_fallback.py`, `test_convert2pdf_*.py`, `test_archive_preview.py` 가 변환·미리보기를 검사한다. 시험에서는 `faxrcvd` 의 해당 단계가 `patch` 로 대체되므로 진짜 수신 TIFF 의 end-to-end 는 시험된 적이 없다.

## 4. 모뎀 상태와 대기열

- [코드] **모뎀 상태**(`services/modem.py`): `faxstat` 실행(5초 제한)의 출력을 `parse_faxstat_output` 이 장치별로 해석한다. 줄 첫 두 글자로 `Ru`(Running and idle → `modem-free`), `Se`(Sending job N → `modem-send`), `Re`(Receiving ... → `modem-recv`), 그 밖(`modem-wait`)을 나눈다. 명령이 실패하면 빈 결과가 되어 "Please wait" 로 표시한다. 화면 갱신은 `/ajax/modemstatus` 가 맡는다(`views/ajax.py`).
- [코드] **대기열**(`services/faxqueue.py`): 발송 대기 `faxstat -s`, 완료 `faxstat -d`(실패만 `s == "F"`), 취소는 `faxrm`, 변경은 `faxalter`. 출력 열은 `jid pri s owner mailaddr number pages dials tts status` 순서로 **공백 단위 토큰** 해석을 하며 마지막 열(status)은 남은 토큰을 이어 붙인다. 그래서 `deploy/hylafax/hfaxd.conf.snippet` 의 `JobFmt` 로 열 구성을 고정해야 한다. 다르면 목록이 어긋난다. [코드] 시험은 예시 문자열만 쓴다(§0).
- [코드] 관리자 대시보드의 HylaFAX 버전은 `faxstat -i` 출력에서 정규식으로 뽑는다(`services/hylafax_info.py`). 못 구하면 `None`(값을 지어내지 않는다).
- [코드] `FaxQueue.shell_exec` 은 `shell=True` 로 `faxstat` 명령을 실행한다. 명령 문자열은 코드 안의 고정값(생성자 기본값)이다.

> 모순: [[hylafax-integration-architecture]] 는 "실시간 모뎀 상태 조회(`faxstat` + TCP 4559)"라고 적는다. 코드에서 TCP 4559(`hfaxd` 포트) 소켓 접속은 찾지 못했다(`src/` 에서 `4559` 검색 결과 없음). 모뎀 상태와 대기열 모두 **`faxstat` 외부 프로세스 실행**으로만 구한다.

## 5. 메일 → 팩스 (Postfix)

- [문서] `deploy/postfix/setup-email2fax.md` ([[setup-email2fax]]): `fax.example.com` 도메인 메일을 Postfix `pipe` 서비스(`user=faxmail argv=/usr/bin/faxmail -d -n -NT ${user}`)로 HylaFAX `faxmail` 에 넘기고, `transport_maps` 로 도메인을 연결하고, `faxmail.conf` 를 설정한다. 이 저장소는 시스템 파일을 직접 고치지 않는 **설명서**일 뿐이며 자동 적용 스크립트가 없다. [코드] `deploy/postfix/` 에는 이 문서만 있다.
- [코드] NamiFAX 가 맡는 부분은 **소유자 식별**이다. `faxmail` 로 접수된 작업의 소유자는 `FAXMAILUSER`(기본 `faxmail`)이며, 대기열 표시와 `notify` 는 소유자가 `FAXMAILUSER` 또는 `WWWUSER`(기본 `www-data`)일 때 작업의 `mailaddr` 로 사용자를 찾아 그 사람의 팩스로 보여 준다. (`services/faxqueue.py::get_queue/list_owner`, `cli/notify.py`) `FAXMAILUSER` 를 Postfix 의 `user=` 와 같게 맞춰야 한다. [문서]
- 한계: 메일 수신 쪽(Postfix → `faxmail` → `sendfax`)은 NamiFAX 코드가 아니라 HylaFAX 의 `faxmail` 이며 이 저장소에서 시험된 적이 없다. [코드] NamiFAX 시험은 소유자 매핑 로직만 본다.

## 6. HylaFAX 사용자 동기화

- [코드] `HYLAFAX_USER_SYNC=1` 일 때만 켜지는 선택 기능(기본 꺼짐). 계정을 만들면 `sudo <PREFIX>/sbin/faxadduser -u <uid> -p <비밀번호> <이름>`, 지우면 `faxdeluser <이름>`, 비밀번호 변경은 삭제 후 재생성이다(HylaFAX 가 제자리 변경을 못 하기 때문). 쉘 없이 인자 리스트로 실행하고 실패는 기록만 하며 계정 변경은 막지 않는다. (`services/hylafax_users.py`)
- [코드] `deploy/sudoers.d/namifax`: 서비스 사용자(`uucp`)가 비밀번호 없이 실행할 수 있는 것은 `/sbin/reboot`, `/sbin/halt`(관리자 > 시스템 기능), `faxdeluser *`, `faxadduser -u * -p * *` 뿐이다.
- [문서] [[install-hylafax]]: `faxadduser` 가 비밀번호를 **명령줄 인자**로 받아 같은 서버의 다른 사용자가 `ps` 로 볼 수 있으므로 다른 사용자가 없는 전용 장비에서만 켠다. `systemd/namifax.service` 의 `NoNewPrivileges=true` 는 `sudo` 를 막으므로 이 기능에는 `false` 로 바꿔야 한다. [코드] 현재 서비스 파일은 `NoNewPrivileges=true` 이다.

> 모순: [[install-hylafax]] 와 `docs/INSTALL_HYLAFAX.md` 는 서비스 파일을 `deploy/systemd/` 에 있다고 쓰지만 저장소의 실제 위치는 최상위 `systemd/`(`namifax.service`, `namifax-scheduler.service`)다. `deploy/` 아래에는 `systemd` 폴더가 없다.

## 7. 주기 작업 배선

- [코드] 전화번호부 내보내기는 스케줄러의 `phonebook` 작업이 `export_phonebook()` 으로 하며 기본 경로는 `<HYLASPOOL>/etc/phonebook`(`PHONEBOOK` 설정으로 변경). HylaFAX 클라이언트 전화번호부 형식 `PBOOK1.1` 을 쓴다. 상세와 한계는 [[scheduler-and-storage]].
- [코드] 정리 작업(임시 폴더, 받은 팩스함 보관, 수명주기)의 배선은 두 갈래다. (1) 스케줄러: 웹 내장(`systemd/namifax.service` 의 `NAMIFAX_ENABLE_SCHEDULER=1`) 또는 별도 서비스(`systemd/namifax-scheduler.service`). (2) OS cron: `deploy/cron.d/namifax`(`namifax cron -t/-i/-d/-p/-s`; 기본으로 켜진 줄은 `-t 2` 하나).
- [코드] 두 서비스 모두 `User=uucp`, `ProtectSystem=full`, `ProtectHome=true`, `NoNewPrivileges=true`, `Restart=always`, `After=hylafax.service` 이다. 보관·임시 폴더는 훅을 실행하는 사용자와 웹 서비스 사용자가 모두 쓸 수 있어야 한다. `ProtectSystem=full` 은 `/usr`, `/boot`, `/etc` 를 읽기 전용으로 만들 뿐이므로 `/var/spool/hylafax` 쓰기는 막지 않는다. [추정] `/etc/namifax.env` 를 서비스가 읽는 방식(`EnvironmentFile`)은 서비스 파일에 보이지 않는다(훅 래퍼만 `. /etc/namifax.env` 를 읽음). 서비스가 환경 파일을 어떻게 받는지는 이 세션에서 확인하지 못했다.

## 8. 그 밖의 접점

- [코드] 설정 위치 변수: `HYLASPOOL`(기본 `/var/spool/hylafax`), `HYLAFAX_PREFIX`(기본 `/usr`), `BINARYDIR`, 프로그램별 변수(`GS`, `FAXINFO`, `SENDFAX`...), `AVANTFAX_ARCHIVE`(기본 `<HYLASPOOL>/archive`), `ARCHIVE_SENT`(기본 `<HYLASPOOL>/sent`), `PHONEBOOK`, `AVANTFAX_TMPDIR`. `common/settings.py`
- [코드] 가상 프린터(CUPS → 팩스)는 `cli/print_in.py`(`[[FAX: ...]]` 태그를 찾아 발송 큐에 올림)와 `services/printer.py` 에 있다. HylaFAX 와는 `sendfax` 경로를 공유한다. 이 세션에서 세부는 읽지 않았다.
- 레거시와의 차이와 알려진 결함은 [[porting-gaps]], [[migration-from-avantfax]], [[known-gaps-and-decisions]] 를 본다.

## 9. 문서-코드 차이 요약

1. TCP 4559 로 모뎀 상태를 읽는다는 설명은 코드에 없다. `faxstat` 프로세스 실행뿐(§4).
2. 쪽 이미지 이름은 `preview<N>.png` 가 아니라 `page<N>.png`(§3).
3. 서비스 파일 위치는 `deploy/systemd/` 가 아니라 `systemd/`(§6).
