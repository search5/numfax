# Spec 41: Multi-Cloud Object Storage Integration (AWS S3 & Google Cloud Storage)

## 1. 개요 및 목적
- **목적**: 온프레미스 단일 서버의 로컬 디스크 용량 한계를 극복하고, 엔터프라이즈 멀티 클라우드(AWS S3, MinIO, Google Cloud Storage, Cloudflare R2 등) 오브젝트 스토리지에 수신/발신 팩스 아카이브를 자동 동기화 및 백업하고, 스마트 스트리밍 다운로드를 제공합니다.
- **연동 대상**:
  - `StorageLifecycleService` (`src/namifax/services/storage_lifecycle.py`)
  - `CloudStorageService` (`src/namifax/services/cloud_storage.py`)
  - 관리자 설정 뷰 (`/admin/storage`)

---

## 2. 인터페이스 및 프로바이더 명세

### 2.1 추상 베이스 클래스 `StorageProvider`
```python
class StorageProvider(ABC):
    @abstractmethod
    def upload_file(self, local_path: str, remote_key: str) -> bool: ...

    @abstractmethod
    def download_file(self, remote_key: str, target_path: str) -> bool: ...

    @abstractmethod
    def delete_file(self, remote_key: str) -> bool: ...

    @abstractmethod
    def delete_fax(self, fid: int | str) -> bool: ...

    @abstractmethod
    def test_connection(self) -> dict: ...
```

### 2.2 지원 프로바이더 구현
1. `LocalStorageProvider`:
   - 로컬 파일시스템에만 저장하는 기본 모드.
2. `S3CompatibleStorageProvider`:
   - AWS S3, MinIO, Ceph, Cloudflare R2, Google Cloud Storage(HMAC) 등 S3 호환 API를 지원.
   - 버킷 존재 여부 확인(`HeadBucket`), 업로드/다운로드/삭제 및 Presigned URL 발급 지원.

---

## 3. 관리자 설정 및 DB 영속화 (`SystemSettings`)
- `SystemSettings` 테이블에 클라우드 스토리지 설정 컬럼 확장:
  - `storage_type`: `LOCAL`, `S3`, `GCS`
  - `storage_endpoint`: S3/MinIO 커스텀 엔드포인트 URL
  - `storage_region`: AWS 리전 (예: `ap-northeast-2`)
  - `storage_bucket`: 버킷명
  - `storage_access_key`: Access Key ID
  - `storage_secret_key`: Secret Access Key
  - `storage_prefix`: 객체 경로 프리픽스 (예: `faxes/`)

---

## 4. 검증 기준
1. 단위 테스트:
   - `tests/unit/test_cloud_storage.py`:
     - LocalStorageProvider 및 S3CompatibleStorageProvider 인터페이스 구현 검증.
     - Mock S3/Boto3를 통한 업로드, 다운로드, 삭제, 팩스 디렉터리 일괄 삭제(`delete_fax`) 검증.
     - `test_connection` 연결 진단 성공/실패 시나리오 검증.
2. 무회귀 검증:
   - 기존 312개 단위 테스트 및 88개 골든 마스터 E2E 100% 통과.
