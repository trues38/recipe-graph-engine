"""전체 정규화 파이프라인 실행"""

import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent

PIPELINE_STEPS = [
    ("normalize_recipe_names.py", "레시피 이름 정규화"),
    ("normalize_recipe_steps.py", "조리순서 정규화"),
    ("auto_classify_recipes.py", "다차원 자동분류"),
    ("deduplicate_recipes.py", "중복제거"),
    ("enrich_nutrition.py", "영양정보 연동"),
    ("reload_vps_data.py", "VPS Neo4j 재로드"),
]


def run_script(script_name: str, description: str) -> bool:
    """스크립트 실행"""
    script_path = SCRIPTS_DIR / script_name

    if not script_path.exists():
        print(f"  [SKIP] {script_name} not found")
        return False

    print(f"\n{'='*60}")
    print(f"[{description}]")
    print(f"{'='*60}")

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=SCRIPTS_DIR.parent
    )

    if result.returncode != 0:
        print(f"  [ERROR] {script_name} failed with code {result.returncode}")
        return False

    return True


def main():
    print("=" * 60)
    print("레시피 정규화 파이프라인")
    print("=" * 60)

    # 인자로 시작 단계 받기
    start_step = 1
    if len(sys.argv) > 1:
        try:
            start_step = int(sys.argv[1])
        except ValueError:
            pass

    print(f"\n시작 단계: {start_step}")

    success_count = 0
    for i, (script, desc) in enumerate(PIPELINE_STEPS, 1):
        if i < start_step:
            print(f"\n[{i}] {desc} - SKIPPED")
            continue

        if run_script(script, f"{i}. {desc}"):
            success_count += 1
        else:
            print(f"\n파이프라인 중단됨 (단계 {i})")
            break

    print(f"\n" + "=" * 60)
    print(f"완료! ({success_count}/{len(PIPELINE_STEPS)} 단계)")
    print("=" * 60)


if __name__ == "__main__":
    main()
