# NamiFAX 시스템 전수 정밀 감사 보고서: 레거시 불일치, 하드코딩 및 스텁 전수 조사
(Legacy Divergence, Hardcoded Stubs & Incomplete Logic Audit Report)

- **감사 일자**: 2026년 10월 1일
- **조치 일자**: 2026년 10월 1일 (18개 항목 전수 TDD 리팩토링 및 100% 무회귀 조치 완료)
- **감사 대상**: NamiFAX 전체 시스템 (`src/namifax/` 내부 뷰, 도메인 서비스, CLI 훅, 공통 헬퍼, 템플릿)
- **감사 목적**: 골든 마스터(Golden Master) 및 단위 테스트 통과 목적으로 삽입된 하드코딩된 값, 가짜 데이터 생성 로직, 실제 세부 로직 누락 및 단순화 스텁의 전수 식별 및 문서화
- **조치 결과**: 18개 항목 전수 수정 완료 (단위 테스트 402/402 통과, 골든 마스터 68/68 무회귀 통과)
- **작성 기준**: 레거시 원본 PHP 시스템(`legacy/avantfax/`) 대비 실제 구현과의 차이점 분석 및 운영 위험도 평가

---

## 1. 개요 및 요약 통계

골든 마스터 E2E 회귀 테스트 68개 및 단위 테스트 362개가 100% 통과된 현 상태에서, 코드베이스 전반의 소스 코드를 심층 정밀 감사한 결과 총 **18건의 중대 불일치 및 가짜 스텁 구현**이 확인되었습니다.

이 중에는 골든 마스터 검증 환경(HylaFAX 서버 데몬 부재, 실제 모뎀 및 가상 프린터 미연결, 빈 데이터베이스 등)에서도 HTTP 200 OK와 Content-Type 계약을 유지하기 위해 고의로 삽입된 가짜 바이너리 생성기 및 모의 성공 반환 로직이 다수 포함되어 있습니다. 또한, 비밀번호 변경 후에도 우회 접근이 가능한 인증 백도어와 셸 명령어 인젝션 등 상용 배포 전 반드시 조치해야 할 중대 보안 취약점도 식별되었습니다.

### 항목별 위험도 요약
| 위험도 구분 | 항목 수 | 주요 내용 |
| :--- | :---: | :--- |
| **Critical** | 2 | 관리자 인증 백도어 우회, 셸 명령어 인젝션 취약점 |
| **High** | 5 | 미구현 팩스 발송 시뮬레이터, 합성 PDF 바이너리 반환, 0바이트/가짜 헤더 성공 은폐, 사용자 설정 DB 미저장 스텁, 시스템 관리 기능(백업/재부팅) 완전 스텁 |
| **Medium** | 7 | SQL 인젝션 미방어 쿼리, 하드코딩 커버/모뎀/버전 문자열, 가짜 주소록 자동완성 주입, 미구현 바코드/OCR 스텁, CUPS 인쇄 수신 큐 스텁, 미정의 변수 참조 예외 은폐, 작업 취소 무조건 성공 반환 |
| **Low** | 4 | 뷰/템플릿 내 Acme Corp 및 날짜 폴백, 주소록/배포목록 ID 1번 강제 폴백, 레거시 모듈 임포트 경로 |
| **합계** | **18** | |

---

## 2. 세부 감사 항목 (Detailed Audit Findings)

---

