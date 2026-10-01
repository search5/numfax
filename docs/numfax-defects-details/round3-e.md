# 3라운드 E: CLI, systemd, ini, babel, tailwind, package.json, golden_master 파일 단위 점검

## 읽은 파일과 줄 수 (src/namifax 기준, 저장소 루트는 numfax/)
- cli/__init__.py 1, cli/faxrcvd.py 267, cli/notify.py 311, cli/cron.py 121, cli/dynconf.py 59, cli/faxcover.py 185, cli/phb.py 85, cli/print_in.py 53, cli/user.py 82, cli/i18n.py 54, cli/populate_all_locales.py 122, cli/populate_ko.py 709(앞 40줄, 뒤 50줄 정독, 딕셔너리는 ast 로 전수 검사), cli/populate_missing_translations.py 91
- "import 계열": namifax/cli 에는 없고 main.py 가 위임하는 src/avantfax/cli 의 import_users.py 75, import_blacklist.py 52, import_archive.py 47, reroute.py 44, ocr_import.py 64, create_thumbnails.py 63, __init__.py 29
- 호출 경로: main.py 203, common/helpers.py 464(CLI 가 쓰는 함수 전체), services/scheduler.py 200, services/dynconf.py 앞 80줄
- systemd/namifax.service 27, systemd/namifax-scheduler.service 20, development.ini 59, production.ini 53, babel.cfg 6, tailwind.config.js 115, package.json 30
- golden_master/Dockerfile.legacy 8, runner.py 312, web_runner.py 244, test_e2e.py 18, test_web_e2e.py 20, extract_live_forms.py 96, extract_form_structure.py 80, apply_strict_form_contracts.py 134, generate_web_golden.py 1321(앞 60줄, 구조, 뒤 40줄), data/ 20건 전부, web/ meta 68건 전부
- 레거시 대조: includes/faxrcvd.php, notify.php, faxcover.php, dynconf.php, avantfaxcron.php, phb.php, langs/en.php(관련 키), functions.php(faxinfo, clean_faxnum, process_template, unaccent, avantfaxlog, mkdirs), config.php(기본값), DynamicConfig.php, tools/import_users.php, import_blacklist.php, reroute.php

실행 환경: NAMIFAX_DB_PATH 와 작업 디렉터리를 scratchpad/agent-r3-e/w 로 지정. HylaFAX 바이너리(faxinfo)는 같은 디렉터리의 가짜 스크립트로 대체. i18n 은 저장소를 건드리지 않도록 패키지를 복사한 i18nroot 에서만 실행. 저장소 소스는 수정하지 않았다.
이미 보고된 항목(COR-03 notify user.email, K13 attach_file, COR-16 토큰 접두어 치환, COR-08 DynConf, F1-03 faxinfo 더미 등)은 재현으로 확인만 하고 다시 적지 않았다.

## 결함 목록

### R3E-01 [중간] `namifax phb` 서브커맨드가 항상 argparse 오류로 종료됨 (종료코드 2)
- 위치: src/namifax/cli/phb.py:53 (`parse_args(argv[1:] if argv is not None else None)` 와 `main()` 이 `run_phb(sys.argv)` 호출), src/namifax/main.py:169-170 (`run_phb()` 에 sub_args 를 넘기지 않음)
- 증상: 통합 CLI 로 호출하면 sys.argv 가 ["namifax","phb",...] 라서 `phb` 문자열이 argparse 위치 인자로 해석되어 "unrecognized arguments: phb" 로 죽는다. `-o` 경로도 지정할 수 없다. USAGE 에 광고된 서브커맨드 중 하나가 동작하지 않는다. 별도 엔트리포인트 `namifax-phb` 는 정상.
- 재현: `python -m namifax.main phb -o x.txt` -> "usage: main.py ... error: unrecognized arguments: phb", rc=2. `namifax-phb -o x.txt` 는 파일 생성, rc=0.
- 확인 수준: 재현

