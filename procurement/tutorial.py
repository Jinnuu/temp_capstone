"""Beginner-only educational content. No business data or practice fixtures.

Keep the six numeric IDs and v1 reading-state namespace stable. These routes are
available in the deployed Preview; local Phase 2-A delivery routes are deliberately
not advertised here. Add future capability content only after deployment.
"""
from django.urls import reverse
from accounts.rbac import can, required_capability

STEPS = [
    {'number': 1, 'title': '어떤 음식을 만들까요?',
     'sentence': '먼저 언제, 어떤 음식을 만들지 정해요.',
     'example': '11월 10일 점심에 카레라이스를 만들기로 했어요.',
     'scene_title': '11월 10일 · 점심', 'scene_detail': '오늘의 메뉴는 카레라이스',
     'instructions': ['「주간 식단 작성」에서 날짜와 점심 칸을 찾아요.', '메뉴 검색에 카레라이스를 입력하고 후보를 누르면 바로 저장돼요. 메뉴가 없다면 먼저 메뉴·레시피 관리에서 등록해요.'],
     'next': '메뉴를 정했어요. 이제 몇 명이 먹을지 생각해 볼까요?',
     'term': '식단은 날짜별 음식 계획, 레시피는 음식에 들어가는 재료와 1인분 양이에요.',
     'learn': '메뉴에는 재료별 1인분 양과 단위가 연결되어 있어야 해요. 이 예시의 날짜는 설명용이므로 실제 작업할 날짜를 선택하세요. 사용 완료된 식단은 덮어쓰지 못할 수 있어요.',
     'routes': [('meals:weekly_mealplan_create', '주간 식단 작성'), ('meals:mealplan_list', '식단표 조회'), ('meals:menu_list', '메뉴·레시피 관리'), ('meals:recipe_upload_page', '레시피 파일 업로드'), ('inventory:ingredient_upload', '식재료 파일 업로드')]},
    {'number': 2, 'title': '몇 명이 먹을까요?',
     'sentence': '식사할 사람 수를 예상하고, 준비할 최종 인원을 정해요.',
     'example': '카레라이스를 먹을 사람이 100명이라고 예상했어요. 확인 후 최종 인원도 100명으로 정해요.',
     'scene_title': '준비할 사람 수 · 100명', 'scene_detail': 'AI는 참고 → 마지막 결정은 영양사',
     'instructions': ['「예상·최종 식수 관리」에서 날짜와 식사를 선택해요.', '예상 인원과 최종 인원을 입력하고 확정 여부를 확인한 뒤 「식수 저장」을 눌러요.'],
     'next': '100명으로 정했어요. 이 인원에게 필요한 재료의 양을 알아볼까요?',
     'term': '식수는 식사하는 사람 수예요. AI 예측, 직접 예상, 최종 확정, 실제로 먹은 인원은 서로 달라요.',
     'learn': 'AI 예측 결과는 참고값이에요. 예측이 없어도 직접 예상하고 최종 인원을 정할 수 있어요. 발주에는 최종 확정 인원을 사용해요. 실제 인원(실측)을 입력하지 않았다면 예측 오차도 알 수 없어요.',
     'routes': [('procurement:workflow_headcounts', '예상·최종 식수 관리'), ('forecasting:prediction_list', 'AI 예측 결과 조회'), ('forecasting:prediction_create', 'AI 예측 실행'), ('forecasting:weekly_forecast_report', '예측·실측 보고서')]},
    {'number': 3, 'title': '어떤 재료가 얼마나 필요할까요?',
     'sentence': '필요한 재료의 양을 보고, 부족한 만큼 공급업체에 주문해요.',
     'example': '교육용 카레 예시에서 감자 3kg, 당근 2kg, 양파 2kg이 필요하다고 해 볼게요. 이미 가진 양을 확인하고 부족분을 주문해요.',
     'scene_title': '교육용 재료 예시', 'scene_detail': '감자 3kg · 당근 2kg · 양파 2kg',
     'instructions': ['「소요량·발주예정서」에서 기간을 고르고 「미리보기」를 눌러요.', '수량과 실제 포장규격을 확인하고 「발주예정서 저장」을 눌러요. 저장한 문서에서 「업체별 구매발주서 확정·저장」을 눌러 주문을 확정해요.'],
     'next': '주문을 확인했어요. 재료가 도착하면 수량과 상태를 살펴봐요.',
     'term': '소요량은 필요한 재료의 양, 발주는 공급업체에 재료를 주문하는 일이에요.',
     'learn': '예시 수량은 실제 레시피나 영양 기준이 아닙니다. 실제 계산에는 등록한 레시피와 최종 인원, 재고를 사용해요. 포장 수량은 등록한 실제 규격으로만 계산해요. 예를 들어 5kg/통이 등록되어 있을 때만 kg을 통으로 바꿀 수 있어요.',
     'routes': [('procurement:workflow_preview', '소요량·발주예정서'), ('procurement:workflow_plans', '저장한 발주예정서'), ('procurement:order_list', '발주 목록'), ('procurement:vendor_procurement_report', '업체별 구매발주서'), ('procurement:workflow_specs', '납품규격 관리')]},
    {'number': 4, 'title': '주문한 재료가 잘 도착했나요?',
     'sentence': '도착한 재료의 수량과 상태를 확인하고, 사용할 수 있는 양만 등록해요.',
     'example': '카레용 감자 3kg이 도착했어요. 수량과 상태가 괜찮다면 합격량을 3kg으로 기록해요.',
     'scene_title': '도착한 감자 · 3kg', 'scene_detail': '수량·상태 확인 → 합격한 양만 재고로',
     'instructions': ['「납품·검수 관리」에서 주문한 품목의 「검수 기록·확인」을 눌러요.', '실제 납품량, 합격량, 규격과 상태를 확인한 뒤 「저장·확정」을 눌러요. 차이가 있으면 사유도 적어요.'],
     'next': '사용할 수 있는 재료를 확인했어요. 이제 조리를 준비해 볼까요?',
     'term': '검수는 도착한 재료의 수량과 상태 확인, 입고는 확인한 재료를 재고에 등록하는 일이에요.',
     'learn': '업체가 출고했다고 재고가 바로 늘지는 않아요. 구매자가 합격량을 저장해야 반영돼요. 잘못 검수했거나 여러 번 나누어 납품하는 경우에는 담당자에게 확인하세요. 공개 Preview의 정정·반품 절차는 아직 완성되지 않았어요.',
     'routes': [('procurement:workflow_inspections', '납품·검수 관리'), ('procurement:daily_inspection_report', '급식물품 검수일지'), ('procurement:supplier_list', '공급업체 현황')]},
    {'number': 5, 'title': '이제 음식을 준비해 볼까요?',
     'sentence': '재료와 조리할 양을 확인하고, 조리할 사람에게 준비 내용을 전달해요.',
     'example': '100명분 카레라이스의 조리지시서를 확인해요. 감자·당근·양파가 준비됐는지 보고 조리할 때 필요한 메모를 남겨요.',
     'scene_title': '카레라이스 · 100명분 준비', 'scene_detail': '재료 확인 → 조리지시서 전달',
     'instructions': ['「조리지시서 조회·수정·출력」에서 날짜와 식사를 골라요.', '재료의 양과 메모를 확인한 뒤 필요한 내용을 저장하거나 Excel·인쇄로 전달해요. 실제 재료 사용량은 별도 재고 기록에 남겨요.'],
     'next': '조리 준비를 마쳤어요. 마지막으로 오늘의 기록을 확인해요.',
     'term': '조리지시서는 어떤 음식을 얼마나 준비할지 전달하는 문서예요.',
     'learn': '조리지시서를 저장하거나 Excel로 받는 것만으로 재고가 줄지 않아요. 실제 사용량은 「선입고·사용·폐기·조정 기록」에서 별도로 남겨요. 사용량 입력도 실제 업무 기록이므로 확인 후 저장하세요.',
     'routes': [('meals:cooking_index', '조리지시서 조회·수정·출력'), ('inventory:ingredient_list', '재고 현황'), ('procurement:workflow_transaction', '선입고·사용·폐기·조정 기록'), ('procurement:workflow_ledger', '주간 수불현황')]},
    {'number': 6, 'title': '오늘 급식은 어떻게 마무리할까요?',
     'sentence': '주문한 재료, 들어온 재료, 사용한 재료와 금액을 돌아봐요.',
     'example': '100명분 카레 급식이 끝났어요. 감자가 얼마나 들어오고 사용됐는지, 주문·납품 금액에 확인할 내용은 없는지 살펴봐요.',
     'scene_title': '오늘 기록 돌아보기', 'scene_detail': '주문 → 도착 → 사용 → 금액 확인',
     'instructions': ['「월말 정산 검토」에서 확인할 월과 업체를 골라 조회해요.', '「주간 수불현황」에서 재료가 들어오고 사용된 기록도 확인해요. 빠진 내용은 해당 업무 메뉴에서 확인하세요.'],
     'next': '전체 흐름을 살펴봤어요. 다음 급식도 음식 계획부터 같은 순서로 시작하면 돼요.',
     'term': '수불은 재료가 들어오고 사용된 기록, 정산은 주문·납품 금액을 확인하는 일이에요.',
     'learn': '정산 화면은 검토용 자료예요. 세금 기준이 없으면 최종 지급액은 아직 정해지지 않아요. 이 가이드를 다 읽어도 실제 주문·검수는 처리되지 않아요.',
     'routes': [('procurement:workflow_settlement', '월말 정산 검토'), ('procurement:workflow_ledger', '주간 수불현황'), ('procurement:doc_monthly_settlement', '월간 발주 정산서'), ('docs_index', '문서·보고서 모음')]},
]


def steps_for(user):
    result = []
    for step in STEPS:
        links = [{'url': reverse(name), 'label': label} for name, label in step['routes']
                 if can(user, required_capability(name, 'GET'))]
        result.append({**{key: value for key, value in step.items() if key != 'routes'},
                       'links': links, 'primary': links[0] if links else None})
    return result
