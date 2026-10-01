# 2라운드 점검: 팩스 수신 흐름 (faxrcvd 훅 -> DB/파일 -> 수신함/보기/PDF/검색/보관함)

점검 방식: 샘플 다중 페이지 G4 TIFF 를 만들고(Pillow), HylaFAX 방식 인자(`file devID commID error-msg CIDNumber CIDName DIDnum`)와 모의 `faxinfo` 바이너리(PATH 앞에 둠)로 `python -m namifax.cli.faxrcvd` 를 실제 실행했다. 이후 sqlite 로 FaxArchive/AddressBook/Modems 를 조회하고, webtest 로 /inbox, /archive, /faxes/download, /ajax/inbox 응답을 확인했다. 모든 DB/아카이브는 scratchpad/agent-r2-recv/ 하위이다. 위치 경로는 모두 `src/namifax/` 기준이다.

1라운드/known2.md 와 같은 원인은 제외했고, 흐름에서만 드러나는 변형은 "변형"으로 표시했다. 다른 2라운드 에이전트(round2-parity F4-09, F4-12)와 겹칠 수 있는 항목은 비고에 적었다.

## F1-01 [높음] 마이그레이션이 발신자 미식별 팩스를 매번 "Acme Corp 의 팩스번호(faxnumid=1)"로 귀속시킴 (COR-05 + COR-02 의 결합 변형)
- 위치: db/schema.py:279 (`UPDATE FaxArchive SET faxnumid = 1 WHERE faxnumid IS NULL`, 모든 프로세스 기동마다 실행), cli/faxrcvd.py:119-132 (COR-05 로 신규 발신번호는 faxnumid=None 으로 저장됨)
- 증상: 주소록에 없는 발신자(또는 발신번호 없는 팩스)의 행은 faxnumid=NULL 로 저장된다. 다음 훅 호출이나 웹 기동 때 마이그레이션이 이를 1 로 바꾸고, 1번은 시드 샘플 "Acme Corp"(1234567)이다. 수신함은 faxnumid 로 회사명을 조회하므로 전혀 무관한 팩스가 Acme Corp 발신으로 표시되고, 이후 주소록 통계와 회사별 검색도 Acme 로 묶인다. 실제 운영 주소록의 1번 번호가 다른 회사이면 그 회사로 귀속된다(데이터 오염).
- 재현: 새 DB 에서 `faxrcvd recvq/fax000000123.tif ttyS0 comm01 "" 5551234 "ACME Test" 100` 실행 -> FaxArchive fid=2 faxnumid=NULL. 다른 번호(9876543)로 훅을 한 번 더 실행한 뒤 조회하면 fid=2 의 faxnumid=1. /inbox 에 "Acme Corp 5551234" 로 표시됨. 발신번호 없는 팩스(`CallID1 <NONE>`, Sender UNKNOWN)도 동일하게 faxnumid=1.
- 확인 수준: 재현

## F1-02 [높음] 같은 마이그레이션이 발신 팩스의 modemdev 를 'ttyS0' 으로 채워 "발신" 검색과 구분 기준을 깨뜨림
- 위치: db/schema.py:276 (`UPDATE FaxArchive SET modemdev = 'ttyS0' WHERE modemdev IS NULL`), 소비처 services/archive_base.py search_archive (`sentrecvd == "s"` 는 `modemdev is null`, "r" 은 `modemdev is not null`)
- 증상: 레거시 의미에서 발신 팩스는 modemdev=NULL 이다. 다음 프로세스 기동(훅, 웹 재시작) 때 NULL 이 모두 'ttyS0' 으로 바뀌어 보관된 발신 팩스가 "Sent only" 검색에서 사라지고, 수신 모뎀이 ttyS0 인 것처럼 집계와 모뎀 기반 열람 권한 필터에 섞여 들어간다.
- 재현: FaxArchive 에 (userid=2, modemdev=NULL, inbox=0) 행을 넣고 `get_default_engine()` 재호출(= 다음 프로세스 기동) -> modemdev='ttyS0'. `FaxPDFArchive().search_archive({"sentrecvd":"s","superuser":True})` -> 0건.
- 확인 수준: 재현
- 비고: COR-02 는 fid=1 과 Modems 덮어쓰기만 다룬다. 이 두 UPDATE(faxnumid, modemdev)는 전 행에 적용되는 별개 경로다.