### R3E-02 [높음] faxcover: 번들 표지 템플릿(cover.ps, 바이너리 포함)을 UTF-8 텍스트로 읽고 써서 출력이 손상됨
- 위치: src/namifax/cli/faxcover.py:54 (`open(..., "r", encoding="utf-8", errors="replace")`), :174 (`sys.stdout.write`)
- 증상: 저장소가 번들한 static/images/cover.ps(239,100바이트)와 cover-letter.ps 는 0xFF 등 비 UTF-8 바이트 10,811개를 포함한다(임베디드 이미지/폰트 데이터). 텍스트 모드 + errors="replace" 로 읽어 U+FFFD 로 치환한 뒤 UTF-8 로 다시 쓰기 때문에, 토큰이 하나도 없는 줄도 바이트가 바뀐다. 출력은 260,487바이트(21,387바이트 증가)이고 10,750곳이 EF BF BD 로 바뀌어 PS 바이너리 구간이 깨진다. 레거시는 file()/echo 로 바이트 그대로 통과시켰다. HylaFAX 가 이 출력을 ps2fax 로 넘기므로 기본 표지가 깨지거나 생성 실패한다. (COR-16 의 토큰 충돌, 비라틴 문자 미처리와는 별개 원인)
- 재현: `AVANTFAX_INSTALLDIR=<dir>` 아래 images/cover.ps 에 저장소의 cover.ps 를 복사하고 `namifax faxcover -f Bob -n 555 > out.ps`; `cmp out.ps cover.ps` 는 219721 번째 바이트에서 다름, U+FFFD 10,750개.
- 확인 수준: 재현

### R3E-03 [높음] faxcover: PostScript 문자열 정화/이스케이프가 없어 괄호, 백슬래시가 PS 구문을 깨고 PS 코드 주입이 가능함
- 위치: src/namifax/cli/faxcover.py:48-61 (process_template), :166-170 (comments), :117-140 (values)
- 증상: 레거시 process_template 은 모든 값을 unaccent() 로 통과시키며, 이 함수가 "(", ")", "\", "^" 를 제거한다(functions.php:1246-1252, 1338). 새 구현은 값을 그대로 `( ... )` 리터럴 안에 넣는다. 사용자가 입력한 regarding(-r), comments(-c), 수신자(-t) 에 짝이 안 맞는 ")" 가 있으면 PS 구문 오류로 표지 전체가 실패하고, 의도적인 입력이면 PS 연산자를 끼워 넣을 수 있다. 원인은 ADM-13(Cover Studio 렌더러)과 별개로 CLI 경로에 있다.
- 재현: 템플릿 `(Re: XXXX-regarding) show`, `-r "a) b"`, `-c "see ) pop (x"` -> 출력 `(Re: a) b) show`, `(see ) pop (x) show`. 실제 PS 주입 영향(file 연산자 등)은 gs 의 -dSAFER 설정에 좌우되므로 실행하지 않았다.
- 확인 수준: 재현(출력 구문 파괴), 추론(주입 영향)

### R3E-04 [중간] faxcover -C 가 확장자 제한 없이 임의 경로의 파일을 템플릿으로 읽어 그대로 출력함
- 위치: src/namifax/cli/faxcover.py:128-130 (`custom_c if os.path.exists(custom_c) else INSTALLDIR/images/custom_c`)
- 증상: 레거시는 확장자가 ps 또는 html/htm 인 파일만 표지로 받아들이고(faxcover.php:84-93) 그 외는 기본 표지로 폴백한다. 새 코드는 존재하는 모든 경로(절대경로, `../` 포함)를 읽어 내용을 출력에 싣는다. F2-11 에서 웹 폼 값이 -C 로 그대로 전달되는 것이 보고되어 있으므로, 사용자가 서버의 읽을 수 있는 임의 파일을 표지로 지정해 원격 수신자에게 전송되는 팩스에 포함시키는 경로가 된다. HTML 표지를 USE_HTML_COVERPAGE 설정과 무관하게 PS 경로로 처리하는 문제도 같은 원인이다.
- 재현: 임의 텍스트 파일 inst/notes.txt 에 `secret data XXXX-from` 를 넣고 `faxcover -f Bob -n 555 -C <절대경로>/notes.txt` -> "secret data Bob". `-C ../notes.txt` 도 동일. (무해한 자작 파일로만 확인)
- 확인 수준: 재현

