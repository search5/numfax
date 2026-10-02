---
title: 실행·배포·운영 점검
type: topic
updated: 2026-10-02
sources: [src/namifax/main.py, src/namifax/__init__.py, src/namifax/db/provider.py, src/namifax/db/bootstrap.py, src/namifax/origin_guard.py, src/namifax/common/passwords.py, src/namifax/common/secretbox.py, src/namifax/common/settings.py, src/namifax/services/scheduler.py, src/namifax/services/scheduler_config.py, src/namifax/services/sysfunc.py, src/namifax/views/sendfax.py, src/namifax/services/upload_check.py, src/namifax/cli/cron.py, development.ini, production.ini, pyproject.toml, systemd/namifax.service, systemd/namifax-scheduler.service, deploy/nginx/namifax.conf, deploy/apache/namifax.conf, deploy/cron.d/namifax, deploy/sudoers.d/namifax, deploy/postfix/setup-email2fax.md, deploy/hylafax/, "[[install-hylafax]]", "[[operations-checklist]]", "[[setup-email2fax]]"]
verified: true
---

실행 방법, 환경 변수, 배포 파일, 설치 후 점검 순서를 코드와 배포 파일을 직접 열어 대조해 정리한 페이지.
근거 문서는 [[install-hylafax]] 와 [[operations-checklist]]. 관련: [[overview]] [[scheduler-and-storage]] [[hylafax-integration]] [[authentication-and-security]] [[migration-from-avantfax]] [[known-gaps-and-decisions]].
이 저장소에서는 실제 HylaFAX 서버에 붙여 시험하지 못했다(아래 "확인하지 못한 것").

## 1. 실행 방법

### 1.1 `namifax serve` (systemd 단위가 쓰는 방식)
- [코드] `pyproject.toml` 의 `[project.scripts]` 가 `namifax`(`namifax.main:main`)와 `namifax-server`, `namifax-scheduler`, `namifax-createuser`, `namifax-dynconf`, `namifax-faxrcvd`, `namifax-notify`, `namifax-faxcover`, `namifax-cron`, `namifax-phb` 를 만든다.
- [코드] `namifax serve`(`src/namifax/main.py` 의 `serve_main`)는 순서대로 (1) `resolve_database_url` 로 DB 주소를 정해 `ensure_schema` 실행, (2) `NAMIFAX_ENABLE_SCHEDULER` 가 `1`/`true`/`True`(기본 `1`)면 프로세스 안에서 APScheduler 시작, (3) `create_app()` 으로 Pyramid 앱 생성(실패하면 메시지를 stderr 에 내고 종료 코드 1, 다른 앱으로 대체하지 않음), (4) 표준 라이브러리 `wsgiref` 의 `ThreadingWSGIServer`(스레드 서버)로 `--host`/`--port`(기본 환경 변수 `NAMIFAX_HOST` 0.0.0.0, `NAMIFAX_PORT` 8000)에 바인딩한다.
- [코드] 이 서버는 `waitress` 가 아니라 `wsgiref` 다. 프로세스는 하나이고 워커 개수 설정이 없다.
- [추정] `wsgiref` 는 표준 라이브러리의 참고 구현이라 부하·보안 면에서 전용 WSGI 서버보다 약하다. 운영에서 문제가 되는지는 측정하지 못했다. 사람이 판단할 항목(5절)에 올린다.

> 모순: [[install-hylafax]] 는 "HTTPS 사용 시 `session.secure = true`" 로 안내하지만, `namifax serve` 는 `create_app()` 을 설정 없이 호출한다(`src/namifax/main.py`). 그래서 ini 의 `session.secure`, `session.secret`, `secret.key`, `csrf.trusted_origins`, `demo.data` 는 이 경로에서 읽히지 않는다. 읽는 코드는 `settings.get(...)` 뿐이다(`src/namifax/__init__.py`, `origin_guard.py`, `db/bootstrap.py`). `session.secure` 에 대응하는 환경 변수는 코드에 없다. 보안 쿠키 표시를 켜려면 아래 1.2 의 `pserve` 경로를 써야 한다.

