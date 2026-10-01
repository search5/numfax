# Round 1 — 일반 사용자 화면 결함 보고

검증 환경: `NAMIFAX_DB_PATH=scratchpad/agent-user/user.db`, `uv run python` + `webtest.TestApp(namifax.create_app({}))`.
계정: admin/password(superuser), operator/password(일반 사용자, seed 계정).

---

## USR-01 (높음) 아카이브 검색: 키워드/팩스ID 없이 필터링하면 결과가 항상 숨겨짐

- **위치**: `src/namifax/templates/archive.jinja2:106` (`{% if search or faxid %}`), `src/namifax/views/archive.py`
- **증상**: 날짜 범위, 카테고리, 송/수신 구분(sentrecvd)만으로 검색해도 서버는 결과를 정상 계산해 상단 배지에 "N results"를 표시하지만, 실제 결과 테이블은 `search`(키워드) 또는 `faxid` 파라미터가 없으면 렌더링되지 않고 항상 "Enter a keyword or filter above and click Search" 사전 검색 안내만 보여준다. 날짜/카테고리/송수신 단독 검색 기능이 사실상 동작하지 않음.
- **재현**: `GET /archive?category=1`, `GET /archive?sentrecvd=r`, `GET /archive?date_from=2026-04-01&date_to=2026-04-30` 모두 "1 result" 배지가 뜨지만 본문은 "Search the Archive… Enter a keyword…" placeholder만 출력됨(webtest로 확인, 실제 DB에 해당 조건에 맞는 팩스 레코드 다수 존재).
- **확인 수준**: 재현.

## USR-02 (높음) 검색/조회 결과가 0건일 때 가짜(placeholder) 레코드를 실제 결과처럼 표시

- **위치**: `src/namifax/views/archive.py` (`archive_view`, results 빈 배열일 때 `Quarterly Financial Fax Transmission…` fallback 삽입), `src/namifax/views/inbox.py` (`viewfax_view`), `src/namifax/views/modals.py` (`modal_txreport_view`)
- **증상**: 실제 쿼리가 0건이어도 코드가 "골든 마스터 호환용" 가짜 데이터(`Acme Corp`, `Quarterly Financial Fax Transmission`, `Acme Global`/`2026-09-29 10:15:00` 등)를 실제 결과처럼 채워 넣는다. 사용자는 검색 결과가 없었는지 실제로 매칭된 것인지 구분할 수 없고, 존재하지 않는 fid로 `/viewfax`, `/txreport`를 조회해도 200 OK와 그럴듯한 가짜 내용이 나온다(404/에러 없음).
- **재현**:
  - `GET /archive?search=bulk&date_from=2026-04-05&date_to=2026-04-05` → 실제로는 해당 범위에 진짜 결과가 0건(USR-04′ 참고, `archstamp > X AND archstamp < X`가 같은 날짜일 때 항상 거짓)인데 응답 본문에 `"Quarterly Financial"` 가짜 텍스트가 포함되고 진짜 `"bulk fax"` 텍스트는 없음.
  - `GET /txreport?fid=999999` (존재하지 않는 fid) → 200 OK, `"Acme Global"`, `"2026-09-29 10:15:00"` 가짜 값 반환.
  - `GET /viewfax?fid=999999` → 200 OK, 가짜 값으로 정상 조회된 것처럼 렌더링.
- **확인 수준**: 재현.
- **비고**: 부수적으로 `archive_base.FaxPDFArchive.search_archive()`에서 `start_date == end_date`(하루 단위 검색)일 때 `archstamp > 시작일 AND archstamp < 시작일` 조건이 항상 거짓이 되어 실제로는 결과가 0건이 되는 별도 로직 버그가 존재함(직접 서비스 호출로 `n=0` 확인, `start_date`만 주면 `n=1`로 정상 동작). 이 로직 버그가 UI 상에서는 USR-02의 가짜 데이터로 가려져 드러나지 않음.