### R3E-05 [중간] faxinfo 출력에 UTF-8 이 아닌 바이트가 있으면 전체 해석을 버리고 발신자 00000000, 현재 시각으로 접수함
- 위치: src/namifax/common/helpers.py:416-431 (`subprocess.run(..., text=True)` 와 `except Exception: pass`), 호출부 cli/faxrcvd.py:85-99
- 증상: text=True 는 strict 디코딩이라 CallID2(발신자 이름) 같은 필드에 Latin-1 바이트(예: "Müller" 의 0xFC, ISDN/CNAM 에서 흔함)가 있으면 UnicodeDecodeError 가 나고 광범위 except 가 삼킨다. 그러면 Pillow 폴백으로 넘어가 Sender="00000000", Received=현재 시각, CallID1="00000000" 이 된다. 실제 TSI, 수신 시각, 발신 번호가 모두 사라지고 보관 경로가 `.../<오늘>/00000000/` 이 된다. F1-03 은 "해석 실패 일반" 이고 이 항목은 인코딩이라는 구체적 원인이다. 같은 위치의 timeout=5 초 초과도 같은 경로로 떨어진다. 레거시는 exec() 로 바이트를 문자열로 받아 파싱했다.
- 재현: 가짜 faxinfo 가 `CallID2: M\374ller` 를 출력하도록 하고 faxrcvd 실행 -> 보관 경로 `archive3/2026/10/01/00000000`(원래 기대값 2024/03/05/8225551234). `faxinfo()` 직접 호출 결과 `{'Sender':'00000000','Pages':2,'Received':'2026:10:01 08:48:38','CallID1':'00000000'}`.
- 확인 수준: 재현

### R3E-06 [낮음] clean_faxnum 이 영문자, 밑줄을 제거해 레거시와 다른 번호가 저장됨
- 위치: src/namifax/common/helpers.py:49-53 (`[^\d+]`), 사용처 cli/notify.py:106-109 (external), cli/faxrcvd.py:116
- 증상: 레거시는 `[^\+\w]` 만 제거해 문자, 숫자, 밑줄, + 를 유지한다(functions.php:189-192). 새 구현은 숫자와 + 만 남긴다. qfile 의 external 에 다이얼 지정 문자(W, P 등)나 영문 식별자가 있으면 값이 바뀌어 주소록 조회 키, 보관 디렉터리명, 발신 목록 번호가 레거시와 달라진다. 영문 TSI/CallerID("ANONYMOUS" 등)는 빈 문자열이 되어 faxrcvd 디렉터리가 `unknown` 으로 합쳐진다.
- 재현: qfile `external:0W02-555-1234` -> notify 출력 `external: 0025551234` (레거시 기대값 0W025551234). 보관 경로 `.../sent/2026/10/01/0025551234/...`.
- 확인 수준: 재현

### R3E-07 [낮음] `i18n init -l <이미 있는 로케일>` 이 기존 번역 카탈로그를 경고 없이 빈 카탈로그로 덮어씀
- 위치: src/namifax/cli/i18n.py:47-52
- 증상: pybabel init 은 대상 .po 가 있어도 덮어쓴다. 존재 여부 확인, 확인 요청, --force 구분이 없어 오타 한 번으로 번역 전체가 사라진다(종료코드 0).
- 재현: 복사본에서 `i18n init -l ko` 실행 -> ko namifax.po 의 번역된 msgstr 530개 중 0개(전부 공백). 기존 ko 는 전부 번역 상태였다.
- 확인 수준: 재현

### R3E-08 [낮음] `i18n update -l ko` 가 -l 을 무시하고 24개 로케일을 모두 갱신하며, 퍼지 매칭을 기본으로 켜 둠
- 위치: src/namifax/cli/i18n.py:43-45 (`-l` 미전달), :27-31 (도움말은 "Locale code for init or update")
- 증상: 도움말과 달리 update 에서 -l 이 쓰이지 않아 한 로케일만 갱신할 수 없다. 또 `--no-fuzzy-matching`, `--ignore-obsolete` 없이 호출하므로 새 문자열마다 유사 문자열의 번역이 fuzzy 로 붙는다(UI-10 의 fuzzy 100건과 UI-13 오역의 재생산 원인). 같은 update 는 깨진 헤더("Project-Id-Version: NamiFAX 4.0.Language: kMIME-Version...", UI-38)도 그대로 유지한다.
- 재현: `i18n update -l ko` 출력에 cs, bg, ar 등 다른 로케일 "updating catalog" 줄이 나옴. 실행 후 ko 는 fuzzy 20, 미번역 54, de 는 fuzzy 100 -> 116.
- 확인 수준: 재현

