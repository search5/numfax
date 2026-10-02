# Module Specification: 22. dynconf (CLI)

## 1. 개요 (Overview)
- **모듈명**: `dynconf` (`src/avantfax/cli/dynconf.py`)
- **레거시 파일**: `legacy/avantfax/includes/dynconf.php`
- **의존성**:
  - `DynamicConfig` (`src/avantfax/services/dynconf.py`)
  - `strip_sipinfo` (SIP 접두사/도메인 정제 유틸리티)
- **책임**:
  - HylaFAX의 `DynamicConfig` 메커니즘을 위한 수신 팩스 콜 필터링 CLI 엔트리포인트.
  - 디바이스명(`device`)과 발신번호(`CallID1`)를 전달받아 블랙리스트(`DynamicConfig` 테이블) 등록 여부를 조회.
  - 등록된 번호일 경우 `RejectCall: true` 표준 출력 및 0 리턴, 아닐 경우 무출력 및 0 리턴.
  - 인자가 없을 경우 Usage(`dynconf.php device CallID1 CallIDn...`)를 출력하고 종료.

---

## 2. 인터페이스 명세 (API Contract)

### CLI 실행 형식
```bash
python3 -m avantfax.cli.dynconf [device] [CallID1] [CallIDn...]
```

### 처리 규칙
1. `len(sys.argv) == 1`:
   - `print("dynconf.php device CallID1 CallIDn...")`
   - `sys.exit(0)`
2. `device = sys.argv[1]`
3. `callid1`:
   - `len(sys.argv) < 3` 또는 `sys.argv[2] == ""` 이면 `"EMPTY CALLID"`
   - 값이 있으면 `strip_sipinfo(sys.argv[2])`
4. `DynamicConfig.lookup(device, callid1)`:
   - True이면 `print("RejectCall: true")`
   - False이면 무출력
5. 종료 코드: `0`

---

## 3. 검증 시나리오 (Golden Master 연동)
- **시나리오 01**: 인자 없음 -> `dynconf.php device CallID1 CallIDn...` (code 0)
- **시나리오 02**: `ttyS0 ""` -> 빈 CallID -> 무출력 (code 0)
- **시나리오 03**: `ttyS0 "sip:12345@domain.com"` -> SIP 제거 -> 무출력 (code 0)
- **추가 단위 테스트**: 블랙리스트 등록된 번호 입력 시 `RejectCall: true` 출력 검증.
