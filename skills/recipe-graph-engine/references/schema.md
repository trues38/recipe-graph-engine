# Neo4j 스키마 상세

## 노드 정의

### Ingredient (재료)

```cypher
CREATE (i:Ingredient {
  name: "돼지고기",           // 필수
  category: "육류",           // 육류/채소/해산물/유제품/곡물/양념/기타
  storage: "냉동",            // 냉장/냉동/실온
  calories_per_100g: 250,     // 100g당 칼로리
  protein_per_100g: 25.0,     // 100g당 단백질(g)
  carbs_per_100g: 0.0,        // 100g당 탄수화물(g)
  fat_per_100g: 15.0,         // 100g당 지방(g)
  fiber_per_100g: 0.0,        // 100g당 식이섬유(g)
  sodium_per_100g: 60,        // 100g당 나트륨(mg)
  allergens: ["없음"],        // 알레르기 유발물질
  gi_index: null,             // 혈당지수 (해당시)
  vegan: false,               // 비건 여부
  kosher: true,               // 코셔 여부
  halal: true                 // 할랄 여부
})
```

### Recipe (레시피)

```cypher
CREATE (r:Recipe {
  name: "김치찌개",           // 필수
  category: "찌개",           // 찌개/볶음/구이/찜/튀김/무침/국/밥/면/디저트
  cuisine: "한식",            // 한식/양식/중식/일식/동남아/퓨전
  time_minutes: 30,           // 조리시간
  difficulty: "쉬움",         // 쉬움/보통/어려움
  servings: 2,                // 인분
  total_calories: 450,        // 총 칼로리
  total_protein: 35.0,        // 총 단백질(g)
  total_carbs: 25.0,          // 총 탄수화물(g)
  total_fat: 20.0,            // 총 지방(g)
  tags: ["국물", "매운맛", "겨울"],  // 태그
  spicy_level: 2,             // 맵기 (0-3)
  description: "...",         // LLM 생성 설명
  steps: ["1. ...", "2. ..."], // LLM 생성 조리법
  tips: "..."                 // LLM 생성 팁
})
```

### Goal (목표)

```cypher
CREATE (g:Goal {
  name: "다이어트",
  daily_calories: 1500,       // 일일 권장 칼로리
  protein_ratio: 0.30,        // 단백질 비율
  carbs_ratio: 0.40,          // 탄수화물 비율
  fat_ratio: 0.30,            // 지방 비율
  avoid_tags: ["고탄수화물", "튀김", "고칼로리"],
  prefer_tags: ["저칼로리", "고단백", "식이섬유"]
})

// 기본 Goal 노드들
// - 다이어트: 저칼로리, 고단백
// - 벌크업: 고칼로리, 고단백
// - 유지: 균형잡힌 매크로
// - 저탄수: 케토/저탄고지
```

### Condition (건강상태)

```cypher
CREATE (c:Condition {
  name: "당뇨",
  avoid_ingredients: ["설탕", "흰쌀", "흰밀가루"],
  limit_nutrients: {carbs: 130},  // 일일 제한량(g)
  prefer_tags: ["저GI", "식이섬유", "통곡물"],
  description: "혈당 관리가 필요한 상태"
})

// 기본 Condition 노드들 (30+)
// - 당뇨: 탄수화물 제한, 저GI
// - 고혈압: 저나트륨
// - 통풍: 저퓨린
// - 신장질환: 저단백, 저칼륨
// - 고지혈증: 저지방, 저콜레스테롤
// - 위장질환: 저자극
// - 알레르기(땅콩/갑각류/유제품/밀/계란/견과류)
```

### Diet (식단)

```cypher
CREATE (d:Diet {
  name: "비건",
  exclude_categories: ["육류", "해산물", "유제품", "계란"],
  exclude_ingredients: ["꿀", "젤라틴"],
  description: "동물성 식품 완전 배제"
})

// 기본 Diet 노드들
// - 비건: 동물성 완전 배제
// - 락토: 유제품만 허용
// - 오보: 계란만 허용
// - 페스코: 해산물만 허용
// - 폴로: 가금류만 허용
// - 플렉시테리언: 가끔 육류 허용
```

### Technique (기법)

```cypher
CREATE (t:Technique {
  name: "수비드",
  difficulty: "상",
  equipment: ["수비드 머신", "진공포장기"],
  description: "저온에서 장시간 조리하는 기법",
  best_for: ["스테이크", "닭가슴살", "연어"]
})

// 기본 Technique 노드들
// - 수비드, 에어프라이어, 훈연
// - 저온조리, 압력조리, 발효
// - 분자요리, 플랑베
```

---

## 엣지 정의

### REQUIRED_FOR (재료 → 레시피)

```cypher
(i:Ingredient)-[:REQUIRED_FOR {
  amount: 300,        // 수량
  unit: "g",          // 단위 (g/ml/개/큰술/작은술/컵)
  optional: false,    // 필수/선택
  prep: "다진 것"     // 전처리 (다진/썬/갈은)
}]->(r:Recipe)

// 예시
MATCH (pork:Ingredient {name: "돼지고기"})
MATCH (kimchi:Ingredient {name: "김치"})
MATCH (recipe:Recipe {name: "김치찌개"})
CREATE (pork)-[:REQUIRED_FOR {amount: 300, unit: "g"}]->(recipe)
CREATE (kimchi)-[:REQUIRED_FOR {amount: 200, unit: "g"}]->(recipe)
```