### R3E-09 [낮음] `i18n extract` 가 절대 경로 위치 주석과 자리표시자 헤더를 만들고 커밋된 .pot 와 크게 어긋남
- 위치: src/namifax/cli/i18n.py:30,35-37 (`root_dir` 절대경로를 입력 디렉터리로 전달, --project/--version/--copyright-holder 없음)
- 증상: 생성된 .pot 의 "#:" 위치 주석이 `/home/<사용자>/.../templates/x.jinja2:13` 형태의 기계 고유 절대경로이고, 헤더가 "Translations template for PROJECT", "PROJECT VERSION", "ORGANIZATION", "FIRST AUTHOR", 헤더 fuzzy 플래그이다. 실행할 때마다 전 줄이 바뀌는 diff 가 되고(복사본 기준 975줄 추가, 650줄 삭제), 입력이 저장소 루트 전체라 .venv 와 node_modules 를 훑는다. 커밋된 .pot(456개 msgid)은 현재 소스 추출 결과(530개)보다 74개 적어 이미 낡았다(UI-05 의 누락 문자열과 같은 현상의 원인).
- 재현: 복사본에서 `i18n extract`; 헤더와 "#:" 줄 확인, msgid 수 456 대 530.
- 확인 수준: 재현

### R3E-10 [낮음] populate_missing_translations.py 는 CWD 와 존재하지 않는 scratch/ 에 의존하고 실패해도 종료코드 0
- 위치: src/namifax/cli/populate_missing_translations.py:12-13 (상대경로 LOCALE_DIR, SCRATCH_DIR), :63-70 (compile 실패 시 False 반환), :90-91 (`populate()` 반환값 무시)
- 증상: 저장소에 scratch/ 디렉터리도, 입력 JSON 을 만드는 스크립트도 없어 실행할 수 없다. 다른 디렉터리에서 실행하면 경로가 어긋나고, "No translation JSON files found" 나 "Compile failed" 이어도 종료코드 0 이다. populate_all_locales.py 는 .po/.mo 를 백업 없이 제자리에서 덮어쓰며 PHP 의 여러 줄 문자열(NEW_USER_MESSAGE, NEWPASS_MSG)과 FAX_WHY, MONTHS 배열은 정규식이 못 읽어 건너뛴다(파서 :41).
- 재현: 저장소 밖 디렉터리에서 실행 -> "No translation JSON files found in scratch/." rc=0. legacy langs/de.php 에서 정규식 미매치 줄 35개(FAX_WHY 12, MONTHS 13, 여러 줄 메시지 등) 목록화.
- 확인 수준: 재현

### R3E-11 [중간] import_users: 비 UTF-8 입력이 조용히 깨지고, 탭이 아닌 줄은 오류 없이 건너뜀
- 위치: src/avantfax/cli/import_users.py:32 (`errors="ignore"`), :54-56 (`len(parts) < 4: continue`); import_blacklist.py:106 (같은 `errors="ignore"`)
- 증상: 한국어 Windows 에서 만든 CP949 텍스트 파일은 바이트가 버려져 이름이 "ȫ浿" 처럼 깨진 채 "User details saved" 로 성공 보고된다. 탭 대신 공백으로 구분한 줄은 아무 메시지 없이 무시되고 종료코드 0 이다(레거시는 explode 후 생성을 시도해 get_error() 로 사유를 출력). language 기본값도 레거시의 $dft_config_lang 이 아니라 "en" 고정이고 from_company 등 기본 필드가 빠진다.
- 재현: `import-users u_cp949.txt` -> `user> ȫ浿: User details saved`, DB name='ȫ浿'. `import-users u_spaces.txt` -> 출력 없음, rc=0, 계정 미생성.
- 확인 수준: 재현 (참고: 이 서브커맨드들은 COR-25 대로 wheel 에 없는 avantfax 트리를 쓴다)

### R3E-12 [낮음] cron 인자 검증이 옵션마다 제각각이고 끊어진 심볼릭 링크는 영원히 정리되지 않음
- 위치: src/namifax/cli/cron.py:67-74, 94-101, 104-111
- 증상: (a) `-i abc` 나 `-d abc` 는 ValueError 트레이스백과 종료코드 1 로 죽고 그 전에 아무 정리도 하지 않는다. `-t abc`, `-t 1.5` 는 사용법 출력 후 0, `-p abc` 는 조용히 무시한다. (b) 임시 디렉터리 정리에서 `os.path.getmtime` 이 끊어진 링크에서 OSError 를 내면 `except OSError: pass` 로 삼켜 그 항목은 영구히 남는다(레거시는 "Stat error" 출력). 디렉터리를 가리키는 심볼릭 링크는 rmtree 가 거부하는데 ignore_errors=True 라 역시 조용히 남는다. (c) 반올림이 파이썬 banker's rounding 이라 2.5일 된 파일이 `-t 3` 에서 지워지지 않는다(PHP round 는 3).
- 재현: tmp 에 dangling 링크와 디렉터리 링크를 두고 `cron -t 0` -> 둘 다 남고 출력 없음, rc=0. `cron -t 2 -i abc` -> ValueError, rc=1.
- 확인 수준: 재현 ((c)는 추론)