## F1-03 [높음] faxinfo 출력 해석 실패가 전부 무경고 "더미 팩스 정보"로 대체되어 실제 발신자와 수신 시각이 사라짐 (COR-15 의 유효 TIFF 변형)
- 위치: common/helpers.py:413-445 (`subprocess.run(..., text=True)` 예외를 `except Exception: pass` 로 삼킨 뒤 Pillow 폴백이 Sender "00000000", CallID1 "00000000", 수신 시각 = 파일 mtime 을 반환), cli/faxrcvd.py:85-99
- 증상: 유효한 HylaFAX TIFF 인데도 다음 두 경우에 faxinfo 결과가 통째로 버려진다. (1) 발신자 TSI/CNAM 에 UTF-8 이 아닌 바이트(유럽 구형 팩스기의 Latin-1 상호명 등)가 있으면 `text=True` 디코딩이 UnicodeDecodeError 를 내고 삼켜짐. (2) 훅 환경의 PATH 에 faxinfo(HylaFAX sbin)가 없으면 FileNotFoundError 가 삼켜짐. 두 경우 모두 발신번호 "00000000", 수신 시각 mtime 으로 저장되고 로그도 없다(레거시는 faxinfo 실패 시 "corrupted" 로그 후 종료). 훅 인자로 CIDNumber 가 오면 그 값은 살아남지만, 인자가 없으면 모든 팩스가 같은 "00000000" 발신자로 섞인다.
- 재현: PATH 앞에 `printf 'Sender: Soci\xe9t\xe9 Dupont\nPages: 3\nReceived: 2026:10:01 23:59:58\nCallID1: 0155512345\n...'` 를 출력하는 faxinfo 를 두고 훅을 인자 없이(CIDNumber 생략) 실행 -> origfaxnum='00000000', archstamp 는 실제 수신 시각(23:59:58) 대신 파일 mtime(08:32:53). faxinfo 가 PATH 에 없을 때도 동일.
- 확인 수준: 재현

## F1-04 [높음] DB 가 잠깐 잠기면(5초 초과) 훅이 종료코드 0 으로 아무 로그 없이 끝나고, 아카이브 파일만 고아로 남아 팩스가 수신함에 나타나지 않음
- 위치: db/engine.py:87 (`sqlite3.connect(path, check_same_thread=False)`: busy_timeout 기본 5초, 문장마다 별도 대기), cli/faxrcvd.py:160-168 (`inbox.create` 실패 분기 없음: 로그도 재시도도 없음), 모든 예외를 QueryResult(executed=False)로 흡수하는 COR-22 동작
- 증상: 웹 요청, 스케줄러, 백업 등이 DB 에 쓰기 잠금을 5초 이상 잡고 있는 동안 도착한 팩스는 TIFF/PDF/미리보기가 디스크에는 만들어지지만 FaxArchive 행이 생기지 않는다. 훅은 rc=0 으로 끝나므로 HylaFAX 는 recvq 원본을 지운다. 사용자는 수신함에서 팩스를 볼 수 없고 알림 메일도 없다. 훅 1회가 30초 이상 걸리는 부작용도 있다. (COR-20 4번은 "실패 로그 없음"만 지적했고, 행 유실, 종료코드, 고아 파일은 다루지 않았다.)
- 재현: 다른 프로세스가 `BEGIN EXCLUSIVE` 를 45초 보유하는 동안 훅 실행 -> 30.4초 후 rc=0, stdout 에 "Create PDF/Create Thumbnails" 만 출력, `archive6/2026/10/01/5550888/000000171/fax.tif` 존재, `SELECT count(*) FROM FaxArchive WHERE origfaxnum='5550888'` = 0. (잠금이 14초 이내에 풀리면 일부 문장만 실패해 우연히 성공하므로 결과가 비결정적이다.)
- 확인 수준: 재현

