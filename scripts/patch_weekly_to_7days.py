from pathlib import Path

path = Path("meals/views.py")
text = path.read_text(encoding="utf-8")

replacements = [
    ("dates = [start_date + timedelta(days=i) for i in range(8)]", "dates = [start_date + timedelta(days=i) for i in range(7)]"),
    ("target_date__lte=dates[7]", "target_date__lte=dates[-1]"),
    ("weekdays_list = ['월', '화', '수', '목', '금', '토', '일', '월(다음주)']", "weekdays_list = ['월', '화', '수', '목', '금', '토', '일']"),
    ("'is_next_monday': (i == 7)", "'is_next_monday': False"),
]

changed = False
for old, new in replacements:
    if old in text:
        text = text.replace(old, new)
        changed = True

path.write_text(text, encoding="utf-8")
print("weekly_mealplan_create를 월~일 7일 입력 기준으로 정리했습니다." if changed else "치환 대상이 없었습니다. 이미 수정되었을 수 있습니다.")
