---
title: 운영 전·운영 중 점검 목록
type: source
updated: 2026-10-02
sources: [docs/OPERATIONS_CHECKLIST.md]
verified: false
---

## 요약

NamiFAX를 운영 환경에 올리기 전 한 번, 운영 중 주기적으로 확인할 사항. 코드로 보장되는 동작은 삭제된 `ARCHITECTURE.md` 17장에 있으며, 이 문서는 사람이 설정하거나 판단해야 하는 항목만 모았다. 첫 기동 전 점검(세션 키, 암호화 키, 관리자, SMTP, 데모 데이터, 해시 방식), SAML 로그인, HylaFAX 연동, AvantFAX 마이그레이션, 보안 판단(비밀번호 찾기), 알려진 한계, 운영 중 주기 점검, 미완료 작업을 다룬다.

## 핵심 내용

### 1단계: 첫 기동 전 (한 번)

| 항목 | 해야 할 일 | 주의 |
|---|---|---|
| 세션 서명 키 | `session.secret`(ini) 또는 환경변수 `NAMIFAX_SESSION_SECRET` 고정 | 없으면 프로세스마다 임의 키 사용. 워커 여러 개 또는 재시작 시 2FA 중간 단계와 로그인 흐름 끊김 |
| HTTPS 보안 쿠키 | `session.secure = true` | 기본값은 false |
| 자격증명 암호화 키 | `NAMIFAX_SECRET_KEY` 환경변수 설정 후 `namifax encrypt-secrets` 한 번 실행 | **키를 잃으면 암호화된 값 복구 불가**. 비밀 저장소에 따로 보관 |
| 첫 관리자 | `namifax createuser -u <이름> -e <메일>` (비밀번호는 `-p`, `NAMIFAX_NEW_USER_PASSWORD` 또는 프롬프트) | 서버 DB에는 데모 계정 없음. 내장 기본 비밀번호도 없음 |
| SMTP 게이트웨이 | 관리자 화면에서 설정 | **비밀번호 찾기**, 수신 팩스 메일 전달, 알림 메일이 이 설정 사용. 메일 미발송 시 비밀번호 찾기는 "Email failed to send" 표시 |
| 데모 데이터 | `NAMIFAX_DEMO_DATA` 끄기 | SQLite에서만 동작하는 옵트인. SQLite는 운영 DB 아님 |
| 비밀번호 해시 | 원본 PHP와 함께 사용할 때만 `NAMIFAX_PASSWORD_HASH=md5` | 기본값은 Argon2id. 원본은 Argon2id를 읽지 못함 |

### SAML 로그인과 권한
- 관리자 > SAML에서 IdP 주소·인증서 저장하고 사용 활성화
- 설정 전에는 로그인 화면에 버튼 미표시
- 응답은 IdP가 **서명**한 것만 받음(SHA-256 이상)
- "권한을 IdP에서 가져오기" 활성화 시 로그인할 때마다 역할 속성(기본 `Role`)에 따라 권한 결정
- Keycloak에서는 클라이언트의 매퍼로 `Role`(다중값)과 `modems` 같은 사용자 속성 응답에 포함
- Keycloak 26 컨테이너로 로그인, 위조·재사용 거부, 역할 부여·회수, 회선 속성 반영 확인함. Okta·Entra ID 등은 시험 미완료

### 2단계: HylaFAX 연동 (실제 서버에서만 확인 가능)
- `sendfax`가 `PATH`에 있어야 함. 없으면 `NAMIFAX_QUEUE_SIMULATION`이 꺼진 환경에서 전송 실패로 표시 (켜져 있거나 `/var/spool/hylafax` 없으면 시뮬레이션)
- 커버페이지: `AVANTFAX_INSTALLDIR/images/<커버 파일>` 경로에 파일 있어야 함. 실행 파일은 `NAMIFAX_FAXCOVER`(기본 `python -m namifax.cli.faxcover`)
- `DEFAULT_TSI_ID`, `ENABLE_DID_ROUTING`(수신 훅과 웹이 같은 값 사용 필수), `AVANTFAX_ARCHIVE`, `AVANTFAX_TMPDIR` 설정 확인
- 첫 전송 후: 출력함에 작업 나타남, `sendfax` 출력의 `request id is N`을 작업 번호로 읽음 확인
- 커버페이지만 보낼 때: 임시 `.ps` 파일이 전송 뒤 지워짐 확인

### 3단계: 기존 AvantFAX에서 옮길 때
- `docs/MIGRATING_FROM_AVANTFAX3.md` 참고 (절차 전체, 설정 대응표, 웹 서버 리다이렉트, 예행연습 결과)
- 원본 MySQL/MariaDB DB에 그대로 붙음. 큰 `FaxArchive` 테이블은 **첫 기동에서 인덱스 생성에 오래 걸릴 수 있음** (시간 측정 미완료. 점검 시간대에 첫 기동 권장)
- **PHP 세션과 로그인 쿠키는 이어지지 않음**. 이전 직후 모든 사용자 재로그인 필요
- 원본 DB는 첫 기동 전에 백업(스키마 보정 발생)
- 이전 버전의 포트가 만든 SQLite 파일은 시작 시 보정됨. 초기 버전은 일부만 보정되므로 운영 데이터 아니면 지우고 새로 만들기
- 기존 보관 팩스 파일: `namifax import-archive`로 들여옴
- 사용자: `namifax import-users`

