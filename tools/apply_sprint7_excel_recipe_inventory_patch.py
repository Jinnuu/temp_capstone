from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]


def backup(path: Path):
    if path.exists():
        bak = path.with_suffix(path.suffix + ".bak_final_excel_patch")
        shutil.copy2(path, bak)
        print(f"backup: {bak}")


def main():
    targets = [
        ROOT / "meals" / "urls.py",
        ROOT / "inventory" / "urls.py",
    ]

    for target in targets:
        backup(target)

    print("패치 파일은 이미 해당 경로에 들어가 있습니다.")
    print("다음 명령을 실행하세요:")
    print("  python manage.py check")
    print("  python manage.py runserver")
    print()
    print("확인 URL:")
    print("  /inventory/ingredients/upload/")
    print("  /meals/menu_list/")
    print("  /meals/menu/upload-excel/")
    print("  /meals/deduct_inventory/?date=2026-06-01&meal_type=중식")


if __name__ == "__main__":
    main()
