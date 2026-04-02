# ADK RAG API 배포 가이드

## 사전 요구사항

- Google Cloud SDK (`gcloud`) 설치 및 인증
- GCP 프로젝트 설정 완료
- Artifact Registry 저장소 생성

## 환경변수 설정

`.env` 파일에 다음 환경변수 설정:

```bash
# GCP
GOOGLE_CLOUD_PROJECT=didimtest006
GOOGLE_CLOUD_LOCATION=us-central1

# Reasoning Engine
REASONING_ENGINE_APP_NAME=projects/didimtest006/locations/us-central1/reasoningEngines/<ENGINE_ID>
REASONING_ENGINE_ID=<ENGINE_ID>
REASONING_ENGINE_LOCATION=us-central1

# Vertex RAG
VERTEX_RAG_LOCATION=asia-northeast3
VERTEX_RAG_CORPUS=projects/didimtest006/locations/asia-northeast3/ragCorpora/<CORPUS_ID>

# Discovery Engine
DISCOVERY_ENGINE_ENGINE_ID=<ENGINE_ID>
DISCOVERY_ENGINE_LOCATION=global
```

## 배포 명령어

### 1. 환경변수 추출 및 배포

```bash
# 권장: .env 값을 그대로 사용해 배포
./deploy_from_env.sh

# 또는 수동 실행
# .env에서 환경변수 추출
VERTEX_RAG_CORPUS=$(grep VERTEX_RAG_CORPUS .env | sed 's/.*=//')
REASONING_ENGINE_APP_NAME=$(grep REASONING_ENGINE_APP_NAME .env | sed 's/.*=//')
REASONING_ENGINE_ID=$(grep "^REASONING_ENGINE_ID" .env | sed 's/.*=//')
REASONING_ENGINE_LOCATION=$(grep REASONING_ENGINE_LOCATION .env | sed 's/.*=//')
DISCOVERY_ENGINE_ENGINE_ID=$(grep DISCOVERY_ENGINE_ENGINE_ID .env | sed 's/.*=//')

# Cloud Build 실행
gcloud builds submit --config=cloudbuild.yaml \
  --substitutions="_VERTEX_RAG_CORPUS=$VERTEX_RAG_CORPUS,_DISCOVERY_ENGINE_ENGINE_ID=$DISCOVERY_ENGINE_ENGINE_ID,_REASONING_ENGINE_APP_NAME=$REASONING_ENGINE_APP_NAME,_REASONING_ENGINE_ID=$REASONING_ENGINE_ID,_REASONING_ENGINE_LOCATION=$REASONING_ENGINE_LOCATION"
```

> `cloudbuild.yaml`은 `_VERTEX_RAG_CORPUS`, `_DISCOVERY_ENGINE_ENGINE_ID`가 비어 있으면 배포를 실패시킵니다.
> (빈 값으로 Cloud Run 환경변수를 덮어쓰는 사고를 방지하기 위함)

### 2. 원라인 배포 스크립트

```bash
gcloud builds submit --config=cloudbuild.yaml \
  --substitutions="_VERTEX_RAG_CORPUS=$(grep VERTEX_RAG_CORPUS .env | sed 's/.*=//'),_DISCOVERY_ENGINE_ENGINE_ID=$(grep DISCOVERY_ENGINE_ENGINE_ID .env | sed 's/.*=//'),_REASONING_ENGINE_APP_NAME=$(grep REASONING_ENGINE_APP_NAME .env | sed 's/.*=//'),_REASONING_ENGINE_ID=$(grep '^REASONING_ENGINE_ID' .env | sed 's/.*=//'),_REASONING_ENGINE_LOCATION=$(grep REASONING_ENGINE_LOCATION .env | sed 's/.*=//')"
```

## 배포 확인

### 서비스 URL 확인

```bash
gcloud run services describe adk-rag-api-dev --region=asia-northeast3 --format='value(status.url)'
```

### API 테스트

```bash
SERVICE_URL=$(gcloud run services describe adk-rag-api-dev --region=asia-northeast3 --format='value(status.url)')
TOKEN=$(gcloud auth print-identity-token)

# Health Check
curl -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/healthz"

# Query 테스트
curl -X POST "$SERVICE_URL/v1/query" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "안녕하세요"}'
```

## 환경별 배포

### Dev 환경 (기본)

```bash
gcloud builds submit --config=cloudbuild.yaml \
  --substitutions="_ENV=dev,_LOG_LEVEL=DEBUG,..."
```

### Prod 환경

```bash
gcloud builds submit --config=cloudbuild.yaml \
  --substitutions="_ENV=prod,_MIN_INSTANCES=1,_LOG_LEVEL=INFO,..."
```

## Cloud Build 설정 (`cloudbuild.yaml`)

주요 substitutions:

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `_REGION` | asia-northeast3 | Cloud Run 배포 리전 |
| `_ENV` | dev | 환경 (dev/prod) |
| `_MIN_INSTANCES` | 0 | 최소 인스턴스 수 |
| `_MAX_INSTANCES` | 10 | 최대 인스턴스 수 |
| `_MEMORY` | 2Gi | 메모리 |
| `_CPU` | 2 | CPU |

## 로그 확인

```bash
gcloud run services logs read adk-rag-api-dev --region=asia-northeast3 --limit=50
```

## 트러블슈팅

### 컨테이너 시작 실패

```bash
# 상세 로그 확인
gcloud run services logs read adk-rag-api-dev --region=asia-northeast3 --limit=100
```

### 환경변수 확인

```bash
gcloud run services describe adk-rag-api-dev --region=asia-northeast3 \
  --format='json(spec.template.spec.containers[0].env)'
```