### 1.2 `pserve` + ini 파일
- [코드] `development.ini`, `production.ini` 는 `use = egg:namifax`(`pyproject.toml` 의 `paste.app_factory` 진입점)와 `waitress` 서버를 쓴다. `development.ini` 는 `0.0.0.0:6543`, `pyramid.reload_templates = true`, 로그 DEBUG. `production.ini` 는 `*:6543`, `reload_templates = false`, 로그 WARN.
- [코드] 두 ini 모두 `session.secret`, `session.secure`, `csrf.trusted_origins`, `secret.key`, `sqlalchemy.url` 줄이 없거나(`sqlalchemy.url` 은 주석 처리) 비어 있다. 이 값들을 쓰려면 `[app:main]` 에 직접 추가해야 한다.
- [코드] 이 경로로 `pserve production.ini` 를 실행하면 `ensure_schema` 는 `create_app` 안에서 돈다. 내장 스케줄러는 시작하지 않는다(스케줄러 시작은 `serve_main` 에만 있음). `namifax scheduler` 를 따로 띄워야 한다.
- [코드] `pserve` 가 `waitress`, `plaster_pastedeploy` 를 쓰는 점은 `pyproject.toml` 의 의존성 목록으로 확인했다. 저장소의 systemd 단위와 nginx/apache 파일은 이 경로를 쓰지 않는다(8000 포트, `namifax serve`).

### 1.3 스케줄러
- [코드] `namifax scheduler`(`run_scheduler_standalone`)는 APScheduler 를 블로킹으로 돌린다. `systemd/namifax-scheduler.service` 가 이것을 서비스로 만든다. `namifax.service` 는 `NAMIFAX_ENABLE_SCHEDULER=1` 로 웹 프로세스 안에서 돌린다. 둘을 함께 켜면 같은 작업이 두 번 돌 수 있는지는 확인하지 못했다. 작업 단위 중복 방지는 프로세스 안 잠금(`claim`)이라 프로세스를 가로지르지는 않는다 [코드: `src/namifax/services/scheduler.py`]. 따라서 둘 중 하나만 켜는 쪽이 안전하다 [추정].
- [코드] 스케줄러 작업은 4개다(`scheduler_config.JOBS`): `tmp`(임시 폴더 정리, 기본 켬 00:00 1일), `inbox`(받은 팩스함 → 보관함 이동, **기본 꺼짐** 01:00 30일), `lifecycle`(Admin > Storage 에 저장한 보존 정책, 정책이 저장돼 있을 때만 실제로 지움), `phonebook`(주소록을 HylaFAX 로 내보내기, 60분).

> 모순: [[install-hylafax]] 와 [[operations-checklist]] 는 "내장 스케줄러는 임시 파일 정리만 한다"고 쓴다. 코드에는 `inbox`(받은 팩스함 보관 이동)와 `lifecycle`(저장 정책 실행), `phonebook` 작업도 있다(`src/namifax/services/scheduler.py` 의 `_run_claimed`). 다만 `inbox` 는 기본이 꺼짐이고, 보관함 안의 오래된 팩스를 날짜로 **삭제**하는 `namifax cron -d` 에 해당하는 스케줄러 작업은 없다(`lifecycle` 의 저장 정책이 있을 때만 삭제). 그래서 "cron 에 -i/-d 를 써야 한다"는 안내는 `-d` 에 관해서는 여전히 유효하다 [코드: `src/namifax/cli/cron.py` 에 `-t -i -d -p -s` 옵션].

## 2. 환경 변수

