---
title: HylaFAX 연동 설치 가이드
type: source
updated: 2026-10-02
sources: [docs/INSTALL_HYLAFAX.md]
verified: false
---

## 요약

NamiFAX와 HylaFAX를 연결하는 7단계 설치 절차. 원본 AvantFAX 설치 스크립트(`debian-install.sh`, `setup-postfix.sh`)의 작업을 이식했으며, 이 저장소에서는 실제 HylaFAX와 연결하여 시험하지 못했다. 훅 스크립트 연결, 웹 서비스 설정, 선택적 사용자 동기화, 주기 작업 설정, 이메일 팩스 전송, 파일 권한, 설치 후 점검을 다룬다.

## 핵심 내용

### 0단계: 환경 파일
- `/etc/namifax.env`(모드 0640)에 DB 접속과 설정을 저장
- 훅 스크립트와 서비스가 같은 파일을 읽음
- 주요 변수: `DATABASE_URL`, `NAMIFAX_SESSION_SECRET`, `NAMIFAX_SECRET_KEY`, `ENABLE_DID_ROUTING`, `FAXMAILUSER`, `WWWUSER`
- HylaFAX가 기본 위치에 없으면 `HYLASPOOL`, `HYLAFAX_PREFIX`, `BINARYDIR`로 지정

### 1단계: 훅 연결 (필수)
- `deploy/hylafax/bin/*`(faxrcvd, dynconf, notify, faxcover)를 `/var/spool/hylafax/bin/`에 복사하고 실행 권한 설정
- 각 모뎀 설정 파일에 `deploy/hylafax/config.namifax`의 세 줄 추가
- 서버 설정(`/var/spool/hylafax/etc/config`)에 `JobFmt`(NamiFAX가 읽는 열 순서), `NotifyCmd`, `CoverCmd` 줄 추가
- **주의**: `JobFmt`는 NamiFAX가 읽는 열 순서와 정확히 일치해야 함. 다르면 출력함 목록이 어긋나거나 비어 보임
- HylaFAX 재시작: `systemctl restart hylafax`(배포판에 따라 `faxq`, `hfaxd`, `faxgetty`)
- 확인: `sudo -u uucp /var/spool/hylafax/bin/dynconf ttyS0 5551234`가 아무것도 출력하지 않고 끝나야 함

### 2단계: 웹 서비스
- `deploy/systemd/namifax.service`를 `/etc/systemd/system/`에 두고 `systemctl enable --now namifax`
- 앞단 웹 서버: `deploy/nginx/namifax.conf` 또는 `deploy/apache/namifax.conf` 설정
- HTTPS 사용 시 `session.secure = true`
- 프록시 뒤에서는 `X-Forwarded-Host` 헤더 필요(변경 요청 출처 검사용)
- 첫 관리자 생성: `namifax createuser -u admin -e you@example.com`

### 3단계: 사용자 동기화 (선택)
- HylaFAX 서버에 사용자 이름 등록 필요(`faxrm`, `faxalter`가 그 사용자의 작업 처리)
- `deploy/sudoers.d/namifax`를 `/etc/sudoers.d/namifax`로 복사(모드 0440, `visudo -cf`로 확인)
- `/etc/namifax.env`에 `HYLAFAX_USER_SYNC=1`
- `deploy/systemd/namifax.service`의 `NoNewPrivileges=true`를 `false`로 변경
- **주의**: `faxadduser`는 비밀번호를 명령줄 인자로 받으므로, 같은 서버의 다른 사용자가 `ps`로 볼 수 있음. 서버에 다른 사용자가 없는 전용 장비에서만 켜기

### 4단계: 주기 작업
- 관리자 > 예약 작업(`/admin/scheduler`)에서 설정
- 임시 폴더 정리, 받은 팩스함 보관 이동, 보존 기간 정책, 전화번호부 내보내기 등
- 각 작업은 "지금 실행", 마지막 실행 결과, 스케줄러 상태/정지/시작 버튼 표시
- 내장 스케줄러(`NAMIFAX_ENABLE_SCHEDULER=1`, 기본) 또는 `namifax scheduler` 별도 서비스 운영
- **중요**: 내장 스케줄러는 임시 파일 정리만. 받은 팩스함 보관(`-i`)과 삭제(`-d`)는 cron에 기입해야 함 (아니면 팩스가 영원히 쌓임)
- `deploy/cron.d/namifax`를 `/etc/cron.d/namifax`로 복사

### 5단계: 이메일로 팩스 보내기 (선택)
- `deploy/postfix/setup-email2fax.md` 참고
- 원본의 `setup-postfix.sh` 설정을 이식했으며, 이 저장소 스크립트는 시스템 파일을 직접 고치지 않음
- 적용 전에 내용을 읽고 직접 넣을 것

### 6단계: 파일 권한
- 보관 폴더(`/var/spool/hylafax/archive`, `…/sent`)는 훅 실행 사용자와 웹 서비스 사용자 모두 쓸 수 있어야 함. 같은 `uucp`로 돌리면 가장 단순
- 임시 폴더(`AVANTFAX_TMPDIR`)도 같음
- `/etc/namifax.env`는 서비스 사용자만 읽게(0640). DB 비밀번호와 세션 키 포함

### 7단계: 설치 뒤 점검 순서
1. 로그인 → 설정 → 시스템 로그에서 오류 확인
2. 관리자 > 모뎀에서 모뎀 생성 후 상태가 `Running and idle` 확인(`faxstat` 읽음)
3. 시험 팩스 전송 후 출력함에 작업 나타남, 완료 뒤 `notify`가 보관함에 보낸 팩스 생성 확인
4. 시험 팩스 수신 후 `faxrcvd`가 받은 팩스함에 올림(썸네일, PDF, 메일 알림)
5. 관리자 화면 대시보드의 HylaFAX 버전 표시 확인(`faxstat -i`)

## 문서가 주장하는 수치·상태

- 경로 가정: NamiFAX는 `/opt/namifax`(가상환경 `.venv`), HylaFAX 스풀은 `/var/spool/hylafax`, 서비스 사용자는 `uucp`
- 기본 파일 모드: `/etc/namifax.env`는 0640

## 낡았을 가능성이 큰 부분

- **실제 HylaFAX 시험 미완료**: 이 저장소에서는 실제 HylaFAX와 연결하여 시험하지 못했으므로, 배포판별 서비스 이름(`faxq`, `hfaxd`, `faxgetty`)이나 버전별 동작 차이 가능성 있음
- **`JobFmt` 열 순서 일치 확인**: 실제 HylaFAX에서 `JobFmt` 설정과 NamiFAX 코드의 열 파싱 순서 일치 여부는 HylaFAX가 있는 서버에서만 확인 가능
- **cron 설정의 중요성 재강조**: 문서에서 "내장 스케줄러는 임시 파일 정리만"이라고 명시하지만, 이는 코드 업데이트에 따라 바뀔 수 있음
- **`tools/migration_rehearsal/` 삭제됨**: 이 디렉터리는 git 이력 정리 후 현재 저장소에 없으므로 검증 방법이 사라짐(커밋 72a7324)

## 관련 주제 페이지

[[hylafax-integration]] [[operations-and-deployment]] [[scheduler-and-storage]]
