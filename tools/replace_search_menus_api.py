from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
VIEWS = ROOT / "meals" / "views.py"

NEW_FUNCTION = """def search_menus_api(request):
    \"\"\"메뉴 검색 API.

    기존 TF-IDF 검색은 테스트 메뉴나 무관 메뉴까지 넓게 노출되는 문제가 있어,
    Sprint7에서는 '포함 + 유사도' 기반으로 후보를 제한한다.
    \"\"\"
    query = request.GET.get("q", "").strip()
    menus = list(Menu.objects.all().order_by("name"))

    if not query:
        results = [
            {"id": menu.id, "name": menu.name, "category": menu.category or "", "score": 1.0}
            for menu in menus[:20]
        ]
        return JsonResponse({"results": results})

    from .search_utils import fuzzy_menu_results

    results = fuzzy_menu_results(menus, query, limit=12)
    return JsonResponse({"results": results})
"""


def main():
    if not VIEWS.exists():
        print(f"views.py를 찾지 못했습니다: {VIEWS}", file=sys.stderr)
        sys.exit(1)

    text = VIEWS.read_text(encoding="utf-8")
    backup = VIEWS.with_suffix(".py.bak_search_menus_api")
    backup.write_text(text, encoding="utf-8")

    pattern = re.compile(
        r"def search_menus_api\(request\):\n"
        r".*?"
        r"(?=\n@csrf_exempt|\ndef add_diet_menu_api|\ndef remove_diet_menu_api|\ndef weekly_mealplan_create|\Z)",
        re.DOTALL,
    )

    if not pattern.search(text):
        print("search_menus_api 함수를 찾지 못했습니다. 수동으로 meals/views.py를 확인하세요.", file=sys.stderr)
        sys.exit(1)

    new_text = pattern.sub(NEW_FUNCTION.rstrip() + "\n", text, count=1)
    VIEWS.write_text(new_text, encoding="utf-8")

    print("OK: meals/views.py의 search_menus_api를 fuzzy 검색 버전으로 교체했습니다.")
    print(f"백업 파일: {backup}")


if __name__ == "__main__":
    main()