### 2.1 `NAMIFAX_*` 전체 (코드·배포 파일 grep 결과, 2026-10-02)
| 변수 | 기본값 | 용도 | 근거 |
|---|---|---|---|
| `NAMIFAX_HOST` / `NAMIFAX_PORT` | `0.0.0.0` / `8000` | `namifax serve` 바인딩 | `src/namifax/main.py` |
| `NAMIFAX_ENABLE_SCHEDULER` | `1` | 웹 프로세스 안 스케줄러 | `src/namifax/main.py` |
| `NAMIFAX_SESSION_SECRET` | 없음(프로세스마다 임의 키 + 경고 로그) | 2FA·패스키 중간 단계 쿠키 서명 | `src/namifax/__init__.py` |
| `NAMIFAX_SECRET_KEY` | 없음 | SMTP 비밀번호·클라우드 키·2FA 시드 암호화(Fernet 계열) | `src/namifax/common/secretbox.py` |
| `NAMIFAX_PASSWORD_HASH` | `argon2` | `md5` 면 새 비밀번호를 원본 형식으로 저장 | `src/namifax/common/passwords.py` |
| `NAMIFAX_ARGON2_TIME_COST` / `_MEMORY_COST` / `_PARALLELISM` | 라이브러리 기본 | Argon2id 비용 조정(양의 정수만 인정) | `src/namifax/common/passwords.py` |
| `NAMIFAX_DB_PATH` | 현재 폴더의 `namifax.db` | SQLite 파일(`DATABASE_URL`, `AFDB_URL` 이 없을 때) | `src/namifax/db/provider.py` |
| `NAMIFAX_DEMO_DATA` | 꺼짐 | 데모 데이터. 새 SQLite DB 에서만 동작, 다른 DB 에서는 경고 후 무시 | `src/namifax/db/bootstrap.py` |
| `NAMIFAX_NEW_USER_PASSWORD` | 없음 | `namifax createuser` 의 비밀번호(`-p` 가 없을 때) | `src/namifax/cli/user.py` |
| `NAMIFAX_DEFAULT_LANGUAGE` | `en` | `import-users` 로 만든 계정의 언어 | `src/namifax/cli/import_users.py` |
| `NAMIFAX_ARCHIVE_DIR` | `/var/spool/hylafax/archive` | 클라우드 스토리지·보존 정책이 보는 보관 폴더 | `src/namifax/services/cloud_storage.py`, `storage_lifecycle.py` |
| `NAMIFAX_TMPDIR` | 시스템 임시 폴더 | 인쇄 작업 임시 파일 | `src/namifax/services/printer.py` |
| `NAMIFAX_MAX_UPLOAD_BYTES` | 10 MiB | 팩스 업로드 크기 한도(양의 정수만 인정) | `src/namifax/services/upload_check.py` |
| `NAMIFAX_FAXCOVER` | `python -m namifax.cli.faxcover` | 표지 생성 실행 파일 | `src/namifax/views/sendfax.py` |
| `NAMIFAX_QUEUE_SIMULATION` | 미지정 | `1/true/yes` 면 전송을 흉내냄. 미지정이면 pytest 실행 중이거나 `/var/spool/hylafax` 가 없을 때 흉내냄 | `src/namifax/views/sendfax.py` |
| `NAMIFAX_REBOOT_CMD` / `NAMIFAX_SHUTDOWN_CMD` | `sudo /sbin/reboot` / `sudo /sbin/halt` | 관리자 > 시스템 기능의 재부팅·종료 명령 | `src/namifax/services/sysfunc.py` |
| `NAMIFAX_HOME` | `/opt/namifax` | 훅 스크립트가 가상환경 위치를 찾을 때만 씀 | `deploy/hylafax/bin/*` |

- [코드] `NAMIFAX_QUEUE_SIMULATION` 이 미지정이고 서버에 `/var/spool/hylafax` 가 없으면, `sendfax` 실행 파일이 없을 때 **전송이 성공한 것처럼 가짜 작업 번호를 돌려준다**(`views/sendfax.py` 의 `dispatch_sendfax`). HylaFAX 가 없는 개발 장비를 위한 동작이다. 운영에서는 `sendfax` 가 `PATH` 에 있는지 점검 순서(4절)에서 확인해야 한다.