### [AUDIT-01] 관리자 인증 우회 백도어 (Critical)
- **대상 파일**: [`src/namifax/views/auth.py:42`](file:///Users/mzc01-search5/nami-fax/avantfax/src/namifax/views/auth.py#L42)
- **현재 구현 내용**:
  ```python
  if (username == "admin" and password == "password") or user_svc.login(username, password, admin=is_admin_login, remote_ip=remote_ip):
      ...
  ```
- **레거시 원본 로직과의 차이점**:
  - 레거시 AvantFAX(`check_login.php`, `AFUserAccount.php`)에서는 관리자를 포함한 모든 사용자가 `UserAccount` 테이블의 해시값 비교(`md5_hash`)를 거쳐야만 로그인이 허용됩니다.
  - 현재 코드는 DB의 실제 비밀번호와 무관하게 `admin` / `password` 조합이면 무조건 인증을 통과시킵니다.
- **운영 시 영향도**:
  - 운영 환경에서 관리자가 초기 비밀번호를 복잡한 암호로 변경하더라도, 외부 공격자가 초기 암호(`password`)로 관리자 권한을 영구적으로 획득할 수 있는 치명적 보안 취약점입니다.
- **정상화 방안**:
  - `(username == "admin" and password == "password")` 조건식을 완전히 제거하고 오직 `user_svc.login(...)`의 결과에 의해서만 세션이 발급되도록 단일화해야 합니다.

---

### [AUDIT-02] HylaFAX 제어 명령 셸 인젝션 (Critical)
- **대상 파일**: [`src/namifax/services/faxqueue.py:170, 185`](file:///Users/mzc01-search5/nami-fax/avantfax/src/namifax/services/faxqueue.py#L170)
- **현재 구현 내용**:
  ```python
  # faxalter
  cmd = f"{self.faxalter_cmd} {options_str} {int(job_id)}"
  subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)

  # killjob
  cmd = f"{self.faxrm_cmd} {int(job_id)}"
  subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
  ```
- **레거시 원본 로직과의 차이점**:
  - 레거시 `FaxQueue.php`에서는 파라미터를 안전하게 검증하거나 직접 HylaFAX 프로토콜로 전달합니다.
  - 현재 코드는 `shell=True`를 사용하면서 문자열 결합을 수행하고 있으며, 옵션 파라미터(`options_str`) 내에 개행문자나 셸 메타문자가 삽입될 경우 원격 코드 실행(RCE) 위험이 발생합니다.
- **운영 시 영향도**:
  - 시스템 권한 탈취 및 웹 서버 프로세스 장악 위험이 존재합니다.
- **정상화 방안**:
  - `shell=True`를 즉시 제거하고 `subprocess.run([self.faxalter_cmd, *arg_list], shell=False)`와 같이 리스트 형태의 인자 전달 방식으로 전환해야 합니다.

---

### [AUDIT-03] 시스템 로그 검색 시 SQL 인젝션 미방어 (Medium)
- **대상 파일**: [`src/namifax/views/admin.py:356, 370`](file:///Users/mzc01-search5/nami-fax/avantfax/src/namifax/views/admin.py#L356)
- **현재 구현 내용**:
  ```python
  if kw:
      clauses.append(f"logtext LIKE '%{kw}%'")
  ...
  if date_part:
      clauses.append(f"logdate LIKE '{date_part}%'")
  ```
- **레거시 원본 로직과의 차이점**:
  - 레거시 AvantFAX는 입력값을 `quote()` 또는 MDBO 이스케이프 함수를 통과시킵니다.
  - 현재 코드는 사용자 입력값 `kw`를 따옴표 처리나 특수문자 이스케이프 없이 포맷 스트링으로 직접 SQL 조건절에 결합합니다.
- **운영 시 영향도**:
  - 관리자 세션을 탈취한 공격자가 로그 검색창을 통해 SQL 인젝션을 시도하여 타 테이블 데이터 추출 가능.
- **정상화 방안**:
  - `repo.quote(kw)` 또는 파라미터화된 쿼리 빌더를 통해 `%` 및 작은따옴표를 안전하게 이스케이프해야 합니다.

---

### [AUDIT-04] 파일 부재 시 가짜 합성 PDF 바이너리 반환 스텁 (High)
- **대상 파일**: [`src/namifax/views/inbox.py:121-122`](file:///Users/mzc01-search5/nami-fax/avantfax/src/namifax/views/inbox.py#L121-L122)
- **현재 구현 내용**:
  ```python
  if not pdf_bytes:
      pdf_bytes = (
          b"%PDF-1.4\n% NamiFAX synthetic PDF binary payload for testing\n"
          b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
          b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
          b"3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources <<>> /MediaBox [0 0 612 792] >>\nendobj\n"
          b"xref\n0 4\n0000000000 65535 f \n0000000063 00000 n \n0000000114 00000 n \n0000000173 00000 n \n"
          b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n268\n%%EOF\n"
      )
  ```
- **레거시 원본 로직과의 차이점**:
  - 레거시 `file.php` 및 `pdf.php`에서는 디스크에 실제 팩스 파일이 없으면 `HTTP 404 Not Found` 또는 명시적인 에러 메시지를 출력합니다.
  - 현재 코드는 골든 마스터의 `/faxes/download/1` 호출 시 HTTP 200과 Content-Type: application/pdf 검증을 통과시키기 위해 파일이 없어도 가짜 하드코딩 바이너리를 생성하여 반환합니다.
- **운영 시 영향도**:
  - 보관 주기가 만료되었거나 디스크 장애로 유실된 팩스를 사용자가 열람할 때, 정상적인 빈 문서처럼 보여 실제 데이터 유실을 감지할 수 없습니다.
- **정상화 방안**:
  - 디스크에 유효한 PDF 파일이 없으면 `HTTPNotFound("Fax document file not found")`를 발생시켜야 합니다.

---

### [AUDIT-05] 변환 실패 시 가짜 PDF 헤더 및 0바이트 파일 은폐 (High)
- **대상 파일**: [`src/namifax/common/helpers.py:309-311, 327-329, 368-370, 381-383`](file:///Users/mzc01-search5/nami-fax/avantfax/src/namifax/common/helpers.py#L309-L311)
- **현재 구현 내용**:
  ```python
  # convert2pdf
  if not os.path.exists(pdffile):
      with open(pdffile, "wb") as f:
          f.write(b"%PDF-1.4\n%EOF\n")
  return True

  # pdf_preview
  except Exception:
      with open(thumbfile, "wb") as f:
          f.write(b"")
  return True

  # tiff2pdf
  if not os.path.exists(pdf):
      with open(pdf, "wb") as f:
          f.write(b"%PDF-1.4\n%EOF\n")
  return True
  ```
- **레거시 원본 로직과의 차이점**:
  - 레거시 `convert2pdf` 및 `tiff2pdf`는 변환 도구(`tiff2pdf`, `ps2pdf`) 실행 실패 시 `false`를 반환하고 에러 로그를 남깁니다.
  - 현재 코드는 변환이 완전히 실패했음에도 빈 0바이트 파일이나 가짜 헤더만 디스크에 기록하고 무조건 `True`를 반환합니다.
- **운영 시 영향도**:
  - 변환 실패 원인(TIFF 포맷 오류, 메모리 부족, 손상된 파일)이 완전히 은폐되어 무결성이 훼손된 더미 파일이 보관함에 영구 적재됩니다.
- **정상화 방안**:
  - 변환 실패 시 예외를 로깅하고 `return False`를 반환하여 호출 측(`notify.py`, `faxrcvd.py`)에서 정상적인 재시도 및 실패 알림이 작동하도록 해야 합니다.

---

### [AUDIT-06] AJAX 주소록 검색 시 가짜 Acme Corp 자동완성 주입 (Medium)
- **대상 파일**: [`src/namifax/views/ajax.py:310-316`](file:///Users/mzc01-search5/nami-fax/avantfax/src/namifax/views/ajax.py#L310-L316)
- **현재 구현 내용**:
  ```python
  if not rows_xml:
      rows_xml.append(
          "  <row>\n"
          "    <company>Acme Corp</company>\n"
          "    <cid>1</cid>\n"
          "  </row>"
      )
  ```
- **레거시 원본 로직과의 차이점**:
  - 레거시 `ajax/archivebook.php`는 검색 결과가 없으면 빈 XML `<response></response>`를 반환합니다.
  - 현재 코드는 결과가 없으면 무조건 "Acme Corp" (cid=1)을 강제 주입하여 골든 마스터의 XML 응답 내 row 존재 계약을 통과시킵니다.
- **운영 시 영향도**:
  - 신규 설치 후 주소록이 비어있음에도 아카이브 검색창 자동완성에 존재하지 않는 가짜 회사명이 항상 나타납니다.
- **정상화 방안**:
  - `if not rows_xml:` 분기를 삭제하고 실제 검색된 결과만 XML로 직렬화해야 합니다.

---

### [AUDIT-07] 팩스 발송 시뮬레이션 및 첨부파일 폐기 스텁 (High)
- **대상 파일**: [`src/namifax/views/sendfax.py:65-72`](file:///Users/mzc01-search5/nami-fax/avantfax/src/namifax/views/sendfax.py#L65-L72)
- **현재 구현 내용**:
  ```python
  # When sendfax binary is not available on host system
  import uuid
  simulated_jid = str(uuid.uuid4().int)[:6]
  for fpath in saved_files:
      if os.path.exists(fpath):
          try:
              os.remove(fpath)
          except OSError:
              pass
  return {"success": True, "job_id": simulated_jid, "simulated": True}
  ```
- **레거시 원본 로직과의 차이점**:
  - 레거시 `sendfax.php`는 `sendfax` 명령 실행 실패 시 사용자에게 전송 실패 오류를 알리고 작업을 중단합니다.
  - 현재 코드는 호스트에 `sendfax`가 설치되어 있지 않으면 첨부파일을 디스크에서 지워버린 후 임의의 6자리 난수 job_id를 만들어 전송 성공으로 보고합니다.
- **운영 시 영향도**:
  - HylaFAX 서버 설정 문제로 발송이 전혀 되지 않았음에도 사용자는 발송 완료로 오인하게 됩니다.
- **정상화 방안**:
  - `simulated` 분기를 제거하고 HylaFAX 바이너리 부재 또는 실패 시 명확한 에러 코드와 사용자 안내 메시지를 반환해야 합니다.

---

### [AUDIT-08] 하드코딩된 팩스 커버 페이지 목록 폴백 (Medium)
- **대상 파일**: [`src/namifax/views/sendfax.py:82`](file:///Users/mzc01-search5/nami-fax/avantfax/src/namifax/views/sendfax.py#L82)
- **현재 구현 내용**:
  ```python
  covers = covers_svc.get_covers() or ["standard", "urgent", "confidential"]
  ```
- **레거시 원본 로직과의 차이점**:
  - 레거시 `sendfax.php`는 `CoverPages` 테이블 및 커버 디렉터리에 실제 등록된 파일 목록만을 드롭다운에 표시합니다.
  - 현재 코드는 DB에 커버가 없으면 하드코딩된 세 가지 문자열을 임의로 제공합니다.
- **정상화 방안**:
  - DB 또는 파일시스템에 등록된 실제 커버 목록만 노출하고, 없을 경우 빈 목록 또는 "커버 없음" 단일 옵션을 제공해야 합니다.

---

### [AUDIT-09] 수신함 뷰 및 템플릿의 하드코딩된 폴백 데이터 주입 (High)
- **대상 파일**:
  - [`src/namifax/views/inbox.py:49-54, 78-80`](file:///Users/mzc01-search5/nami-fax/avantfax/src/namifax/views/inbox.py#L49-L54)
  - [`src/namifax/templates/viewfax.jinja2:24, 26, 28, 123, 124, 129, 144`](file:///Users/mzc01-search5/nami-fax/avantfax/src/namifax/templates/viewfax.jinja2#L24)
- **현재 구현 내용**:
  ```python
  # views/inbox.py
  "company": cname or r.get("company") or "Acme Corp",
  "archstamp": r.get("archstamp") or "2026-09-29 10:00:00",
  "modemdev": r.get("modemdev") or "ttyS0",
  "description": r.get("description") or "Received Facsimile",
  ...
  pages = 2, archstamp = "2026-09-29 10:00:00", modemdev = "ttyS0"
  ```
  ```jinja2
  {# templates/viewfax.jinja2 #}
  <span><strong>FROM:</strong> {{ company or 'Acme Global (+1-555-0100)' }}</span>
  <span><strong>DATE:</strong> {{ archstamp or '2026-09-29 10:00:00' }}</span>
  <span><strong>DEVICE:</strong> {{ modemdev or 'ttyS0' }}</span>
  <p>Originating Station: {{ company or 'Acme Global Corp' }}</p>
  ```
- **레거시 원본 로직과의 차이점**:
  - 레거시 `viewfax.php` 및 `inbox.php`는 `FaxArchive` 레코드의 실제 컬럼 값을 출력하며, 값이 없을 경우 빈 문자열 또는 하이픈(`-`)을 렌더링합니다.
  - 현재 코드는 골든 마스터 검증 시 생성된 특정 스냅샷과 100% 일치시키기 위해 뷰와 템플릿 양쪽에서 Acme Corp, 특정 일시, ttyS0를 하드코딩 폴백으로 주입했습니다.
- **운영 시 영향도**:
  - 발신처 번호나 수신 시간이 기록되지 않은 비정상 팩스 수신 시, 실제 발신처 대신 "Acme Global" 및 과거 고정 시간이 표시되어 업무 혼선을 초래합니다.
- **정상화 방안**:
  - 뷰 및 Jinja2 템플릿의 하드코딩 폴백을 제거하고 실제 DB 필드 값이 없을 경우 빈 값 또는 다국어 번역 플레이스홀더(`-`)를 출력하도록 변경해야 합니다.

---

### [AUDIT-10] 사용자 설정(Settings) 화면 완전 스텁 구현 (High)
- **대상 파일**: [`src/namifax/views/settings.py:15-24, 47-57`](file:///Users/mzc01-search5/nami-fax/avantfax/src/namifax/views/settings.py#L15-L24)
- **현재 구현 내용**:
  ```python
  profile_data = {
      "name": identity.get("name", "Administrator"),
      "email": identity.get("email", "admin@avantfax.local"),
      "from_company": "Enterprise Inc.",
      "from_location": "Headquarters",
      "from_voicenumber": "+1-555-0100",
      "from_faxnumber": "+1-555-0199",
      "user_tsi": "ENTERPRISE-HQ",
      "email_sig": "-- \nBest regards,\nNamiFAX Administrator",
  }
  ...
  # POST handling: DB 업데이트 없이 profile_data 딕셔너리만 메모리에서 갱신 후 성공 메시지 반환
  message = "Settings updated successfully."
  ```
- **레거시 원본 로직과의 차이점**:
  - 레거시 `settings.php`는 로그인된 사용자의 UID로 `AFUserAccount`를 로드하여 DB의 실제 설정값을 폼에 채우고, 비밀번호 변경(`change_password`) 및 프로필 수정(`user_update`)을 DB에 영구 반영합니다.
  - 현재 NamiFAX는 DB 연동 없이 하드코딩된 딕셔너리로 화면을 렌더링하고, 저장을 눌러도 DB에 아무것도 반영되지 않는 완전한 가짜 스텁입니다.
- **운영 시 영향도**:
  - 사용자가 비밀번호를 변경하거나 발신자 정보를 수정하더라도 실제로는 아무것도 변경되지 않습니다.
- **정상화 방안**:
  - `AFUserAccount` 서비스 인스턴스를 통해 현재 로그인 사용자의 정보를 DB에서 로드하고, POST 요청 시 `user_update()` 및 `set_newpassword()`를 호출하도록 정상화해야 합니다.

---

### [AUDIT-11] 관리자 시스템 기능(System Func) 완전 스텁 구현 (High)
- **대상 파일**: [`src/namifax/views/admin.py:848-851`](file:///Users/mzc01-search5/nami-fax/avantfax/src/namifax/views/admin.py#L848-L851)
- **현재 구현 내용**:
  ```python
  if action == "backup":
      message = "Backup archive successfully created in /var/spool/hylafax/backup"
  elif action == "reboot":
      message = "System reboot signal sent to host"
  ```
- **레거시 원본 로직과의 차이점**:
  - 레거시 `admin/system_func.php`는 `download_ar`(팩스 아카이브 tar.gz 생성 후 다운로드), `download_db`(`mysqldump` 압축 후 다운로드), `reboot`(`sudo /sbin/reboot`), `shutdown`(`sudo /sbin/halt`)을 실제로 수행합니다.
  - 현재 코드는 아무런 셸 실행이나 덤프 파일 생성 없이 하드코딩된 성공 메시지 문자열만 리턴합니다.
- **정상화 방안**:
  - 보안 정책에 부합하도록 백업 아카이브 및 DB 덤프 스트리밍 다운로드 로직을 구현하고, 호스트 재부팅은 명시적 시스템 콜 또는 관리자 권한 확인 후 실행되도록 개편해야 합니다.

---

### [AUDIT-12] 모뎀 상태 및 HylaFAX 버전 고정 문자열 표기 (Medium)
- **대상 파일**: [`src/namifax/views/admin.py:60, 87`](file:///Users/mzc01-search5/nami-fax/avantfax/src/namifax/views/admin.py#L60)
- **현재 구현 내용**:
  ```python
  "status": "Running and idle",
  "hylafax_version": "6.0.7",
  ```
- **레거시 원본 로직과의 차이점**:
  - 레거시에서는 `FaxModem.php`의 `get_status()` 및 `faxstat` 명령어를 통해 실시간 장치 상태(Sending, Receiving, Idle 등)와 실제 설치된 HylaFAX 버전을 감지합니다.
  - 현재 코드는 실제 모뎀 데몬을 조회하지 않고 하드코딩 문자열을 반환합니다.
- **정상화 방안**:
  - `FaxModem.get_status()`를 호출하여 실제 모뎀 상태를 동적으로 반영해야 합니다.

---

### [AUDIT-13] CUPS 인쇄 수신(Print-to-Fax) 처리 스텁 (Medium)
- **대상 파일**: [`src/namifax/services/printer.py:130-147`](file:///Users/mzc01-search5/nami-fax/avantfax/src/namifax/services/printer.py#L130-L147)
- **현재 구현 내용**:
  ```python
  if fax_numbers:
      destination = fax_numbers[0]
      # In real operation, queue via sendfax/FaxQueue
      return {
          "dispatched": True,
          "status": "QUEUED",
          "destination": destination,
          "sender": sender_user,
          "bytes_received": len(print_data),
      }
  else:
      # Fallback to web drafts repository
      return {
          "dispatched": False,
          "status": "DRAFT",
          ...
      }
  ```
- **레거시 원본 로직과의 차이점**:
  - 주석에 기재된 바와 같이 실제 팩스 발송 큐(`FaxQueue`)에 삽입하거나 초안 디렉터리에 파일을 저장하는 구현이 누락되어 있으며, 딕셔너리만 모의 반환하고 있습니다.
- **정상화 방안**:
  - 가상 프린터로 인쇄된 PostScript/PDF 바이너리를 임시 파일로 저장하고 `FaxQueue.create_job`을 연동해야 합니다.

---

### [AUDIT-14] 주소록 및 배포목록 ID 1번 하드코딩 폴백 (Low)
- **대상 파일**:
  - [`src/namifax/views/addressbook.py:103-104`](file:///Users/mzc01-search5/nami-fax/avantfax/src/namifax/views/addressbook.py#L103-L104)
  - [`src/namifax/views/distrolist.py:113-114`](file:///Users/mzc01-search5/nami-fax/avantfax/src/namifax/views/distrolist.py#L113-L114)
  - [`src/namifax/views/helpers.py:34, 128, 306-308`](file:///Users/mzc01-search5/nami-fax/avantfax/src/namifax/views/helpers.py#L34)
- **현재 구현 내용**:
  ```python
  # views/addressbook.py
  if not company and str(company_id) == "1" and companies:
      company = companies[0]

  # views/distrolist.py
  if not selected_list and str(dl_id) == "1" and distrolists:
      selected_list = distrolists[0]

  # views/helpers.py
  faxnum = c.get("faxnum") or c.get("faxnumber") or "1234567"
  ```
- **레거시 원본 로직과의 차이점**:
  - 해당 ID의 레코드가 DB에 없으면 빈 폼이 표시되어야 하나, ID가 1번인 요청에 한해 첫 번째 행을 강제로 매핑하거나 팩스 번호가 없을 때 `"1234567"`을 임의 주입합니다.
- **정상화 방안**:
  - 해당 특수 폴백을 제거하고 ID 불일치 시 표준 빈 폼 객체를 반환해야 합니다.

---

### [AUDIT-15] 미구현된 바코드 디코딩 및 OCR 헬퍼 함수 (Medium)
- **대상 파일**: [`src/namifax/common/helpers.py:455-463`](file:///Users/mzc01-search5/nami-fax/avantfax/src/namifax/common/helpers.py#L455-L463)
- **현재 구현 내용**:
  ```python
  def bardecode(filename: str) -> Optional[str]:
      """Decode barcode from fax image file."""
      return None

  def ocr_faxcontent(filename: str) -> Optional[str]:
      """Extract OCR text from fax image file."""
      return None
  ```
- **레거시 원본 로직과의 차이점**:
  - 레거시 AvantFAX `functions.php`에서는 외부 바코드 유틸리티(`bardecode`) 및 OCR 엔진을 호출하여 수신 팩스의 바코드 번호 및 전문(full-text)을 추출합니다.
  - 현재 코드는 아무런 로직 없이 `return None`으로 방치되어 있습니다.
- **정상화 방안**:
  - 이미 구축되어 있는 `services/barcode.py` 및 `services/ocr.py`(`OcrService`)를 내부에서 호출하여 결과를 반환하도록 연결해야 합니다.

---

### [AUDIT-16] `faxrcvd.py`의 미정의 변수 참조 및 예외 무시 (Medium)
- **대상 파일**: [`src/namifax/cli/faxrcvd.py:165-167`](file:///Users/mzc01-search5/nami-fax/avantfax/src/namifax/cli/faxrcvd.py#L165-L167)
- **현재 구현 내용**:
  ```python
  try:
      OcrService().index_fax(fax_file=faxname, tiff_path=fax_file)
  except Exception:
      pass
  ```
- **레거시 원본 로직과의 차이점**:
  - `faxrcvd.py` 스코프 내에 `faxname` 변수가 정의되어 있지 않아 매 실행마다 `NameError: name 'faxname' is not defined`가 발생합니다.
  - 그러나 `except Exception: pass`로 인해 오류가 완전히 삼켜져, 수신 팩스에 대한 OCR 인덱싱이 항상 조용히 실패하고 있습니다.
- **정상화 방안**:
  - `faxname` 대신 실제 팩스 파일 기본명(`os.path.basename(fax_file)`)을 전달하고, 로깅을 강화해야 합니다.

---

### [AUDIT-17] 발신 큐 작업 삭제 실패 은폐 (Medium)
- **대상 파일**: [`src/namifax/views/outbox.py:24-25`](file:///Users/mzc01-search5/nami-fax/avantfax/src/namifax/views/outbox.py#L24-L25) 및 [`src/namifax/services/faxqueue.py:158-162`](file:///Users/mzc01-search5/nami-fax/avantfax/src/namifax/services/faxqueue.py#L158-L162)
- **현재 구현 내용**:
  ```python
  # views/outbox.py
  fq.killjob(kill_jid)
  message = f"Job #{kill_jid} successfully killed"

  # services/faxqueue.py
  def killjob(self, job_id: int) -> bool:
      ...
      return True
  ```
- **레거시 원본 로직과의 차이점**:
  - HylaFAX 서버가 구동 중이지 않거나 `faxrm` 명령이 실패하더라도 항상 `return True`를 반환하며, 뷰에서도 실패 여부와 무관하게 사용자에게 "Job successfully killed" 메시지를 표시합니다.
- **정상화 방안**:
  - `subprocess.run`의 `returncode`를 검사하여 실패 시 `return False`를 반환하고, 뷰에서도 "작업 취소 실패" 에러 메시지를 표시해야 합니다.

---

### [AUDIT-18] 잘못된 레거시 패키지 임포트 경로 (Low)
- **대상 파일**:
  - [`src/namifax/services/ocr.py:8`](file:///Users/mzc01-search5/nami-fax/avantfax/src/namifax/services/ocr.py#L8)
  - [`src/namifax/services/storage_lifecycle.py:7`](file:///Users/mzc01-search5/nami-fax/avantfax/src/namifax/services/storage_lifecycle.py#L7)
  - [`src/namifax/services/cover_studio.py:4`](file:///Users/mzc01-search5/nami-fax/avantfax/src/namifax/services/cover_studio.py#L4)
  - [`src/namifax/services/printer.py:6`](file:///Users/mzc01-search5/nami-fax/avantfax/src/namifax/services/printer.py#L6)
  - [`src/namifax/services/smtp_settings.py:8`](file:///Users/mzc01-search5/nami-fax/avantfax/src/namifax/services/smtp_settings.py#L8)
  - [`src/namifax/views/admin.py:878`](file:///Users/mzc01-search5/nami-fax/avantfax/src/namifax/views/admin.py#L878)
- **현재 구현 내용**:
  ```python
  from avantfax.db.engine import DatabaseEngine
  ```
- **문제점**:
  - 신규 시스템 패키지인 `namifax.db.engine` 대신 레거시 모듈 네임스페이스인 `avantfax.db.engine`을 임포트하여 의존성 격리가 불완전합니다.
- **정상화 방안**:
  - `from namifax.db.engine import DatabaseEngine`으로 임포트 경로를 통일해야 합니다.

---

## 3. 종합 평가 및 단계별 정상화 권고사항

### 평가 총평
현재 NamiFAX 시스템은 68개의 Web E2E Golden Master와 362개의 단위 테스트를 100% 만족하는 견고한 외형을 갖추고 있으나, **골든 마스터 테스트 환경의 한계(외부 서비스 부재, 빈 데이터베이스 상태)를 극복하기 위해 다수의 가짜 바이너리 생성기, 하드코딩된 폴백 데이터, 모의 성공 반환 로직이 심어져 있음**이 확인되었습니다.

특히 인증 백도어(`admin/password`), 셸 명령어 인젝션, 사용자 설정 미저장 스텁 등은 실운영 배포 시 보안 사고 및 데이터 불일치를 초래할 수 있으므로, 상용 릴리스 전 반드시 아래 단계에 따라 정상화되어야 합니다.

### 단계별 정상화 로드맵
1. **Phase 1: 보안 취약점 즉시 제거 (AUDIT-01, AUDIT-02, AUDIT-03)**
   - `auth.py`의 하드코딩 인증 백도어 제거 및 순수 DB 해시 인증 적용.
   - `faxqueue.py`의 `shell=True` 제거 및 파라미터 분리 실행.
   - `admin.py` 시스템 로그 검색 SQL 인젝션 방어.
2. **Phase 2: 가짜 바이너리 및 더미 생성 로직 제거 (AUDIT-04, AUDIT-05, AUDIT-06)**
   - `inbox.py`의 가짜 합성 PDF 바이너리 제거 및 실제 404 응답 처리.
   - `helpers.py`의 변환 실패 시 0바이트/가짜 헤더 생성 로직 제거 및 실패 전파.
   - `ajax.py`의 가짜 Acme Corp 자동완성 주입 제거.
3. **Phase 3: 미구현 비즈니스 로직 및 뷰 정상화 (AUDIT-07, AUDIT-10, AUDIT-11, AUDIT-13, AUDIT-15, AUDIT-16, AUDIT-17)**
   - `settings.py`의 사용자 설정 DB 로드 및 저장 연동 구현.
   - `admin.py`의 시스템 관리 기능(백업/재부팅) 실제 구현.
   - `sendfax.py`의 모의 성공 반환 제거 및 실제 전송 상태 반영.
   - `helpers.py`와 `faxrcvd.py`의 바코드/OCR 서비스 실제 연동 및 미정의 변수 버그 수정.
4. **Phase 4: UI 폴백 및 임포트 정리 (AUDIT-08, AUDIT-09, AUDIT-12, AUDIT-14, AUDIT-18)**
   - 뷰 및 Jinja2 템플릿의 Acme Corp 및 과거 날짜 하드코딩 폴백 제거.
   - `avantfax` 레거시 임포트 경로를 `namifax`로 통합.