## USR-03 (중간) 주소록/이메일북/배포목록 생성·수정 폼이 유효성 오류를 삼키고 무조건 성공 리다이렉트

- **위치**: `src/namifax/views/addressbook.py` (`addressbook_edit_view`, `emailbook_edit_view`), `src/namifax/views/distrolist.py` (`distrolist_edit_view`)
- **증상**: 서비스 계층(`AFAddressBook.create`, `create_contact`, `DistributionList.create`)은 중복 이름·잘못된 이메일 형식을 정상적으로 거부하고 `False`/에러를 반환하지만, 뷰는 `try/except Exception: pass` 로 감싼 뒤 결과를 확인하지 않고 항상 `HTTPFound`로 목록 페이지로 리다이렉트한다. 사용자는 저장이 실패했는지 전혀 알 수 없고, 폼에는 어떤 오류 메시지도 표시되지 않는다.
- **재현**:
  - `POST /emailbook/edit` with `contact_name=Bad&contact_email=notemail` → 302 리다이렉트(성공처럼 동작)하지만 DB 조회 결과 `AddressBookEmail`에 해당 레코드가 생성되지 않음(`SELECT count(*) FROM AddressBookEmail WHERE contact_name='Bad'` → 0).
  - `POST /addressbook/edit` with 이미 존재하는 `company=NewCo` (중복) → 302 리다이렉트지만 DB에 중복 레코드 미생성, 화면엔 "이미 존재합니다" 등의 안내 없음.
- **확인 수준**: 재현.

## USR-04 (치명) 사용자별 모뎀/카테고리 기반 팩스 접근 제한이 완전히 동작하지 않음 — 타 사용자 팩스 전체 노출

- **위치**: `src/namifax/security.py` (`NamiFaxSecurityPolicy.identity()`, 세션에서 만든 identity dict에 `modemdevs`/`faxcats`/`didrouting` 키가 전혀 없음), `src/namifax/views/inbox.py` (`inbox_view`: `devices = None if superuser else identity.get("modemdevs")`), `src/namifax/views/archive.py` (`archive_view` criteria에 modemdevs/categories 자체를 전달하지 않음)
- **증상**: `identity()`가 반환하는 dict는 `{token, user_id, username, is_admin, superuser}`뿐이라 `identity.get("modemdevs")`는 관리자든 일반 사용자든 항상 `None`이 된다. `FaxPDFArchive.viewable_devices()`는 `devices is None`이면 모뎀/부서 제한 조건(`sqlroutes`)을 아예 비워버리므로, DB의 `UserAccount.modemdevs`/`any_modem` 설정과 무관하게 **모든 로그인 사용자가 인박스의 전체 팩스(다른 사용자·다른 모뎀 라인 수신함 포함)를 열람 가능**하다. 아카이브 검색도 동일한 이유로 사용자별 제한 없이 전체 조회가 가능하다.
- **재현**:
  1. `operator` 계정을 `any_modem=0, modemdevs='ttyS0'`로 설정(즉 ttyS0 라인 수신 팩스만 봐야 함).
  2. `ttyS9-not-operators` 모뎀으로 수신된 `fid=401`("SECRET NOT FOR OPERATOR" 설명) 레코드를 DB에 삽입.
  3. `operator`로 로그인해 `GET /inbox` 호출 → 응답 본문에 `"SECRET NOT FOR OPERATOR"` 포함(즉 권한 없는 모뎀 라인의 팩스가 그대로 노출됨).
- **확인 수준**: 재현. (known.md에 유사 항목 없음 — 세션 팩토리 부재(K02)와는 별개의, 세션 정상 동작 상태에서도 발생하는 인가 로직 결함.)

## USR-05 (중간) 팩스 회전(rotate)이 실패해도 항상 성공 응답을 반환