### 2.2 원본 이름을 그대로 쓰는 설정(NAMIFAX_ 접두사 없음)
- [코드] `DATABASE_URL`(없으면 `AFDB_URL`, 그다음 `NAMIFAX_DB_PATH`) 순서로 DB 를 정한다(`src/namifax/db/provider.py`). ini 의 `sqlalchemy.url` 이 있으면 그것이 먼저다.
- [코드] `src/namifax/common/settings.py` 의 `flag/text/number` 와 `os.environ` 로 읽는 원본 이름은 다음과 같다: `AVANTFAX_INSTALLDIR`, `AVANTFAX_ARCHIVE`, `AVANTFAX_ARCHIVE_SENT`, `AVANTFAX_TMPDIR`, `AVANTFAX_AUDIO_DIR`, `AVANTFAX_SERVERNAME`, `AVANTFAX_RESERVED_FAX_NUM`, `HYLASPOOL`, `HYLAFAX_PREFIX`, `BINARYDIR`, `HYLAFAX_USER_SYNC`, `FAXMAILUSER`, `WWWUSER`, `DEFAULT_TSI_ID`, `ENABLE_DID_ROUTING`, `ENABLE_BARDECODE_SUPPORT`, `ENABLE_OCR_SUPPORT`, `ENABLE_DL_TIFF`, `ENABLE_FAX_ANNOTATION`, `ARCHIVEFAX2EMAIL`, `FAXRCVD_INCLUDE_PDF`, `FAXRCVD_INCLUDE_THUMBNAIL`, `FAXRCVD_PRINT_PDF`, `PRINTFAXRCVD`, `PRINTERNAME`, `PRINTCMD`, `PDFPRINTCMD`, `NOTIFY_INCLUDE_PDF`, `NOTIFY_ON_SUCCESS`, `COVERPAGE_FILE`, `COVERPAGE_MATCH`, `FROM_COMPANY`, `FROM_LOCATION`, `FROM_FAXNUMBER`, `FROM_VOICENUMBER`, `PAPERSIZE`, `DPI`, `PREV_TN`, `PREV_SP`, `PHONEBOOK`, `WHITEPAGES`, `ALTERNATE_AUTH_ENABLE`, `ALTERNATE_AUTH_CLASS`, `ALTERNATE_AUTH_FALLBACK`, `WEBSERVER_AUTH`, `PWAUTHPATH`, `MIN_PASSWD_SIZE`, `MAX_PASSWD_SIZE`, `MAX_USERNAME_SIZE`, `MAX_EMAIL_SIZE`, `DEFAULT_FAXES_PER_PAGE_INBOX`, `DEFAULT_FAXES_PER_PAGE_ARCHIVE`, `INBOX_LIST_MODEM`, `RESTRICTED_USER_MODE`, `SHOW_ALL_CONTACTS`, `SHOWSERVER_DETAILS`, `FOCUS_ON_NEW_FAX`, `FOCUS_ON_NEW_FAX_POPUP`, `SENDFAX_USE_COVERPAGE`, `SENDFAX_REQUEUE_EMAIL`, 날짜·메일 형식(`EMAIL_DATE_FORMAT`, `FAXCOVER_DATE_FORMAT`, `EMAIL_ENCODING_CHARSET`), OCR·바코드(`OCR_BINARY`, `OCR_COMMAND`, `OCR_LANGUAGE`, `BARDECODE_BINARY`, `BARDECODE_COMMAND`), 그 밖(`ADMIN_EMAIL`, `AUTOCONFDID`, `ANN_GRAVITY`, `CPAGE_LINELEN`, `NUM_PAGES_FOLLOW`, `USE_HTML_COVERPAGE`, `TIFF_TO_G4`, `PRINTFAX2PS`, `SUDO`). 켜고 끄는 값은 `1`/`true`/`True`/`yes`(`settings.TRUE`). 일부는 `1/true/True` 만 인정한다(`fax_access._did_routing_enabled`). 변수별 기본값은 `common/settings.py` 와 사용하는 파일에 흩어져 있어 이 페이지에서 일일이 옮기지 않았다.
- [코드] `REMOTE_USER` 는 웹 서버가 넘기는 값이고 설정이 아니다(`WEBSERVER_AUTH` 와 함께 쓰는 로그인).

### 2.3 ini 전용 설정(환경 변수로는 설정 불가)
- [코드] `session.secure`, `csrf.trusted_origins`(쉼표로 구분한 `https://호스트`), 그리고 `session.secret`/`secret.key`/`demo.data`/`sqlalchemy.url` 은 ini 로도 쓸 수 있다. 앞의 두 개는 환경 변수가 없다. `namifax serve` 로는 쓸 수 없다(1.1 모순 참고).
- [코드] 프록시 뒤에서는 `X-Forwarded-Host` 를 읽어 `Origin`/`Referer` 와 비교하므로(`origin_guard.py`) `csrf.trusted_origins` 없이도 nginx 설정의 `proxy_set_header X-Forwarded-Host $host` 만으로 동작한다. 단, SAML 콜백(`/auth/saml/acs`, `/auth/saml/sls`)은 검사에서 제외된다.

## 3. 배포 파일(저장소 `deploy/`, `systemd/`)

