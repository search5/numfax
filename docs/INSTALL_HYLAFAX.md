# HylaFAX 연동 설치 가이드

NamiFAX와 HylaFAX를 연결하는 순서입니다. 파일은 `deploy/` 폴더에 있습니다. **이 저장소에서는 실제 HylaFAX에 붙여 시험하지
못했습니다.** 아래 순서는 원본 AvantFAX의 설치 스크립트(`legacy/debian-install.sh`, `setup-postfix.sh`)가 하던 일을 그대로
옮긴 것이고, 각 단계의 확인 방법을 함께 적었습니다. 운영 서버에 적용하기 전에 시험 서버에서 한 번 거치십시오.

경로 가정: NamiFAX는 `/opt/namifax`(가상환경 `.venv`), HylaFAX 스풀은 `/var/spool/hylafax`, 서비스 사용자는 `uucp`입니다.
다르면 `deploy/` 파일 안의 해당 부분을 바꾸십시오.

## 0. 환경 파일

`/etc/namifax.env`(모드 0640)에 DB 접속과 설정을 둡니다. 훅 스크립트와 서비스가 같은 파일을 읽습니다.

```
DATABASE_URL=mysql+pymysql://avantfax:비밀번호@localhost/avantfax
NAMIFAX_SESSION_SECRET=<긴 무작위 문자열>
NAMIFAX_SECRET_KEY=<비밀 저장소에 따로 보관>
ENABLE_DID_ROUTING=0            # 훅과 웹이 같은 값을 써야 합니다
FAXMAILUSER=faxmail
WWWUSER=uucp                    # 서비스를 실행하는 사용자
```

HylaFAX가 기본 위치에 없으면 `HYLASPOOL`, `HYLAFAX_PREFIX`, `BINARYDIR`로 알려 줍니다(`sendfax`, `faxstat`, `faxinfo`,
`faxadduser`를 찾는 데 쓰입니다).

## 1. 훅 연결

1. `deploy/hylafax/bin/*`를 `/var/spool/hylafax/bin/`에 복사하고 실행 권한을 줍니다
   (`faxrcvd`, `dynconf`, `notify`, `faxcover`). 소유자는 HylaFAX가 훅을 실행하는 사용자(보통 `uucp`)입니다.
2. 각 모뎀 설정(`/etc/hylafax/config.ttyS0` 등)에 `deploy/hylafax/config.namifax`의 세 줄을 붙입니다.
   여러 모뎀이면 파일마다 붙입니다.
3. 서버 설정(`/var/spool/hylafax/etc/config`)에 `deploy/hylafax/hfaxd.conf.snippet`의 `JobFmt` 줄과
   `deploy/hylafax/etc-faxq.snippet`의 `NotifyCmd`, `CoverCmd` 줄을 붙입니다.
   **`JobFmt`는 NamiFAX가 읽는 열 순서와 같아야 합니다.** 다르면 출력함 목록이 어긋나거나 비어 보입니다.
4. HylaFAX 재시작: `systemctl restart hylafax`(배포판에 따라 `faxq`, `hfaxd`, `faxgetty`).

확인: `sudo -u uucp /var/spool/hylafax/bin/dynconf ttyS0 5551234` 가 아무것도 출력하지 않고 끝나야 합니다(차단 번호면
`RejectCall: true`). 시스템 로그 화면에 `dynconf> checking CallID1 …` 줄이 남습니다.

## 2. 웹 서비스

- `deploy/systemd/namifax.service`를 `/etc/systemd/system/`에 두고 `systemctl enable --now namifax`.
- 앞단 웹 서버: `deploy/nginx/namifax.conf` 또는 `deploy/apache/namifax.conf`. HTTPS를 쓰면 `session.secure = true`.
  프록시 뒤에서는 `X-Forwarded-Host`를 넘겨야 변경 요청의 출처 검사가 통과합니다.
- 첫 관리자: `namifax createuser -u admin -e you@example.com`.

## 3. 사용자 동기화 (선택)