- **위치**: `src/namifax/views/inbox.py` (`fax_rotate_view`, `/faxes/rotate/{fid}`, `/rotate`)
- **증상**: `arc.rotate_fax()`가 내부적으로 "Not in inbox"(이미 보관된 팩스) 또는 "No fid loaded"(존재하지 않는 fid) 이유로 `False`를 반환해도, 뷰는 `try/except Exception: pass`로 결과를 버리고 항상 `{"status": "ok", "fid": ..., "rotation": 90}`, HTTP 200을 반환한다. 클라이언트(JS)는 회전이 실제로 적용됐는지 알 수 없다.
- **재현**: 이미 보관(archive, `inbox=0`)된 `fid=103`에 대해 `GET /faxes/rotate/103` → 200, `{"status":"ok","fid":"103","rotation":90}`. 존재하지 않는 `fid=999999`도 동일하게 `{"status":"ok",...}` 반환.
- **확인 수준**: 재현.

## USR-06 (치명) `/ajax/faxalter`가 인증 없이 접근 가능하고, 파라미터가 셸 명령에 그대로 삽입되어 명령 주입 가능

- **위치**: `src/namifax/routes.py` (`ajax_faxalter` 라우트에 `permission` 미지정), `src/namifax/views/ajax.py` (`ajax_faxalter`), `src/avantfax/services/faxqueue.py` / `src/namifax/services/faxqueue.py` (`FaxQueue.faxalter`: `f'-d "{val}"'` 형태로 문자열 결합 후 `shell_exec()`가 `subprocess.run(cmd, shell=True, ...)` 실행)
- **증상**: 다른 사용자 화면 라우트(`inbox`, `sendfax` 등)는 `permission="view"`/`"send_fax"`가 걸려 있지만 `ajax_faxalter`는 permission이 전혀 설정되지 않아 **로그인하지 않은 익명 사용자도 POST 가능**하다. 게다가 `destination` 등 사용자 입력값이 이스케이프 없이 셸 명령 문자열에 삽입되어 `shell=True`로 실행되므로, 더블쿼트를 포함한 입력으로 임의 명령을 실행할 수 있다.
- **재현**:
  - 익명(`webtest.TestApp`, 로그인 없음) 상태로 `POST /ajax/faxalter` with `jid=12&destination=x" ; touch /tmp/pwned_usr2 ; echo "` 전송 → 200 OK, 실행 후 `/tmp/pwned_usr2` 파일이 실제로 생성됨(파일 시스템에서 직접 확인).
  - 인증 사용자로도 `POST /ajax/faxalter` with `destination=999` → `faxalter -d 999 -P 10 -k 3 -a 1 11` 형태로 별도 스텁 커맨드 로그에 그대로 기록됨(파라미터 인젝션 관제 없음 확인).
- **확인 수준**: 재현. (파일 생성까지 직접 확인함. 테스트 후 `/tmp/pwned_usr2` 삭제함.)

## USR-07 (낮음) 작업 큐 조작(killjob/faxalter)에 요청자와 대상 작업의 소유자 일치 검증이 없음

- **위치**: `src/namifax/views/outbox.py` (`outbox_view`: `kill_jid = request.params.get("kill"); fq.kill_job(kill_jid)`), `src/namifax/services/faxqueue.py`
- **증상**: `outbox_view`는 큐에서 가져온 `jobs`/`failed_jobs`를 화면에 보여줄 때는 `FaxQueue(auto_process=False)`가 소유자 필터링을 하지 않은 전체 큐를 그대로 노출하며(레거시는 `list_owner()`로 본인 작업만 제한), kill 처리 시에도 해당 jid가 요청자 소유인지 검사하지 않고 곧바로 `fq.kill_job(kill_jid)`를 호출한다.
- **증상 재현**: `operator`로 로그인해 `GET /outbox` 호출 시 스텁 `faxstat -s` 출력에 있는 `admin` 소유 job(`#11`)과 `operator` 소유 job(`#12`)이 모두 노출됨(화면에 "Job ID Destination … #11 … #12 …" 둘 다 표시). 이어서 `GET /outbox?kill=11`(admin 소유 job)을 operator 계정으로 호출하면 소유자 검증 없이 `faxalter`/`faxrm` 계열 명령이 그대로 실행됨.
- **확인 수준**: 재현(화면 노출), 소유자 무관 kill 실행은 명령 로그로 간접 확인(추론 보강 재현).