### CAN_REPLACE (대체 재료)

```cypher
(i1:Ingredient)-[:CAN_REPLACE {
  ratio: 1.0,         // 대체 비율
  context: "비건",    // 어떤 맥락에서 대체
  notes: "식감 유사"
}]->(i2:Ingredient)

// 예시: 비건 대체재
CREATE (tofu)-[:CAN_REPLACE {ratio: 1.0, context: "비건"}]->(pork)
CREATE (mushroom)-[:CAN_REPLACE {ratio: 0.8, context: "비건"}]->(beef)
```

### PAIRS_WELL / CONFLICTS (궁합)

```cypher
(i1:Ingredient)-[:PAIRS_WELL {
  reason: "감칠맛 상승"
}]->(i2:Ingredient)

(i1:Ingredient)-[:CONFLICTS {
  reason: "풍미 충돌"
}]->(i2:Ingredient)
```

### SUITABLE_FOR (레시피 → 목표)

```cypher
(r:Recipe)-[:SUITABLE_FOR {
  score: 0.95,        // 적합도 (0-1)
  reason: "고단백 저칼로리"
}]->(g:Goal)

// 예시
MATCH (salad:Recipe {name: "닭가슴살 샐러드"})
MATCH (diet:Goal {name: "다이어트"})
CREATE (salad)-[:SUITABLE_FOR {score: 0.95}]->(diet)
```

### SAFE_FOR / AVOID_FOR (레시피 → 건강상태)

```cypher
// 안전한 레시피
(r:Recipe)-[:SAFE_FOR]->(c:Condition)

// 피해야 할 레시피
(r:Recipe)-[:AVOID_FOR {
  reason: "고퓨린 함유",
  severity: "high"    // high/medium/low
}]->(c:Condition)

// 예시
MATCH (gamjatang:Recipe {name: "감자탕"})
MATCH (gout:Condition {name: "통풍"})
CREATE (gamjatang)-[:AVOID_FOR {reason: "퓨린 함량 높음"}]->(gout)
```

### COMPATIBLE_WITH (레시피 → 식단)

```cypher
(r:Recipe)-[:COMPATIBLE_WITH]->(d:Diet)

// 예시
MATCH (tofu_steak:Recipe {name: "두부스테이크"})
MATCH (vegan:Diet {name: "비건"})
CREATE (tofu_steak)-[:COMPATIBLE_WITH]->(vegan)
```

### USES_TECHNIQUE (레시피 → 기법)

```cypher
(r:Recipe)-[:USES_TECHNIQUE {
  step: 3,            // 몇 번째 단계에서 사용
  duration: "2시간"   // 소요 시간
}]->(t:Technique)
```

### SIMILAR_TO (레시피 유사도)

```cypher
(r1:Recipe)-[:SIMILAR_TO {
  score: 0.85,
  shared_ingredients: 4,
  same_category: true
}]->(r2:Recipe)
```

---

## 인덱스 및 제약조건

```cypher
// 유니크 제약조건
CREATE CONSTRAINT ingredient_name IF NOT EXISTS
FOR (i:Ingredient) REQUIRE i.name IS UNIQUE;

CREATE CONSTRAINT recipe_name IF NOT EXISTS
FOR (r:Recipe) REQUIRE r.name IS UNIQUE;

CREATE CONSTRAINT goal_name IF NOT EXISTS
FOR (g:Goal) REQUIRE g.name IS UNIQUE;

CREATE CONSTRAINT condition_name IF NOT EXISTS
FOR (c:Condition) REQUIRE c.name IS UNIQUE;

CREATE CONSTRAINT diet_name IF NOT EXISTS
FOR (d:Diet) REQUIRE d.name IS UNIQUE;

// 검색용 인덱스
CREATE INDEX ingredient_category IF NOT EXISTS
FOR (i:Ingredient) ON (i.category);

CREATE INDEX recipe_category IF NOT EXISTS
FOR (r:Recipe) ON (r.category);

CREATE INDEX recipe_cuisine IF NOT EXISTS
FOR (r:Recipe) ON (r.cuisine);

CREATE INDEX recipe_calories IF NOT EXISTS
FOR (r:Recipe) ON (r.total_calories);

// 풀텍스트 인덱스 (태그 검색)
CREATE FULLTEXT INDEX recipe_tags IF NOT EXISTS
FOR (r:Recipe) ON EACH [r.tags];
```

---

## 티어별 그래프 레이어

| 티어 | 사용 노드 | 사용 엣지 |
|------|-----------|-----------|
| FREE (엄마밥) | Ingredient, Recipe | REQUIRED_FOR |
| 흑백요리사 | + Technique | + USES_TECHNIQUE, PAIRS_WELL |
| 다이어트코치 | + Goal | + SUITABLE_FOR |
| 건강맞춤 | + Condition | + SAFE_FOR, AVOID_FOR |
| 무지개요리사 | + Diet | + COMPATIBLE_WITH, CAN_REPLACE |