## F1-05 [중간] Pillow 폴백 PDF/미리보기가 TIFF 해상도 태그를 무시해 페이지 크기와 비율이 틀어짐
- 위치: common/helpers.py:355-362 (tiff2pdf 폴백: `img.convert("RGB")` 후 `save(format="PDF")`, dpi/resolution 미지정), :388-400 (static_preview 는 원본 픽셀 그대로 PNG 저장)
- 증상: tiff2pdf 바이너리가 없을 때(이 환경처럼 대부분의 웹 호스트) PDF 는 72dpi 로 해석되어 MediaBox 가 픽셀 수 그대로 나온다. 1728x2291 픽셀 파인 모드 페이지는 24x31.8인치 용지가 되고, HylaFAX 표준 해상도(204x98dpi, 1728x1145 픽셀)는 세로가 절반으로 눌린 가로형 페이지가 된다. 썸네일과 미리보기도 비율이 틀린 그대로(가로로 납작) 저장된다. 인쇄나 메일 첨부 PDF(FAXRCVD_INCLUDE_PDF)가 실사용 불가 크기다.
- 재현: dpi=(204,98), 1728x1145 G4 TIFF -> fax.pdf `/MediaBox [0 0 1728.0 1145.0]`, preview0.png 1728x1145. 파인(204x196)은 `[0 0 1728.0 2291.0]`.
- 확인 수준: 재현

## F1-06 [중간] 다쪽 수신 팩스를 모든 페이지 RGB 비트맵으로 메모리에 올려 PDF 를 만듦: 크기 70배, 메모리 수백 MB
- 위치: common/helpers.py:352-362 (tiff2pdf 폴백이 `pages.append(img.convert("RGB"))` 를 전 페이지 누적 후 일괄 저장), :296-305 convert2pdf 동일
- 증상: 1비트 G4 팩스를 24비트로 확장하므로 60쪽 53KB TIFF 가 3.7MB PDF 가 되고, 훅 프로세스의 최대 RSS 가 약 700MB 증가한다. 100쪽 이상 수신이나 모뎀 여러 개의 동시 수신에서 OOM 으로 훅이 죽으면 F1-04 와 같은 고아 상태가 된다(행 삽입 이전 단계이므로 파일만 남고 DB 행 없음).
- 재현: 60쪽 1728x2291 G4 TIFF -> tiff2pdf() 1.0초, PDF 3722KB, maxrss 948MB(기준 251MB).
- 확인 수준: 재현 (OOM 연쇄는 추론)

## F1-07 [중간] 회전: 경로가 맞는 경우 다쪽 TIFF 를 1쪽으로 잘라 저장(데이터 손실), 기본 구성에서는 아무것도 안 하면서 "rotation: 90" 응답
- 위치: services/archive_in.py:71 (`faxpath.lstrip("/")` 로 훅이 저장한 절대경로를 상대경로로 바꿈), :80-84 (`Image.open` 한 첫 프레임만 `rotate(180)` 후 같은 경로에 save), views/inbox.py fax_rotate_view (응답에 `"rotation": 90` 고정, 실제는 180)
- 증상: (a) 웹 기본(`ArchiveIn()` installdir="")에서는 경로가 cwd 상대로 바뀌어 TIFF, 썸네일, 미리보기가 하나도 안 돌아가는데 200 ok 를 반환한다(COR-28 1번 삭제 불능과 같은 원인의 회전판, 파일 md5 불변 확인). (b) installdir 을 "/" 로 주어 경로가 맞는 경우에는 fax.tif 가 1프레임으로 덮어써져 2쪽 이후가 영구 삭제된다. DB pages 는 그대로 3이고 fax.pdf 와 미리보기는 회전되지 않아 파일 간 불일치. 90도 회전이라는 응답과 실제 180도 동작도 다르다.
- 재현: 훅으로 만든 3쪽 팩스에 `GET /faxes/rotate/3` -> 파일 md5 전부 불변, 응답 `{"status":"ok","rotation":90}`. `ArchiveIn(installdir="/").load_fax(3); rotate_fax()` -> True, fax.tif `n_frames` 3 -> 1.
- 확인 수준: 재현

## F1-08 [높음] 수신함이 최신 25건만 보여주고 "25 of 25" 로 표시, 26번째 이후 팩스는 웹에서 접근 불가
- 위치: views/inbox.py:29 (`arc.list_inbox(devices=devices)` 는 index=0, limit=25 고정), :67 (`total_faxes = len(faxes)`), templates/inbox.jinja2 (페이지 링크 고정 "1")
- 증상: 수신함에 48건이 있어도 25건만 렌더되고 합계와 헤더 배지가 25 로 나오므로 오래된 23건은 존재 자체를 알 수 없다. 보관, 삭제 동작도 보이는 행에만 적용 가능해서 새 팩스를 보관 처리해야만 예전 것이 보인다. 훅이 계속 쌓는 수신 팩스의 주 열람 경로가 막힌다.
- 재현: inbox=1 행 48건 -> `GET /inbox` 의 `id="faxid_"` 25개, "25 of 25 faxes", `GET /inbox?page=2` 도 동일한 25개.
- 확인 수준: 재현
- 비고: round2-parity F4-09 가 "페이지네이션 없음"을 언급하므로 겹칠 수 있다. 여기서는 총건수 오표시와 접근 불가 영향을 실제 수치로 확인했다.