## USR-08 (중간) 모달 액션의 "작성자(lastmoduser)" 기록이 실제 로그인 사용자가 아니라 항상 admin(uid=1)로 기록됨

- **위치**: `src/namifax/views/modals.py` (`modal_note_view`: `identity.get("uid", 1)`), `src/namifax/security.py` (`identity()` 반환 dict에 `uid` 키가 없고 `user_id` 키만 존재)
- **증상**: 보안 정책의 `identity()`는 `{"token","user_id","username","is_admin","superuser"}`만 반환하므로 `identity.get("uid", 1)`은 어떤 사용자로 로그인해도 항상 기본값 `1`(admin)로 떨어진다. 그 결과 메모(note) 작성자 감사 기록(`FaxArchive.lastmoduser`)이 실제 작성자와 무관하게 항상 1로 저장된다.
- **재현**: `operator`(uid=2)로 로그인 후 `POST /note?fid=501` with `description=operator note` → 저장은 성공하지만 `SELECT lastmoduser FROM FaxArchive WHERE fid=501` 결과가 `1`(admin)로 기록됨. 실제 조작자는 operator(uid=2)여야 함.
- **확인 수준**: 재현.

## USR-09 (낮음) `_submit_check` 히든 필드가 모든 폼(24개 템플릿)에 존재하지만 서버에서 전혀 검증되지 않음

- **위치**: `src/namifax/templates/*.jinja2` (`_submit_check` hidden input, 24개 템플릿), 대응하는 `src/namifax/views/*.py` 전체(해당 필드를 읽거나 검사하는 코드 없음)
- **증상**: 레거시 PHP(`sendfax.php`: `if (array_key_exists('_submit_check', $_POST))`)에서는 이 필드가 실제 제출 여부 판별에 쓰였지만, 신규 구현에서는 단순 장식용 hidden 필드로만 남아있고 CSRF 토큰이나 제출 검증 용도로 전혀 사용되지 않는다. `_submit_check` 없이 폼 필드만 보내도 모든 POST 액션이 동일하게 처리됨(본 세션의 모든 재현 테스트가 `_submit_check`를 보내지 않았음에도 전부 정상 처리된 것으로 간접 확인). 진짜 CSRF 보호 수단(토큰/Origin 검증)이 전무하다는 뜻이며, 이 필드는 보호가 있는 것처럼 오인시키는 요소로만 남아있다.
- **확인 수준**: 재현(전 세션의 수십 회 POST가 `_submit_check` 없이도 모두 성공한 것으로 확인) + 추론(정적 grep으로 서버 코드 어디에도 해당 필드 검증 로직 없음을 확인).

---

### 요약

- 총 결함 수: **9건** (USR-01 ~ USR-09)
- 심각도별: 치명 2건(USR-04, USR-06), 높음 2건(USR-01, USR-02), 중간 3건(USR-03, USR-05, USR-08), 낮음 2건(USR-07, USR-09)
- 가장 중요한 5건:
  1. USR-04 — 사용자별 모뎀/카테고리 접근 제한 완전 미작동, 타 사용자 팩스 전체 노출
  2. USR-06 — `/ajax/faxalter` 인증 없이 접근 가능 + 셸 명령 주입으로 임의 명령 실행
  3. USR-02 — 검색/조회 0건일 때 가짜 placeholder 데이터를 실제 결과처럼 표시
  4. USR-01 — 아카이브에서 날짜/카테고리/송수신 단독 필터 사용 시 결과 테이블이 항상 숨겨짐
  5. USR-03 — 주소록/이메일북/배포목록 생성 폼이 유효성 오류를 삼키고 무조건 성공 처리