| 파일 | 내용 | 비고 |
|---|---|---|
| `systemd/namifax.service` | `User=uucp`, `/opt/namifax`, `namifax serve`, `NAMIFAX_HOST=0.0.0.0`, `NAMIFAX_PORT=8000`, `NAMIFAX_ENABLE_SCHEDULER=1`, `ProtectSystem=full`, `ProtectHome=true`, `NoNewPrivileges=true`, `LimitNOFILE=65536` | 문서와 달리 `deploy/systemd/` 가 아니라 최상위 `systemd/` 에 있다 |
| `systemd/namifax-scheduler.service` | 위와 같은 보호 설정, `namifax scheduler` | 웹 단위의 내장 스케줄러와 중복 주의 |
| `deploy/nginx/namifax.conf` | 443 SSL, `client_max_body_size 25m`, `127.0.0.1:8000` 프록시, `Host`/`X-Forwarded-Host`/`-Proto`/`-For` 전달, `/forgot` 속도 제한 예시는 주석 | 포트가 systemd 단위와 일치 |
| `deploy/apache/namifax.conf` | 443 SSL, `LimitRequestBody 26214400`, `ProxyPass` 8000, `X-Forwarded-Proto https` | `X-Forwarded-Host` 줄은 없다. `ProxyPreserveHost On` 으로 Host 가 그대로 가므로 출처 검사는 통과한다 [코드]. 웹 서버 로그인(`WEBSERVER_AUTH`)은 프록시 방식에서 `REMOTE_USER` 가 안 넘어간다고 파일 주석이 명시 |
| `deploy/legacy-redirects/{nginx,apache}.conf` | 옛 주소 301 | [[migration-from-avantfax]] 참고 |
| `deploy/cron.d/namifax` | `0 0 * * * uucp namifax cron -t 2` 만 켜짐. `-i 30 -d 365`, `-p 90`, `-s` 줄은 주석 | |
| `deploy/sudoers.d/namifax` | `uucp` 가 `/sbin/reboot`, `/sbin/halt`, `/usr/sbin/faxdeluser *`, `/usr/sbin/faxadduser -u * -p * *` 만 비밀번호 없이 | 사용자 이름은 서비스 사용자에 맞춰 바꿀 것 |
| `deploy/hylafax/bin/{faxrcvd,dynconf,notify,faxcover}` | `/etc/namifax.env` 를 읽고 `${NAMIFAX_HOME:-/opt/namifax}/.venv/bin/namifax-*` 를 `exec` | |
| `deploy/hylafax/config.namifax` | `FaxRcvdCmd: bin/faxrcvd`, `DynamicConfig: bin/dynconf`, `UseJobTSI: true` (모뎀별 설정에 추가) | |
| `deploy/hylafax/etc-faxq.snippet` | `NotifyCmd: bin/notify`, `CoverCmd: bin/faxcover` | |
| `deploy/hylafax/hfaxd.conf.snippet` | 파일 이름과 달리 `JobFmt: "%-3j %3i %1a %15o %40M %-12.12e %5P %5D %7z %.25s"` (큐 목록 열 10개) | 이름이 내용을 가리킴 |
| `deploy/postfix/setup-email2fax.md` | 메일 → `faxmail` 파이프 설정 단계 | 시스템 파일을 직접 고치지 않는 설명서. 상세는 [[setup-email2fax]] |

- [코드] 위 단위·설정 파일의 내용은 직접 열어 확인했다. 실제 서버에 적용해 시험한 적은 없다.

### 3.1 문서와 배포 파일의 차이(코드를 따름)
> 모순: [[install-hylafax]] 0단계는 "`/etc/namifax.env` 를 훅 스크립트와 **서비스**가 같은 파일로 읽는다"고 쓴다. 훅 스크립트 4개는 `[ -r /etc/namifax.env ] && . /etc/namifax.env` 로 읽는다(`deploy/hylafax/bin/*`). 그러나 `systemd/namifax.service` 와 `namifax-scheduler.service` 에는 `EnvironmentFile=` 줄이 **없고**, `deploy/cron.d/namifax` 도 환경 파일을 읽지 않는다. 따라서 저장소의 기본 단위 파일로는 `DATABASE_URL`, `NAMIFAX_SESSION_SECRET`, `NAMIFAX_SECRET_KEY` 가 웹 서비스·스케줄러·cron 에 전달되지 않는다. 설치할 때 `EnvironmentFile=/etc/namifax.env` 를 단위 파일에 넣고, cron 줄에도 환경을 주도록 직접 고쳐야 한다. 안 그러면 `DATABASE_URL` 이 없어 `namifax.db`(SQLite, 현재 폴더)로 조용히 떨어진다(`db/provider.py`).