### R3E-13 [낮음] faxcover: -z 가 0 이거나 숫자가 아니면 트레이스백으로 죽어 표지가 생성되지 않음
- 위치: src/namifax/cli/faxcover.py:166-168
- 증상: `int(opt_dict.get("-z", ...))` 와 `textwrap.wrap(width=0)` 가 검증 없이 ValueError 를 낸다. 표지 출력이 비고 종료코드 1 이라 sendfax 의 표지 생성이 실패한다. 레거시 wordwrap 은 오류 없이 넘어간다.
- 재현: `faxcover -f Bob -n 555 -c "hello world" -z 0` -> "ValueError: invalid width 0 (must be > 0)", rc=1. `-z abc` 도 동일.
- 확인 수준: 재현

### R3E-14 [낮음] 보관 디렉터리/파일 권한이 레거시와 다름: 디렉터리 0755, fax.tif 는 원본의 0600 을 상속
- 위치: src/namifax/common/helpers.py:141-147 (mkdirs, umask 적용), src/namifax/cli/faxrcvd.py:118, :125 (`shutil.copy2`)
- 증상: 레거시 mkdirs 는 생성 후 chmod 0777 을 명시하고(functions.php:775-790), TIFF 는 tiffcp 가 새 파일로 만든다. 새 구현은 umask 022 에서 디렉터리가 0755 가 되어 다른 계정(웹 서버가 uucp 가 아닌 배포)이 삭제/회전/갱신할 수 없고, copy2 가 recvq 원본의 모드(HylaFAX 기본 0600)를 복사해 fax.tif 만 0600 이 되고 PDF/썸네일은 0644 라 권한이 섞인다. 제공된 systemd 유닛은 웹과 훅이 모두 uucp 라 그 배포에서는 드러나지 않는다.
- 재현: `umask 022` 에서 원본을 chmod 600 한 뒤 faxrcvd 실행 -> 디렉터리 755, fax.tif 600, 나머지 644.
- 확인 수준: 재현

### R3E-15 [낮음] 알림 메일 문구가 레거시와 다르고, 보관 등록 실패 시 본문에 "fax id: None" 이 찍힘
- 위치: src/namifax/cli/notify.py:44, 46-59 (LANG), src/namifax/cli/faxrcvd.py:51-55, 246
- 증상: 레거시 en.php 는 FAX_FAILED="Problem sending the fax.", FAX_WHY 는 소문자("format failed", "timed out", "requeued" 등), COMPANY_EXISTS="Company name already exists" 이다. 새 구현은 "Fax transmission failed", "Format Failed", "Timed Out", "Company already exists" 로 바꿔 제목과 본문이 달라져 메일 필터/규칙이 어긋난다. faxrcvd 는 ArchiveIn.create 실패 시 faxid=None 이 f-string 으로 "fax id: None" 이 되고(레거시는 빈 값) 실패 로그도 남기지 않는다.
- 재현: 코드 대조(en.php:313-327 대 notify.py:44-59). faxrcvd 는 faxid=None 경로를 코드로 확인.
- 확인 수준: 추론

### R3E-16 [낮음] dynconf CLI 에 로그가 전혀 없고 DB 오류는 트레이스백으로 종료됨
- 위치: src/namifax/cli/dynconf.py:30-52 (avantfaxlog 호출 없음)
- 증상: 레거시는 "dynconf> checking CallID1 ... on device ..." 와 "dynconf> rejecting ..." 를 SysLog 에 남겨 관리자가 차단된 호출을 화면에서 확인할 수 있었다. 새 구현은 차단해도 흔적이 없다. DynamicConfig() 나 lookup 이 예외를 내면 try 없이 트레이스백과 종료코드 1 로 끝나므로 HylaFAX 가 빈 응답을 받은 것과 구분되지 않는다(레거시는 DB 오류를 로그하고 계속).
- 재현: 코드 대조. 규칙이 있어도 "RejectCall: true" 외에 로그 호출이 없음.
- 확인 수준: 추론