### 4단계: 보안 판단이 필요한 것

**비밀번호 찾기(원본 `forgot.php` 방식)**
- 이메일 주소로 새 임시 비밀번호 만들어 메일로 보냄. 그 비밀번호는 다음 로그인에서 바꿔야 함
- 누구든 다른 사람의 이메일만 알면 그 계정의 **기존 비밀번호 무효화 가능** (임시 비밀번호가 본인 메일로 가므로 탈취는 아님). 앞단에서 `/forgot`에 요청 횟수 제한 권장
- 없는 주소 입력 시 "해당 사용자 없음" 알려줌(원본 동작). 계정 존재 여부 노출
- 원본과 다른 점: 새 비밀번호를 **시스템 로그에 남기지 않음**(원본은 평문). 메일 발송 실패 시 **기존 비밀번호 되돌림**(원본은 잠긴 채). 삭제된 계정 찾지 않음
- 2단계 인증 켠 계정은 임시 비밀번호로 로그인해도 인증 코드 요구

**알려진 한계 (수정 안 함)**
- SAML 로그인은 앱의 2FA를 거치지 않음. **확정된 정책**: IdP가 책임짐
- 원본 보관함 검색과 받은 팩스함의 권한 규칙은 원본 실행으로 일치 확인. 다만 대기열 작업 수정(`/ajax/faxalter`)은 원본처럼 로그인만 확인

### 5단계: 운영 중 주기 점검
- 시스템 로그에서 `Access denied to … fax`(권한 없는 접근), `Attempt to reset password for email`(비밀번호 찾기 실패) 확인
- TOTP 5회 실패 시 일정 시간 잠김. 기기와 복구 코드 모두 잃으면 `namifax reset-2fa <사용자>`로 풀기
- 설정에서 지운 모뎀의 팩스는 **받은 팩스함에 보이지 않음**(슈퍼유저 포함). 모뎀 지우기 전에 받은 팩스함 비우거나 보관
- 키 회전: 새 `NAMIFAX_SECRET_KEY`로 바꾸기 전에 기존 키로 값을 읽을 수 있는 상태에서 작업 (키를 잃으면 복구 불가)

### 6단계: 아직 하지 않은 일
- **번역**: 한국어만 새 문구까지 채움(빠진 번역 0개, 테스트 보장). 나머지 23개 언어에서는 약 190개의 새 화면 문구(SAML, 프린터, 스토리지, 패스키, 2FA, 보내기 폼 등)가 영어로 보임
- **출력함**: 원본과 같은 열·버튼이지만 **가짜 `faxstat` 출력으로만** 확인. 실제 HylaFAX의 작업 목록 형식(`JobFmt`의 `Mailaddr` 열 필수)과 `faxrm`·`faxalter` 소유자 권한은 HylaFAX 서버에서 확인 필요

## 문서가 주장하는 수치·상태

- 한국어 번역: 빠진 문구 0개(테스트로 보장)
- 번역 커버리지(기타 언어): 695개 문구 중 292~333개(약 42~47%) 번역됨. 나머지는 영어
- SAML 인증: Keycloak 26 컨테이너로 로그인, 위조·재사용 거부, 역할 부여·회수, 회선 속성 반영 **확인됨**
- Okta·Entra ID: **시험 미완료**
- 실제 HylaFAX 연동: **이 저장소에서 검증 안 함**

## 낡았을 가능성이 큰 부분

- **ARCHITECTURE.md 참조**: 삭제된 `ARCHITECTURE.md` 17장을 가리키므로, 코드와 동기화 상태 확인 불가(커밋 01f2f64에서 복원 가능)
- **내장 스케줄러 동작**: 문서는 "임시 파일 정리만"이라고 명시하지만, 코드 업데이트로 기능이 확장될 수 있음
- **번역 상태**: 2026-10-02 기준이므로 이후 새 화면 문구 추가 시 번역 비율 변화 가능
- **실제 HylaFAX와의 미검증**: `JobFmt` 열 순서, `faxrm`·`faxalter` 소유자 권한, 버전별 동작 등은 HylaFAX 있는 서버에서만 확인 가능
- **cron 설정 필수성**: "내장 스케줄러는 임시 파일 정리만"이라는 문구에 의존하는데, 코드 변경으로 인해 거짓이 될 수 있음

## 관련 주제 페이지

[[authentication-and-security]] [[hylafax-integration]] [[migration-from-avantfax]] [[operations-and-deployment]] [[scheduler-and-storage]] [[i18n-and-ui]]
