# Cypher 쿼리 목록

## 기본 쿼리 (FREE 티어)

### 1. 재료 → 레시피 역방향 쿼리

보유 재료로 만들 수 있는 레시피 검색 (커버리지 기반)

```cypher
// 파라미터: $my_ingredients = ["돼지고기", "김치", "두부", "파"]
MATCH (r:Recipe)-[:REQUIRED_FOR]-(i:Ingredient)
WHERE i.name IN $my_ingredients
WITH r, 
     count(i) AS matched,
     size((r)-[:REQUIRED_FOR]-()) AS total
WITH r, matched, total,
     round(matched * 100.0 / total) AS coverage
WHERE coverage >= 60  // 60% 이상 재료 보유
RETURN r.name AS recipe,
       r.time_minutes AS time,
       r.difficulty AS difficulty,
       coverage AS match_percent,
       total - matched AS missing_count
ORDER BY coverage DESC, r.time_minutes ASC
LIMIT 10
```

### 2. 부족한 재료 찾기

선택한 레시피에 부족한 재료 목록

```cypher
// 파라미터: $recipe_name, $my_ingredients
MATCH (r:Recipe {name: $recipe_name})-[req:REQUIRED_FOR]-(i:Ingredient)
WHERE NOT i.name IN $my_ingredients
RETURN i.name AS missing_ingredient,
       req.amount AS amount,
       req.unit AS unit,
       i.category AS category
ORDER BY i.category
```

### 3. 카테고리별 검색

```cypher
// 파라미터: $category, $my_ingredients
MATCH (r:Recipe {category: $category})-[:REQUIRED_FOR]-(i:Ingredient)
WHERE i.name IN $my_ingredients
WITH r, count(i) AS matched
WHERE matched >= 2
RETURN r.name, r.time_minutes, matched
ORDER BY matched DESC
LIMIT 10
```

---

## 다이어트코치 쿼리 (PREMIUM)

### 4. 칼로리 제한 + 재료 매칭

```cypher
// 파라미터: $my_ingredients, $max_calories
MATCH (r:Recipe)-[:REQUIRED_FOR]-(i:Ingredient)
WHERE i.name IN $my_ingredients
AND r.total_calories <= $max_calories
WITH r, count(i) AS matched,
     size((r)-[:REQUIRED_FOR]-()) AS total
WITH r, round(matched * 100.0 / total) AS coverage
WHERE coverage >= 50
RETURN r.name,
       r.total_calories AS calories,
       r.total_protein AS protein,
       coverage
ORDER BY r.total_protein DESC, r.total_calories ASC
LIMIT 10
```

### 5. 목표 기반 추천

```cypher
// 파라미터: $my_ingredients, $goal_name
MATCH (r:Recipe)-[:REQUIRED_FOR]-(i:Ingredient)
WHERE i.name IN $my_ingredients
MATCH (r)-[s:SUITABLE_FOR]->(g:Goal {name: $goal_name})
WITH r, s.score AS fitness_score, count(i) AS matched
WHERE matched >= 2
RETURN r.name,
       r.total_calories,
       r.total_protein,
       fitness_score
ORDER BY fitness_score DESC, matched DESC
LIMIT 10
```

### 6. 매크로 밸런스 검색

```cypher
// 파라미터: 단백질 최소, 탄수화물 최대
MATCH (r:Recipe)
WHERE r.total_protein >= $min_protein
AND r.total_carbs <= $max_carbs
AND r.total_calories <= $max_calories
RETURN r.name,
       r.total_calories,
       r.total_protein,
       r.total_carbs,
       r.total_fat
ORDER BY r.total_protein DESC
LIMIT 10
```

---

## 건강맞춤 쿼리 (PREMIUM)

### 7. 건강 상태 필터링

위험 레시피 제외, 안전 레시피 우선

```cypher
// 파라미터: $my_ingredients, $condition_name
MATCH (r:Recipe)-[:REQUIRED_FOR]-(i:Ingredient)
WHERE i.name IN $my_ingredients
// 위험한 레시피 완전 제외
AND NOT (r)-[:AVOID_FOR]->(:Condition {name: $condition_name})
WITH r, count(i) AS matched,
     exists((r)-[:SAFE_FOR]->(:Condition {name: $condition_name})) AS recommended
RETURN r.name,
       r.total_calories,
       recommended,
       matched
ORDER BY recommended DESC, matched DESC
LIMIT 10
```

### 8. 복수 건강 상태 필터링

여러 건강 상태 동시 고려

```cypher
// 파라미터: $conditions = ["당뇨", "고혈압"]
MATCH (r:Recipe)-[:REQUIRED_FOR]-(i:Ingredient)
WHERE i.name IN $my_ingredients
// 모든 조건에서 위험하지 않아야 함
AND NOT EXISTS {
  MATCH (r)-[:AVOID_FOR]->(c:Condition)
  WHERE c.name IN $conditions
}
WITH r, count(i) AS matched
RETURN r.name, matched
ORDER BY matched DESC
LIMIT 10
```

### 9. 영양소 제한 검색

특정 영양소 제한 (나트륨, 퓨린 등)

```cypher
// 파라미터: 나트륨 제한 (고혈압)
MATCH (r:Recipe)-[req:REQUIRED_FOR]-(i:Ingredient)
WHERE i.name IN $my_ingredients
WITH r, sum(i.sodium_per_100g * req.amount / 100) AS total_sodium
WHERE total_sodium <= $max_sodium
RETURN r.name, total_sodium
ORDER BY total_sodium ASC
LIMIT 10
```

