#!/bin/bash
#
# Recipe Graph Engine - VPS에 데이터 로드
#

VPS_IP="141.164.35.214"
VPS_USER="root"
REMOTE_DIR="/opt/recipe"

echo "======================================================================"
echo "🍳 Recipe Graph Engine - 데이터 로드"
echo "======================================================================"
echo ""

# 1. 로컬에서 데이터 export (JSON)
echo "📦 [1/3] 로컬 데이터 확인..."
LOCAL_DATA="$(dirname "$0")/../data/processed/recipes.json"

if [ ! -f "$LOCAL_DATA" ]; then
    echo "❌ $LOCAL_DATA 파일이 없습니다."
    echo "먼저 로컬에서 데이터를 처리해주세요:"
    echo "  python scripts/recipe_loader.py"
    exit 1
fi

# 2. 데이터 전송
echo "📤 [2/3] 데이터 전송..."
ssh ${VPS_USER}@${VPS_IP} "mkdir -p ${REMOTE_DIR}/data/processed"
scp "$LOCAL_DATA" ${VPS_USER}@${VPS_IP}:${REMOTE_DIR}/data/processed/

# 3. VPS에서 Neo4j 로드
echo "📊 [3/3] Neo4j에 데이터 로드..."
ssh ${VPS_USER}@${VPS_IP} "
    cd ${REMOTE_DIR}

    # Python 환경에서 로드 스크립트 실행
    docker exec recipe-api python -c \"
import json
from neo4j import GraphDatabase

driver = GraphDatabase.driver('bolt://neo4j-recipe:7687', auth=('neo4j', 'recipe_vultr_2025'))

with open('/app/data/processed/recipes.json', 'r') as f:
    recipes = json.load(f)

print(f'Loading {len(recipes)} recipes...')

with driver.session() as session:
    # Clear existing data
    session.run('MATCH (n) DETACH DELETE n')

    # Create constraints
    session.run('CREATE CONSTRAINT IF NOT EXISTS FOR (r:Recipe) REQUIRE r.id IS UNIQUE')
    session.run('CREATE CONSTRAINT IF NOT EXISTS FOR (i:Ingredient) REQUIRE i.name IS UNIQUE')

    # Load recipes
    for i, recipe in enumerate(recipes):
        session.run('''
            MERGE (r:Recipe {id: \$id})
            SET r.name = \$name,
                r.category = \$category,
                r.cooking_time = \$cooking_time,
                r.difficulty = \$difficulty,
                r.calories = \$calories
        ''', **recipe)

        for ing in recipe.get('ingredients', []):
            session.run('''
                MERGE (i:Ingredient {name: \$ing_name})
                WITH i
                MATCH (r:Recipe {id: \$recipe_id})
                MERGE (r)-[:USES]->(i)
            ''', ing_name=ing, recipe_id=recipe['id'])

        if (i + 1) % 500 == 0:
            print(f'Loaded {i + 1} recipes...')

print('Done!')
driver.close()
\"
"

echo ""
echo "======================================================================"
echo "✅ 데이터 로드 완료!"
echo "======================================================================"
echo ""
echo "확인:"
echo "  curl http://${VPS_IP}:8002/stats"
echo ""