### R3E-17 [낮음] CLI 스크립트 실행 비트가 제각각이라 경로 지정 실행이 일부만 가능함
- 위치: src/namifax/cli/ (cron.py, dynconf.py, phb.py 만 755, faxrcvd.py, notify.py, faxcover.py, print_in.py, user.py, i18n.py 는 644)
- 증상: 전 파일에 `#!/usr/bin/env python3` shebang 이 있고 레거시는 스크립트 경로를 HylaFAX 와 CUPS 설정에 직접 적었지만, faxrcvd, notify, faxcover, print_in 은 실행 권한이 없어 "Permission denied" 가 난다. 또 shebang 이 시스템 python3 라 venv 의존성(Pillow, APScheduler, pyramid)을 못 찾는다. print_in 은 CUPS 백엔드로 쓰려면 실행 가능해야 하지만 엔트리포인트도 없다(COR-26).
- 재현: `ls -l src/namifax/cli/*.py`
- 확인 수준: 재현

### R3E-18 [낮음] createuser: 비밀번호가 명령행 인자라 ps 에 노출되고, 길이와 이메일 형식 검증이 없음
- 위치: src/namifax/cli/user.py:20-22 (`-p/--password`, `-e/--email`), :67 (create 호출)
- 증상: getpass, 환경변수, 표준입력 입력 수단이 없어 비밀번호가 프로세스 목록과 셸 히스토리에 남는다. 서비스 계층이 username 형식과 이메일 중복은 검사하지만 최소 길이와 이메일 형식은 검사하지 않아 1자 비밀번호와 "bad email" 이 그대로 저장된다(F3-25 의 관리자 화면 항목과 같은 계열의 CLI 경로). 기본 비밀번호 공개(F5-14)와는 별개.
- 재현: `createuser -u bob -p a -e "bad email" --user-only` -> "Created user 'bob' ... successfully", rc=0.
- 확인 수준: 재현

### R3E-19 [낮음] golden_master/runner.py: 빈 인자가 사라지고, 셸 인용이 없으며, 이미지를 빌드하지 않고, docker 실패를 골든으로 기록함
- 위치: golden_master/runner.py:197-199 (`" ".join(f'"{arg}"' if " " in arg else arg ...)`), :201-210 (run_legacy 가 반환코드 미검사), :235-240 (record 가 그대로 저장); golden_master/Dockerfile.legacy
- 증상: (a) 빈 문자열 인자는 공백이 없어 따옴표 없이 사라지므로 02_dynconf_empty_callid 의 레거시 실행은 `dynconf.php ttyS0` 로 실행되어 "빈 CallID" 를 검증하지 않는다. 공백 외 셸 메타문자도 인용하지 않는다(shlex.quote 아님). (b) 이미지 태그 avantfax-legacy-test 를 만드는 명령이 저장소 어디에도 없고(ARCHITECTURE.md 는 파일 이름만 언급), Dockerfile.legacy 는 이름이 기본값이 아니라 -f 가 필요하다. (c) 이미지가 없으면 docker 가 종료코드 125 와 stderr 를 내는데 record 가 이를 골든(exit_code.txt=125, stderr)으로 저장해 기존 정상 골든을 덮어쓴다. (d) Dockerfile.legacy 에는 MySQL 서버, local_config.php, tiffcp/tiff2pdf/ghostscript 가 없어 16_create_thumbnails("No faxes found", DB 조회 필요) 같은 골든이 이 이미지로 재현되지 않는다. 바인드 마운트로 컨테이너(root)가 저장소에 root 소유 파일을 만들 수도 있다.
- 재현: (a) 문자열 조합 로직 확인(02 시나리오는 `" ".join` 결과 끝에 인자가 없음). (b)-(d) 코드, 파일 대조.
- 확인 수준: 재현 ((a)), 추론 ((b)-(d), docker 를 실제로 실행하지 않음)