HylaFAX 서버(`hfaxd`)에 사용자 이름이 등록돼 있어야 `faxrm`, `faxalter`가 그 사용자의 작업을 다룰 수 있습니다. 원본은 계정을
만들거나 비밀번호를 바꿀 때마다 `faxadduser`/`faxdeluser`를 `sudo`로 실행했습니다. 같은 동작을 켜려면:

1. `deploy/sudoers.d/namifax`를 `/etc/sudoers.d/namifax`로 복사(모드 0440, `visudo -cf`로 확인). 서비스 사용자 이름을 맞추십시오.
2. `/etc/namifax.env`에 `HYLAFAX_USER_SYNC=1`.
3. `deploy/systemd/namifax.service`의 `NoNewPrivileges=true`를 `false`로 바꾸십시오. 켜져 있으면 `sudo`가 동작하지 않습니다.

`faxadduser`는 비밀번호를 명령줄 인자(`-p`)로만 받으므로, 실행되는 짧은 순간 같은 서버의 다른 사용자가 `ps`로 볼 수 있습니다
(원본과 같은 한계입니다). 서버에 다른 사용자가 없는 전용 장비에서 쓰십시오. 끄면(기본) 아무것도 실행하지 않습니다.

## 4. 주기 작업

**관리자 > 예약 작업**(`/admin/scheduler`)에서 설정합니다: 임시 폴더 정리(일수·시각), 받은 팩스함의 오래된 팩스를 보관함으로 이동(일수·시각, 기본 꺼짐), 보존 기간 정책 적용(정책 값은 Storage & Cloud 화면), 전화번호부 내보내기(주기). 각 작업은 "지금 실행"과 마지막 실행 결과를 보여 줍니다. 저장한 변경은 실행 중인 스케줄러가 1분 안에 반영하며(재시작 불필요), 화면 위쪽에 스케줄러가 살아 있는지(1분마다 남기는 신호)가 표시됩니다. 스케줄러는 웹 서비스에 내장되어 있거나(`NAMIFAX_ENABLE_SCHEDULER=1`, 기본값) `namifax scheduler`를 별도 서비스로 돌립니다. 아래 cron 방식은 스케줄러를 쓰지 않을 때의 대안입니다.


`deploy/cron.d/namifax`를 `/etc/cron.d/namifax`로 복사하고 보존 기간을 정하십시오.
**내장 스케줄러(`NAMIFAX_ENABLE_SCHEDULER=1`)는 임시 파일 정리만 합니다.** 받은 팩스함 보관(`-i`)과 오래된 팩스 삭제(`-d`)는
cron에 적어야 돌아갑니다. 적지 않으면 팩스가 영원히 쌓입니다.

## 5. 이메일로 팩스 보내기 (선택)

`deploy/postfix/setup-email2fax.md`. 원본의 `setup-postfix.sh`가 하던 설정이며, 이 저장소의 스크립트는 시스템 파일을 직접
고치지 않으므로 적용 전에 내용을 읽고 직접 넣으십시오.

## 6. 파일 권한

- 보관 폴더(`/var/spool/hylafax/archive`, `…/sent`)는 훅을 실행하는 사용자와 웹 서비스 사용자가 모두 쓸 수 있어야 합니다
  (같은 `uucp`로 돌리면 가장 단순합니다).
- 임시 폴더(`AVANTFAX_TMPDIR`)도 같습니다.
- `/etc/namifax.env`는 서비스 사용자만 읽게(0640) 하십시오. DB 비밀번호와 세션 키가 들어 있습니다.

## 7. 설치 뒤 점검 순서

1. 로그인 → 설정 → 시스템 로그에 오류가 없는지.
2. 관리자 > 모뎀에서 모뎀을 만들고 상태가 `Running and idle`로 나오는지(`faxstat`을 읽습니다).
3. 시험 팩스를 보내고 출력함에 작업이 나오는지, 완료 뒤 `notify`가 보관함에 보낸 팩스를 만드는지.
4. 시험 팩스를 받고 `faxrcvd`가 받은 팩스함에 올리는지(썸네일, PDF, 메일 알림).
5. 관리자 화면 대시보드의 HylaFAX 버전이 표시되는지(`faxstat -i`).
