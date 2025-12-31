#!/bin/bash
#
# Recipe Graph Engine - VPS 배포 스크립트
#

VPS_IP="141.164.35.214"
VPS_USER="root"
REMOTE_DIR="/opt/recipe"

echo "======================================================================"
echo "🍳 Recipe Graph Engine - VPS 배포"
echo "======================================================================"
echo ""

# 1. VPS에 디렉토리 생성
echo "📁 [1/5] VPS 디렉토리 생성..."
ssh ${VPS_USER}@${VPS_IP} "mkdir -p ${REMOTE_DIR}"

# 2. 파일 전송
echo "📦 [2/5] 파일 전송..."
cd "$(dirname "$0")/.."

# 필요한 파일들만 전송
rsync -avz --progress \
    --exclude='.git' \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.DS_Store' \
    --exclude='data/' \
    --exclude='node_modules/' \
    --exclude='web/' \
    . ${VPS_USER}@${VPS_IP}:${REMOTE_DIR}/

# 3. .env 파일 확인
echo "🔐 [3/5] 환경변수 확인..."
ssh ${VPS_USER}@${VPS_IP} "
    if [ ! -f ${REMOTE_DIR}/deploy/.env ]; then
        echo '⚠️  .env 파일이 없습니다. .env.example을 복사합니다...'
        cp ${REMOTE_DIR}/deploy/.env.example ${REMOTE_DIR}/deploy/.env
        echo '📝 ${REMOTE_DIR}/deploy/.env 파일을 수정해주세요!'
        exit 1
    fi
"

# 4. Docker 빌드 및 실행
echo "🐳 [4/5] Docker 컨테이너 시작..."
ssh ${VPS_USER}@${VPS_IP} "
    cd ${REMOTE_DIR}/deploy
    docker compose -f docker-compose.vps.yml down 2>/dev/null
    docker compose -f docker-compose.vps.yml up -d --build
"

# 5. 상태 확인
echo "✅ [5/5] 상태 확인..."
sleep 10

echo ""
echo "======================================================================"
echo "🏥 헬스체크..."
curl -s http://${VPS_IP}:8002/health | python3 -m json.tool 2>/dev/null || echo "API 시작 중..."
echo ""

echo "======================================================================"
echo "✅ 배포 완료!"
echo "======================================================================"
echo ""
echo "서비스 URL:"
echo "  - Recipe API:    http://${VPS_IP}:8002"
echo "  - Neo4j Browser: http://${VPS_IP}:7477"
echo ""
echo "다음 단계:"
echo "  1. Neo4j에 데이터 로드: python scripts/neo4j_loader.py"
echo "  2. API 테스트: curl http://${VPS_IP}:8002/health"
echo ""