### R3E-20 [낮음] generate_web_golden.py 는 50건만 만들고 meta 를 덮어써 수작업 필드가 사라지며, web_runner 검증이 느슨함
- 위치: golden_master/generate_web_golden.py:1296-1315 (meta 에 id, description, route, method, expected_status, implemented 만 기록), golden_master/web_runner.py:146-157 (required_text 를 raw HTML 까지 포함해 매칭), :160-165 (required_links 는 any 매칭)
- 증상: web/ 에는 68건이 있는데 생성기는 W01-W50 만 안다. 생성기를 다시 돌리면 W04_inbox_empty 의 authenticated, W68 의 authenticated 와 headers, 6건의 scenario_id/params 가 사라지고 W51-W68 18건은 재생성 수단이 없다. required_text 는 스크립트, 속성, 주석에 있어도 통과하므로 화면에 보이지 않는 문자열만으로 성공한다. (F5-06 의 "자기 참조" 와는 별개의 재현성, 검증력 문제)
- 재현: meta.json 68개의 키 집계(authenticated 2건, headers 1건, scenario_id 6건, params 4건), 생성기 SCENARIOS 50건.
- 확인 수준: 재현

### R3E-21 [낮음] ini 파일: 개발 설정이 모든 인터페이스에 바인딩되고, 운영 설정에 waitress 제한값이 없음
- 위치: development.ini:27 (`listen = 0.0.0.0:6543`, reload_templates=true), production.ini:21 (`listen = *:6543`, waitress 옵션 없음)
- 증상: Pyramid 스캐폴드 기본은 localhost 인데 개발 ini 가 0.0.0.0 으로 열려 있어, K10 의 하드코딩 admin/password 우회 로그인이 켜진 채로 네트워크 전체에 노출된다. production.ini 는 threads, max_request_body_size(waitress 기본 1 GiB), channel_timeout, 프록시 신뢰 설정(trusted_proxy, url_scheme)을 지정하지 않아 업로드 제한(F2-09)과 리버스 프록시 뒤의 URL/리다이렉트 스킴이 기본값에 맡겨진다.
- 재현: ini 대조(pserve 로 기동해 waitress 기본값을 확인하지는 않음).
- 확인 수준: 추론

### R3E-22 [낮음] systemd 유닛에 PYTHONUNBUFFERED 가 없어 `serve` 의 시작 안내가 journald 에 남지 않음
- 위치: systemd/namifax.service:14 (ExecStart namifax serve), src/namifax/main.py:80, 88 (print), systemd/namifax-scheduler.service:11
- 증상: stdout 이 파이프/파일이면 파이썬이 블록 버퍼링을 하므로 "[*] Starting NamiFAX Web Service ..." 와 "[*] In-process APScheduler started." 가 기동 직후 보이지 않고, SIGTERM(systemctl stop)으로 끝나면 버퍼가 플러시되지 않아 영영 사라진다. `serve` 는 logging 설정이 없어(F5-19 (d)) 기동 기록이 유닛 로그에 전혀 남지 않는다.
- 재현: stdout 을 파일로 리다이렉트해 `serve --port 18653` 기동, HTTP 200 확인 후 SIGTERM -> srv.out 0바이트(access log 는 stderr 로만 나옴).
- 확인 수준: 재현

## 새로 적지 않은 것(이미 보고된 항목과 겹침)
- tailwind.config.js, package.json, babel.cfg: content 경로와 설정 자체에서 새 결함을 찾지 못했다. 스타일 누락은 UI-04, 라이선스 표기는 F5-21. babel.cfg 의 패턴(`src/namifax/**.py`, `templates/**.jinja2`)은 실제 추출에서 정상 동작했고 템플릿은 `_()` 만 쓰며 `{% trans %}` 는 없어 jinja2.ext.i18n 설정 문제는 없다.
- .po/.mo 동기화와 자리표시자(%(x)s, %s, {}) 불일치: 24개 로케일 모두 0건(불일치 없음, po 와 mo 내용 일치). populate_ko.py 딕셔너리 587개 키에 중복 키와 자리표시자 불일치 없음.
- systemd: 이중 기동(COR-23), DB/WorkingDirectory(F5-20), 포트와 인자(COR-23, F5-23) 외의 새 항목은 위 R3E-22 뿐.
- faxrcvd/notify 의 DB 경로(COR-13), 미동작 훅 기능(COR-20, F4-17, F4-18), 메일 미발송(COR-04), 첨부 TypeError(K13), user.email 오류(COR-03)는 재현으로 확인만 했다. notify 'rejected' 경로는 K13 TypeError(rc=1) 후 임시 디렉터리(`TMPDIR/날짜-번호-시각-jobid/fax.pdf`)가 남는 것까지 확인했다(정리는 cron -t 가 나중에 수행).