> 모순(추가 확인 필요): 훅 스크립트는 `. /etc/namifax.env` 로 변수를 읽은 뒤 `exec` 한다. 파일에 `export` 가 없는 `KEY=value` 형식(systemd `EnvironmentFile` 과 같은 형식)이면 POSIX sh 에서는 변수가 자식 프로세스에 전달되지 않는다. 같은 파일을 두 곳에서 쓰려면 `export` 를 붙이거나 스크립트에 `set -a` 가 있어야 한다. 현재 스크립트에는 `set -a` 가 없다 [코드: `deploy/hylafax/bin/notify` 등]. 실제 HylaFAX 훅 실행 환경에서 확인하지 못했다.

- [코드] 사용자 동기화(`HYLAFAX_USER_SYNC=1`)와 시스템 기능의 재부팅·종료는 `sudo` 를 쓴다. `systemd/namifax.service` 의 `NoNewPrivileges=true` 는 문서가 사용자 동기화를 켤 때 `false` 로 바꾸라고만 안내한다([[install-hylafax]] 3단계). 관리자 > 시스템 기능의 재부팅·종료(`sysfunc.reboot_command` = `sudo /sbin/reboot`)도 같은 sudo 를 쓰므로, 단위를 그대로 두면 동작하지 않을 가능성이 크다 [추정: `NoNewPrivileges` 가 `sudo` 의 권한 상승을 막는다는 일반 동작에 근거, 실제 시험은 하지 못함]. 재부팅 버튼을 쓸 계획이면 점검 항목에 넣을 것.
- [문서] [[install-hylafax]] 는 경로 가정을 `/opt/namifax`(가상환경 `.venv`), `/var/spool/hylafax`, 서비스 사용자 `uucp` 로 둔다. 단위 파일과 `deploy/cron.d` 가 같은 가정이다 [코드].
- [코드] `ProtectSystem=full` 은 `/etc`, `/usr` 를 읽기 전용으로 만든다. 서비스가 쓰는 `/var/spool/hylafax` 는 영향 밖이다 [추정: systemd 일반 동작].

## 4. 설치 후 점검 순서(권장)
[문서] [[install-hylafax]] 7단계를 기준으로, 위 코드 대조에서 나온 점검을 앞에 붙인 순서다.

1. 단위 파일에 `EnvironmentFile` 을 넣었는지, `DATABASE_URL`/`NAMIFAX_SESSION_SECRET`/`NAMIFAX_SECRET_KEY` 가 웹 서비스·스케줄러·cron·훅 모두에 전달되는지 확인한다(3.1). 로그에 `No session.secret / NAMIFAX_SESSION_SECRET configured` 경고가 없어야 한다 [코드].
2. DB: MySQL/MariaDB/PostgreSQL 은 시작할 때 Alembic `upgrade head` 로 테이블을 만들고, 데모 계정은 만들지 않는다 [코드: `db/bootstrap.py`]. 첫 관리자는 `namifax createuser -u <이름> -e <메일>` 로 만든다(비밀번호는 `-p`, `NAMIFAX_NEW_USER_PASSWORD`, 터미널 프롬프트 순. 기본 비밀번호 없음) [코드: `cli/user.py`].
3. 암호화 키: `NAMIFAX_SECRET_KEY` 를 정한 뒤 `namifax encrypt-secrets` 를 한 번 실행한다. 키를 잃으면 암호화된 값은 복구할 수 없다 [코드: `common/secretbox.py` 가 키 없으면 `SecretKeyError`; 복구 불가는 [문서] [[operations-checklist]]].
4. 웹 서버(nginx 또는 apache) 설정 후 HTTPS 로 접속한다. `session.secure` 를 켜야 하면 `pserve` 경로를 쓴다(1.1).
5. 로그인 → 설정 → 시스템 로그에서 오류를 확인한다 [문서].
6. HylaFAX: `sendfax`, `faxstat` 이 `PATH` 에 있는지 확인한다. 없으면 전송이 시뮬레이션될 수 있다(2.1 `NAMIFAX_QUEUE_SIMULATION`) [코드]. `sudo -u uucp /var/spool/hylafax/bin/dynconf ttyS0 5551234` 가 아무것도 출력하지 않고 끝나야 한다 [문서].
7. 관리자 > 모뎀에서 모뎀을 만들고 상태가 `Running and idle` 인지, 대시보드에 HylaFAX 버전이 보이는지 확인한다(`faxstat -i`, 못 읽으면 `None` 이라 표시를 지어내지 않음) [코드: `services/hylafax_info.py`].
8. 시험 팩스를 보내 출력함에 나타나는지, `notify` 가 보낸 팩스를 보관함에 올리는지 확인한다. 시험 팩스를 받아 `faxrcvd` 가 받은 팩스함에 올리는지(썸네일, PDF, 메일 알림) 확인한다 [문서].
9. 주기 작업: 관리자 > 예약 작업을 확인하고, 보관함 날짜 삭제(`-d`)가 필요하면 `deploy/cron.d/namifax` 의 주석 줄을 풀어 `/etc/cron.d/namifax` 로 둔다 [코드].
10. SMTP 게이트웨이를 관리자 화면에서 설정한다. 비밀번호 찾기, 수신 팩스 메일 전달, 알림이 이 설정을 쓴다. 기본 호스트는 `localhost` 이고 DB 를 읽지 못하면 로컬 MTA(localhost:25)로 보낸다 [코드: `services/smtp_settings.py`, `services/mailer.py`].