## F1-09 [중간] /ajax/inbox 신규 팩스 카운트가 항상 0 (TypeError 삼킴)
- 위치: views/ajax.py:60 (`arc.get_num_faxes(inbox=True)`), services/archive_base.py:144 (시그니처는 devices, faxcats, enable_did_routing 뿐)
- 증상: 미지원 키워드 인자로 TypeError 가 나고 `except Exception: count = 0` 이 삼킨다. 레거시 ajaxinbox.php 는 새 수신 팩스 수로 "새 팩스 도착" 갱신을 하는데 신규 앱은 수신함에 6건이 있어도 "0" 을 돌려준다.
- 재현: inbox=1 행 6건에서 `GET /ajax/inbox` -> 200 "0".
- 확인 수준: 재현
- 비고: round2-parity 표는 이 엔드포인트를 "사용자 범위 없는 전체 집계"로 적었으나 실제로는 집계 자체가 실패한다.

## F1-10 [높음] 보관(아카이브)된 수신 팩스가 보관함 화면에 나타나지 않음: 결과 행을 로드하지 않고 존재하지 않는 get_company 호출
- 위치: views/archive.py:42-50 (`fa.next_archive_entry()` 는 fid 만 반환하는데 `fa.load_fax(fid)` 없이 `fa.get_company()`, `get_origfaxnum()` 등을 호출), services/archive_base.py (FaxPDFArchive 에 get_company 없음)
- 증상: 수신함에서 보관한 팩스가 search_archive 에서는 정상적으로 잡히지만(faxid=2 -> 1건), 뷰 루프에서 AttributeError 가 나 바깥 `except Exception: pass` 에 삼켜지고 results 는 빈 목록이 되어 가짜 placeholder(Acme Corp / Quarterly Financial Fax Transmission)가 대신 표시된다. load_fax 를 호출해도 get_company 가 없어 같은 예외가 난다. USR-01, USR-02 와 별개로, 실데이터가 있어도 보관함 행 렌더링 자체가 불가능하다.
- 재현: 훅으로 fid 2, 4 생성 후 `ArchiveIn().set_archivebox(2)`, `set_archivebox(4)`. `GET /archive?faxid=2` -> "1 result" 이지만 본문은 "Acme Corp +1-555-0199 Quarterly Financial Fax Transmission 2 2026-09-29 09:30:00". 서비스 직접 호출: `search_archive({"faxid":2,"superuser":True})` -> 1건 `[{'fid': 2}]`, `fa.get_company()` -> AttributeError, `get_pages()` 등은 None.
- 확인 수준: 재현
- 부가: 훅이 저장한 archstamp 는 "2026/10/01 08:24:02" 이므로 UI 날짜 입력(`2026-10-01`)으로는 `start_date` 검색이 0건, 슬래시 형식은 매칭된다(COR-14 의 날짜 형식 불일치가 검색에서 드러나는 사례).

## F1-11 [중간] 수신함 행의 빈 값을 가짜 기본값으로 채움: 미식별 발신자가 "Acme Corp", 수신 시각이 2026-09-29, 모뎀이 ttyS0 (USR-02 의 수신함판)
- 위치: views/inbox.py:49-51 (`cname or r.get("company") or "Acme Corp"`, `r.get("archstamp") or "2026-09-29 10:00:00"`, `r.get("modemdev") or "ttyS0"`), :79 viewfax 도 같은 기본값
- 증상: 훅이 주소록 매칭에 실패한 팩스(F1-01 이전 상태, 또는 faxnumid 없는 행)는 회사명 자리에 "Acme Corp" 가 표시된다. 실제 발신번호가 "-" 이어도 회사는 Acme Corp 다. 사용자는 미식별과 실제 Acme 발신을 구분할 수 없다. USR-02 는 보관함/조회 페이지만 언급했다.
- 재현: faxnumid NULL 행(프로세스 기동 전의 fid 7)이 `GET /inbox` 에서 "Acme Corp - Received Facsimile" 로 표시됨.
- 확인 수준: 재현

