---
title: Google Cloud Storage 구현 보류 메모
type: source
updated: 2026-10-02
sources: [docs/FUTURE_GCS_STORAGE.md]
verified: false
---

## 요약

2026-10-02에 Admin > Storage 화면과 코드에서 GCS(Google Cloud Storage) 항목을 제거했으며, 나중에 다시 추가할 때 참고하려고 제거 전 상태를 기록한 메모. GCS는 S3 호환 인터페이스와 GCS 전용 방식 두 가지 구현 선택지가 있고, 코드에서 실제 GCS 계정으로 시험 미완료.

## 핵심 내용

### 제거 전 상태 (커밋 53ed28b 시점)

**화면**:
- Storage Provider 드롭다운에 `GCS` 옵션 있음
- S3와 같은 입력란: 엔드포인트, 리전, 버킷, 액세스 키, 시크릿, 접두사
- 라벨: "HMAC Access Key / HMAC Secret"
- 안내문(영어): "Google Cloud Storage is reached through its S3-compatible interface: use the endpoint https://storage.googleapis.com and an HMAC key (Cloud Storage > Settings > Interoperability)."
- 안내문(한국어): "Google Cloud Storage는 S3 호환 인터페이스로 연결합니다. 엔드포인트는 https://storage.googleapis.com, 인증은 HMAC 키(Cloud Storage > 설정 > 상호 운용성)를 사용하십시오."
- 템플릿 구조: `#cloud-fields` 묶음 + `data-for="S3"` / `data-for="GCS"` 라벨 + `static/js/storage.js`(제공자 선택에 따라 보임/숨김)

**코드**:
- GCS 전용 코드 없음
- `CloudStorageManager.get_provider`가 `("S3", "GCS")`를 모두 `S3CompatibleStorageProvider`(boto3)로 전달
- **결함**: 엔드포인트가 비어 있으면 AWS로 접속하는 문제 있음(결함 보고서 R3D-05, 커밋 01f2f64에서 복원 가능)
- 실제 GCS 계정으로는 **한 번도 시험하지 않음**

### 다시 추가할 때의 선택지

**선택지 1: S3 호환(XML API) 방식**
- 엔드포인트: `https://storage.googleapis.com` + HMAC 키
- 기존 boto3 코드 재사용
- 필요 작업:
  - 엔드포인트 기본값 채우기
  - 실제 GCS에서의 연결 시험
  - 일부 S3 기능(버전, 일부 헤더) GCS 차이 처리
  
**선택지 2: GCS 전용 방식(권장)**
- 라이브러리: `google-cloud-storage`
- 인증: 서비스 계정 JSON 키 + Project ID
- 구현: 별도 `GcsStorageProvider` 클래스 필요
- 서명된 URL: `generate_signed_url` 구현 필요
- 참고: 명세 계획서 3.8, 명세 41 §2.2

### 다시 추가할 때 수정해야 할 부분

1. **저장소 프로바이더 코드**: 어느 방식이든 `StorageLifecycleService`의 원격 삭제 동기화 두 곳에 새 유형 추가
   - 현재: `cloud_storage_type in (...)` 두 곳
   
2. **설정 저장**: 저장된 설정 키(`cloud_*`)와 시크릿(`cloud_secret_key`) 처리 로직 추가

3. **테스트**: `tests/unit/test_storage_page_fields.py`의 GCS 시험 복구

## 문서가 주장하는 수치·상태

- **제거 시점**: 2026-10-02, 커밋 53ed28b
- **제거된 항목**: Admin > Storage 화면 GCS 드롭다운 옵션, 관련 코드 전체
- **코드 재사용 가능성**: 기존 `S3CompatibleStorageProvider(boto3)` 사용 가능
- **시험 현황**: 실제 GCS 계정으로는 **0회 시험**
- **구현 선택지**: 2가지 (S3 호환 또는 GCS 전용)
- **구현 난이도**: GCS 전용 방식 권장

## 낡았을 가능성이 큰 부분

- **커밋 53ed28b 참조**: 제거 전 상태는 그 시점의 코드. 이후 다른 Storage 기능이 수정되었다면 GCS 복구 시 충돌 가능
- **결함 보고서 R3D-05**: "엔드포인트가 비어 있으면 AWS로 접속" 문제는 현재 코드에서 해결되었을 가능성. 복구 전 확인 필요
- **boto3 S3 호환**: S3 표준이 업데이트되었거나 GCS S3 호환 인터페이스가 기능을 추가/제거했을 수 있음
- **`google-cloud-storage` 라이브러리 버전**: 명세는 특정 버전 명시 없음. 최신 버전과 API 호환성 확인 필요
- **서명된 URL 구현**: `generate_signed_url` 파라미터나 동작이 라이브러리 버전에 따라 달라질 수 있음
- **명세 참고 경로**: "명세 계획서 3.8, 명세 41 §2.2"가 삭제된 문서. git 이력에서 복원 필요

## 관련 주제 페이지

[[scheduler-and-storage]] [[known-gaps-and-decisions]]