## 5. 운영 전에 사람이 판단할 것
| 항목 | 이유 | 근거 |
|---|---|---|
| `namifax serve`(wsgiref 스레드 서버) 그대로 운영할지, `pserve`+waitress 로 갈지 | 단위 파일은 전자를 쓰고 전자는 `session.secure` 를 못 켠다 | [코드] `main.py`, `__init__.py` |
| 쿠키 `Secure` 표시 | HTTPS 에서는 켜야 하지만 `namifax serve` 로는 설정 경로가 없음 | [코드] |
| `/forgot` 요청 횟수 제한(앞단) | 이메일만 알면 남의 기존 비밀번호를 무효화할 수 있음. 새 비밀번호는 본인 메일로만 간다 | [문서] [[operations-checklist]] |
| 사용자 동기화(`HYLAFAX_USER_SYNC`) 켤지 | `faxadduser` 가 비밀번호를 명령줄 인자로 받아 `ps` 로 노출됨. 전용 장비에서만 | [문서] [[install-hylafax]], sudoers 의 `faxadduser -u * -p * *` [코드] |
| SAML 로그인이 앱의 2FA 를 거치지 않음 | 확정된 정책: IdP 가 책임진다 | [문서] [[operations-checklist]] |
| 설정에서 지운 모뎀의 팩스는 받은 팩스함에서 안 보임(슈퍼유저 포함) | 모뎀 삭제 전에 비우거나 보관 | [문서]; 관련 코드 주석: 슈퍼유저 목록은 "설정된 모뎀·DID" 로 제한 [코드: `services/fax_access.py`] |
| 첫 기동 시간 | 큰 `FaxArchive` 에 인덱스를 만들 때 오래 걸릴 수 있음. 측정 안 함 | [문서] [[migrating-from-avantfax3]] |
| 키 회전 | 새 `NAMIFAX_SECRET_KEY` 로 바꾸기 전에 옛 키로 읽을 수 있는 상태에서 작업 | [문서] |
| 번역 | 한국어만 새 문구까지 채워짐. 나머지 언어는 새 화면 문구가 영어로 보일 수 있음 | [문서] [[i18n-and-ui]] |

## 6. 확인하지 못한 것
- 실제 HylaFAX 서버와의 연동(`JobFmt` 열 순서, `faxrm`/`faxalter` 의 소유자 권한, 배포판별 서비스 이름 `faxq`/`hfaxd`/`faxgetty`, 훅 환경 변수 전달). 문서와 파일 내용만 읽었고 연동은 이 세션에서 시험하지 않았다. 출력함은 가짜 `faxstat` 출력으로만 시험됐다고 문서는 말한다 [문서].
- Okta, Entra ID 등 실제 IdP(문서는 Keycloak 26 컨테이너로만 확인했다고 함) [문서].
- 단위 파일·nginx·apache 설정을 실제 서버에 적용해 시작해 보는 것. 이 세션에서는 서버를 띄우지 않았다.
- 이메일 → 팩스(Postfix `faxmail`)는 설명서만 있고 시험하지 않았다 [문서: [[setup-email2fax]]].
