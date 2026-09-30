# Spec 40: Storage Lifecycle & Automated TIFF Purge Engine

## 1. 개요 및 목적
- **목적**: 팩스 서버의 로컬 디스크 공간 고갈을 방지하고, 클라우드 스토리지 비용을 최적화하기 위해 원본 TIFF 선별 삭제 및 원격(S3/GCS) 객체 라이프사이클 연동 엔진을 구축합니다.
- **주요 해결 과제**:
  - 대용량 원본 TIFF(`fax.tif`) 파일이 계속 누적되어 로컬 서버 스토리지가 고갈되는 문제 해결.
  - PDF가 정상 생성되었을 경우 원본 TIFF를 N일 후 선별 삭제하는 정책 지원.
  - 아카이브 보존 주기(예: 365일) 만료 시 로컬 디렉터리 및 원격 클라우드 객체까지 완결적으로 폐기하는 통합 수명주기 관리 지원.

---

## 2. 정책 및 동작 모드 (Policy Modes)

### 2.1 로컬 원본 TIFF 선별 삭제 (`purge_local_tiff_after_pdf`)
- PDF 파일(`fax.pdf`)이 존재하고 크기가 0보다 큰 경우에 한해, 수신된 지 N일이 경과한 원본 TIFF(`fax.tif`)를 로컬에서 삭제.
- 수신함 및 아카이브 조회는 PDF와 PNG 썸네일을 통해 정상 지속되므로 사용자 경험에 영향 없음.

### 2.2 보존 만료 팩스 일괄 삭제 (`purge_expired_faxes`)
- 지정된 보존 일수(`retention_days`)를 초과한 팩스에 대해:
  1. `FaxArchive` / `ArchiveIn` / `ArchiveOut` DB 레코드 정리.
  2. 로컬 파일 디렉터리(`/var/spool/hylafax/archive/YYYY/MM/DD/fid/`) 완전 삭제.
  3. 원격 스토리지 프로바이더(S3/GCS)가 구성된 경우, 원격 버킷의 해당 팩스 객체 일괄 `DeleteObject` 동기화 폐기.

### 2.3 스케줄러 자동 연동 (`run_storage_lifecycle_job`)
- `APScheduler` 및 `avantfaxcron` CLI 정기 배치와 연동하여 매일 지정된 시각에 무인 자동 실행.

---

## 3. 서비스 인터페이스 명세 (`StorageLifecycleService`)

```python
class StorageLifecyclePolicy:
    purge_tiff_after_days: int = 7       # PDF 생성 후 TIFF 보존 일수 (0 = 즉시)
    full_retention_days: int = 365       # 팩스 전체(DB+파일) 보존 일수 (0 = 영구 보존)
    remote_sync_delete: bool = True       # 팩스 삭제 시 원격 S3/GCS 객체도 함께 영구 삭제할지 여부
    delete_remote_tiff_only: bool = False # 원격에서도 TIFF만 선별 삭제할지 여부

class StorageLifecycleService:
    def __init__(self, db=None, storage_provider=None, spool_dir=None):
        ...

    def purge_local_tiffs(self, days_old: int = 7) -> dict:
        """Purge raw TIFF files where valid PDF exists and file is older than days_old."""

    def purge_expired_faxes(self, retention_days: int) -> dict:
        """Purge entire fax records, local files, and remote cloud objects older than retention_days."""

    def run_lifecycle(self, policy: StorageLifecyclePolicy) -> dict:
        """Execute full storage lifecycle sequence according to policy."""
```

---

## 4. 검증 기준
1. 단위 테스트:
   - `tests/unit/test_storage_lifecycle.py`:
     - 유효한 PDF가 있을 때 TIFF만 선별 삭제되는지 검증.
     - PDF가 없거나 크기가 0인 경우 TIFF가 안전하게 보존되는지 검증.
     - 만료된 팩스 일괄 삭제 시 DB, 로컬 폴더 및 원격 Mock Storage의 delete_fax가 모두 정상 호출되는지 검증.
2. 기존 306개 테스트 및 88개 골든 마스터 무회귀 통과.