---

## 무지개요리사 쿼리 (PREMIUM)

### 10. 비건/식단 호환 검색

```cypher
// 파라미터: $diet_name = "비건"
MATCH (r:Recipe)-[:COMPATIBLE_WITH]->(d:Diet {name: $diet_name})
MATCH (r)-[:REQUIRED_FOR]-(i:Ingredient)
WHERE i.name IN $my_ingredients
WITH r, count(i) AS matched
RETURN r.name, r.category, matched
ORDER BY matched DESC
LIMIT 10
```

### 11. 대체재 포함 검색

비건 대체재로 변환 가능한 레시피

```cypher
// 원래 레시피에서 육류를 대체재로 바꿀 수 있는지 확인
MATCH (r:Recipe)-[:REQUIRED_FOR]-(original:Ingredient)
WHERE NOT original.vegan
OPTIONAL MATCH (alt:Ingredient)-[rep:CAN_REPLACE]->(original)
WHERE alt.vegan AND rep.context = "비건"
WITH r, 
     collect(DISTINCT original.name) AS meat_ingredients,
     collect(DISTINCT alt.name) AS alternatives
WHERE size(alternatives) > 0
RETURN r.name,
       meat_ingredients,
       alternatives
LIMIT 10
```

### 12. 영양 보완 조합

비건 식단에서 단백질/B12 보완

```cypher
// 단백질 높은 비건 레시피
MATCH (r:Recipe)-[:COMPATIBLE_WITH]->(:Diet {name: "비건"})
WHERE r.total_protein >= 20
RETURN r.name, r.total_protein
ORDER BY r.total_protein DESC
LIMIT 10
```

---

## 흑백요리사 쿼리 (PREMIUM)

### 13. 테크닉 기반 추천

```cypher
// 파라미터: $my_ingredients, 고급 기법 포함
MATCH (r:Recipe)-[:REQUIRED_FOR]-(i:Ingredient)
WHERE i.name IN $my_ingredients
MATCH (r)-[:USES_TECHNIQUE]->(t:Technique)
WHERE t.difficulty IN ["중", "상"]
WITH r, collect(t.name) AS techniques, count(DISTINCT i) AS matched
RETURN r.name,
       techniques,
       r.difficulty,
       matched
ORDER BY size(techniques) DESC, matched DESC
LIMIT 5
```

### 14. 재료 페어링 추천

선택한 재료와 잘 어울리는 추가 재료

```cypher
// 파라미터: $main_ingredient
MATCH (main:Ingredient {name: $main_ingredient})
      -[:PAIRS_WELL]->(pair:Ingredient)
RETURN pair.name, pair.category
LIMIT 10
```

### 15. 고급 플레이팅 레시피

```cypher
MATCH (r:Recipe)-[:USES_TECHNIQUE]->(t:Technique)
WHERE t.name IN ["분자요리", "플랑베", "수비드"]
RETURN r.name, collect(t.name) AS techniques
ORDER BY size(techniques) DESC
LIMIT 10
```

---

## 유틸리티 쿼리

### 16. 레시피 유사도 검색

```cypher
// 파라미터: $recipe_name
MATCH (r1:Recipe {name: $recipe_name})-[s:SIMILAR_TO]->(r2:Recipe)
RETURN r2.name, s.score, s.shared_ingredients
ORDER BY s.score DESC
LIMIT 5
```

### 17. 재료 자동완성

```cypher
// 파라미터: $prefix = "김"
MATCH (i:Ingredient)
WHERE i.name STARTS WITH $prefix
RETURN i.name, i.category
LIMIT 10
```

### 18. 인기 레시피 (특정 재료)

```cypher
// 이 재료가 들어간 레시피 중 가장 많이 조회된 것
MATCH (i:Ingredient {name: $ingredient})-[:REQUIRED_FOR]->(r:Recipe)
RETURN r.name, r.category, r.time_minutes
ORDER BY r.view_count DESC
LIMIT 10
```

### 19. 시간 기반 필터

```cypher
// 30분 이내 요리
MATCH (r:Recipe)-[:REQUIRED_FOR]-(i:Ingredient)
WHERE i.name IN $my_ingredients
AND r.time_minutes <= 30
WITH r, count(i) AS matched
RETURN r.name, r.time_minutes, matched
ORDER BY r.time_minutes ASC, matched DESC
LIMIT 10
```

### 20. 난이도 기반 필터

```cypher
// 쉬운 요리만
MATCH (r:Recipe {difficulty: "쉬움"})-[:REQUIRED_FOR]-(i:Ingredient)
WHERE i.name IN $my_ingredients
WITH r, count(i) AS matched
RETURN r.name, r.time_minutes, matched
ORDER BY matched DESC
LIMIT 10
```

---

## 집계 쿼리

### 통계

```cypher
// 전체 통계
MATCH (r:Recipe) RETURN count(r) AS total_recipes;
MATCH (i:Ingredient) RETURN count(i) AS total_ingredients;
MATCH ()-[req:REQUIRED_FOR]->() RETURN count(req) AS total_relations;
```

### 카테고리별 레시피 수

```cypher
MATCH (r:Recipe)
RETURN r.category, count(r) AS count
ORDER BY count DESC
```