## F1-12 [중간] 훅이 받은 원격 팩스 송신자의 TSI/CallerID 이름이 검증 없이 SQL 문자열 값이 됨 (SEC-11 의 공격 출처 변형, MySQL 전용)
- 위치: cli/faxrcvd.py:101 (`company_name = cid_name or sender`), :142 (`addressbook.create(company_name)` -> MDBOData.find/new_entry -> DatabaseEngine.quote), db/engine.py:188 (작은따옴표만 이중화, 백슬래시 미처리)
- 증상: 훅 입력 중 회사명(CIDName/TSI 텍스트)은 전화망 건너편 송신자가 임의 문자열로 정할 수 있어 로그인 사용자가 필요 없는 공격 출처다. MySQL/MariaDB 백엔드(NO_BACKSLASH_ESCAPES 아님)에서는 `\` 로 끝나는 이름 등이 이스케이프를 깨뜨릴 수 있다. SQLite 에서는 영향이 없고, 지금은 COR-05 로 create 경로에 도달하지 못해 잠복 상태이며 COR-05 를 고치면 활성화된다.
- 재현 방법: 공격 페이로드는 실행하지 않았고 코드 경로만 확인했다.
- 확인 수준: 추론

## F1-13 [중간] 훅 실행 시 모뎀 라우팅 설정이 훅 자신의 seed 로 파괴되어 알림 메일, 분류, 프린터 지정이 사라짐 (COR-02 의 수신 흐름 변형)
- 위치: db/schema.py (`seed_database_if_empty`: Modems 행이 2개 미만이면 devid 1, 2 를 INSERT OR REPLACE), 호출은 faxrcvd 의 `FaxModem()` 사용 직전 `get_default_engine()`
- 증상: 운영자가 모뎀을 1개만 등록한 구성(devid 1 = 실제 회선)에서 훅이 시작되면 seed 가 devid 1 을 샘플(ttyS0 Sales Inbound, sales@avantfax.local, lp1)로 덮어쓰고 devid 2 (ttyS1)를 추가한다. 곧바로 `modem.load_device(실제 장치)` 가 실패하여 "unconfigured modem" 으로 새 모뎀(연락처, 프린터, 분류 없음)을 만든다. 그 팩스는 분류, 담당자 메일, 프린터 라우팅을 전부 잃고, 실제 모뎀 설정은 복구되지 않는다.
- 재현: Modems 를 (devid 1, ttyIAX0, Main Line, ops@corp.example, hp_office, faxcatid 1) 한 행만 남기고 `faxrcvd ... ttyIAX0` 실행 -> Modems 가 ttyS0 Sales Inbound / ttyS1 Support Outbound / ttyIAX0(연락처 없음)로 바뀌고, 수신 팩스의 faxcatid=NULL.
- 확인 수준: 재현

## F1-14 [낮음] 레거시 faxinfo() 후처리 누락: UNKNOWN/UNSPECIFIED 발신자 예약번호 치환, CallID 인덱스 설정, 알림 제목 날짜 형식
- 위치: common/helpers.py:406-452 (faxinfo 에 Sender 정규화 없음), cli/faxrcvd.py:94-99 (CallID1/2/3 하드코딩), :239-240 (제목 날짜를 `%Y-%m-%d %H:%M:%S` 로 고정), services/addressbook.py:96-100 (`get_companies(with_reserved)` 인자 무시)
- 증상: 레거시 functions.php:853-856 은 Sender 가 UNKNOWN/UNSPECIFIED/빈 값이면 RESERVED_FAX_NUM("XXXXXXX")로 바꾸고 주소록 목록에서 그 예약 회사를 숨긴다. Python 은 "UNKNOWN" 을 그대로 발신자로 쓰므로 디렉터리명은 `unknown`, origfaxnum 은 빈 문자열이 되고, COR-05 를 고치면 "UNKNOWN" 회사가 주소록에 생긴다. CallID1/2/3 인덱스는 레거시의 `$CALLIDn_*` 설정으로 바꿀 수 있었지만 고정이다. 제목 날짜는 레거시 EMAIL_DATE_FORMAT(`%d.%m.%Y %H:%M`)과 다르다. SIP 접미사 제거는 faxinfo 경로에서 이루어지지 않아 `5551234@10.0.0.5` 가 origfaxnum `555123410005` 가 되며, dynconf 는 `@` 앞만 쓰므로 블랙리스트 키와 저장 번호가 다르다(참고: 레거시의 SIP 제거 코드는 키 오타 `CallID11` 로 사실상 무효였으므로 이 부분은 레거시와 동일한 결함이다).
- 재현: 모의 faxinfo 에 `Sender: UNKNOWN`, `CallID1 <NONE>` -> origfaxnum '', faxpath `.../unknown/...`. `CallID1: 5551234@10.0.0.5` -> origfaxnum '555123410005'. DID 모드에서 `CallID3: 100@host` 가 DIDRoute routecode 로 그대로 자동 등록됨.
- 확인 수준: 재현

## F1-15 [낮음] fax_download: 없는 fid 나 없는 파일에 200 + 64바이트 가짜 PDF, TIFF 요청에도 PDF 본문을 image/tiff 로 전송, format 값이 파일명 헤더에 검증 없이 삽입
- 위치: views/inbox.py:108-125 (파일을 못 찾으면 합성 PDF 바이트를 돌려줌, `content_type` 은 요청 format 으로만 결정), :125 (`filename="fax_{fid}.{fmt}"`)
- 증상: 수명주기가 TIFF 를 지웠거나(ADM-11/12, COR-15) 시드 fid 1, 존재하지 않는 fid, 숫자가 아닌 fid 모두 200 OK 로 깨진 "PDF" 를 받고 사용자는 팩스가 손상됐다고 생각한다. TIFF 다운로드는 PDF 스텁을 `image/tiff` 로 보낸다. format 파라미터는 `pdf` 가 아닌 임의 문자열이면 TIFF 로 취급하고 그 문자열이 그대로 Content-Disposition 파일명에 들어간다(헤더 주입 가능성은 추론, 실행하지 않음).
- 재현: `GET /faxes/download/1?format=tiff` -> 200 `image/tiff`, 본문 `%PDF-1.4\n% NamiFAX synthetic PDF ...`(64바이트). `/faxes/download/999`, `/faxes/download/abc` 도 200.
- 확인 수준: 재현 (헤더 주입은 추론)
- 비고: round2-parity F4-12 가 같은 합성 PDF 를 다룬다. 여기서는 TIFF 요청 시 MIME 불일치와 format 값 미검증이 추가된다.

---

## 흐름에서 확인했으나 새 결함이 아니라 기존 항목에 포함된다고 판단한 지점
- 훅 자체(TIFF 복사, PDF, 썸네일, ArchiveIn 삽입, 모뎀/DID 자동 등록, 카테고리 설정)는 실제로 동작했다. 동시에 8개 훅을 돌려도(신규 DB 포함) 행 8개, 파일 8세트가 정상 생성되어 동시 실행 자체의 문제는 없었다(F1-04 는 장기 잠금 한정).
- Fax2Email 라우팅과 주소록 카운터: COR-05, COR-06. 알림 메일 발송, 썸네일 임베드, PDF 첨부 시 TypeError 종료: COR-04, K13, ADM-17. 바코드/OCR: 스텁과 K12, COR-27, ADM-15. archstamp 형식과 prune: COR-14. 미리보기 파일명(preview vs page)과 삭제 불능: COR-28. 썸네일 미서빙: UI-23. DynConf: COR-08, ADM-08. 저장소 수명주기와 클라우드 업로드: K06, ADM-11, ADM-12, COR-32. PRINTFAXRCVD/ENABLE_FAX_ANNOTATION 미사용: COR-20. DB 경로 cwd 기본값: COR-13.
- PDF 다운로드 경로 자체는 정상: 훅이 저장한 절대 faxpath 로 `/faxes/download/{fid}?format=pdf|tiff` 가 실제 파일을 돌려준다(PDF %PDF 헤더 확인, TIFF 원본 3552바이트 일치).
- 훅 인자 위생: CIDNumber 는 clean_faxnum 으로 숫자와 '+' 만 남겨 아카이브 경로 탈출이 없다. hylfaxid 는 basename 기반이다.
