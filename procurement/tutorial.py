"""Static onboarding, filtered with the same server policy as real endpoints."""
from django.urls import reverse
from accounts.rbac import can, required_capability

STEPS = [
    {'number':1,'title':'식단 계획','why':'식단과 1인분 레시피가 식재료 소요량의 기준이 됩니다.',
     'tasks':'일간·주간 식단을 작성하고 메뉴에 재료와 기준량을 연결합니다. 필요한 경우 기존 파일 업로드를 사용합니다.',
     'inputs':'급식 날짜, 조식·중식·석식, 메뉴, 재료별 1인량과 기준 단위',
     'result':'날짜·식사별 식단과 연결된 레시피',
     'next':'다음 단계에서 같은 날짜·식사의 식수를 확인하고 확정합니다.',
     'warning':'사용 완료된 식단과 연결 레시피는 덮어쓸 수 없습니다. 영양성분·알레르기 자동 검증을 제공한다고 가정하지 마세요.',
     'routes':[('meals:weekly_mealplan_create','주간 식단 작성'),('meals:mealplan_list','식단표 조회'),('meals:menu_list','메뉴·레시피 관리'),('meals:recipe_upload_page','레시피 파일 업로드'),('inventory:ingredient_upload','식재료 파일 업로드')]},
    {'number':2,'title':'AI 식수 예측 및 최종 식수 확정','why':'예측은 참고값이고 발주량의 기준은 영양사가 최종 확정한 인원입니다.',
     'tasks':'AI 결과와 수동 예상 식수를 비교하고 식사별 최종 식수를 저장합니다. AI가 실패해도 수동 업무를 계속할 수 있습니다.',
     'inputs':'날짜·식사, 수동 예상 인원, 최종 확정 인원',
     'result':'예상 식수·최종 확정 식수와 확정 시각',
     'next':'최종 식수가 확정되면 레시피와 결합해 발주 소요량을 계산합니다.',
     'warning':'AI 예측·수동 예상·최종 확정·실측은 다릅니다. 미생성 / 수동 입력 가능 상태와 실제 0명을 구분합니다. 실측 입력 화면과 현재 DB 메뉴의 AI 입력 연결은 후속 범위입니다.',
     'routes':[('forecasting:prediction_create','AI 예측 실행'),('forecasting:prediction_list','AI 예측 결과 조회'),('procurement:workflow_headcounts','예상·최종 식수 관리'),('forecasting:weekly_forecast_report','예측·실측 보고서')]},
    {'number':3,'title':'식재료 소요량 계산 및 발주','why':'필요량과 재고, 납품 포장을 구분해야 부족하거나 중복된 발주를 줄일 수 있습니다.',
     'tasks':'확정 식수와 1인량을 합산하고 재고·안전재고를 반영합니다. 납품규격을 확인한 뒤 발주예정서를 저장하고 업체별 구매발주서를 확정합니다.',
     'inputs':'계산 기간, 최종 식수, 레시피, 실제 업체·납품규격, 필요한 수량 조정',
     'result':'재료 소요량·발주 포장 수량, 저장한 예정서, 업체별 구매발주서',
     'next':'발주 목록에서 업체와 납품 예정 정보를 확인하고 검수를 준비합니다.',
     'warning':'35kg을 7통으로 환산하려면 5kg/통의 명시 규격이 필요합니다. 날짜별 묶음·금요일/주말 계산을 확인하세요. 재검토 표시가 있으면 최신 데이터로 다시 검토합니다. 취소·재발주 완결은 후속입니다.',
     'routes':[('procurement:workflow_preview','소요량·발주예정서'),('procurement:workflow_plans','저장한 발주예정서'),('procurement:order_list','발주 목록'),('procurement:vendor_procurement_report','업체별 구매발주서'),('procurement:workflow_specs','납품규격 관리')]},
    {'number':4,'title':'공급업체 납품 확인 및 검수','why':'공급업체의 수락·출고와 구매자의 실제 합격 입고는 서로 다른 업무입니다.',
     'tasks':'구매자 화면에서 업체의 수주·납품 예정 정보를 확인합니다. 실제 물품의 수량·규격·상태·기한을 확인해 합격량을 저장합니다.',
     'inputs':'실제 납품량, 검수 합격량, 확인 규격, 상태, 수량 차이 사유와 유통기한',
     'result':'검수 기록과 합격 수량만큼의 입고',
     'next':'재고와 수불에서 입고량을 확인하고 조리·사용 업무로 이동합니다.',
     'warning':'공급업체 출고만으로 재고가 증가하지 않습니다. 같은 검수의 중복 제출은 추가 입고를 만들지 않습니다. 반복 분납·검수 정정·반품/재배송은 아직 완결되지 않았습니다.',
     'routes':[('procurement:workflow_inspections','납품·검수 관리'),('procurement:daily_inspection_report','급식물품 검수일지'),('procurement:supplier_list','공급업체 현황')]},
    {'number':5,'title':'재고 및 조리 관리','why':'조리 지시와 실제 재고 사용을 나눠 기록해야 필요량과 잔량을 대사할 수 있습니다.',
     'tasks':'입고·사용·폐기·조정 내역과 주간 수불을 확인합니다. 날짜·식사별 조리지시서를 조회하고 현장 지시·비고를 저장해 Excel 또는 인쇄로 전달합니다.',
     'inputs':'재고 기준 단위의 실제 거래량·일자·사유, 조리 지시·재료별 비고',
     'result':'재고 로그·수불현황, 저장한 조리지시서와 출력 문서',
     'next':'월말 정산 자료에서 발주·검수 금액과 사용 흐름을 대조합니다.',
     'warning':'조리지시서 메모 저장이나 Excel 다운로드는 재고를 자동 차감하지 않습니다. 실제 사용은 별도 기록합니다. 조리 담당자별 작업 완료와 불변 발행본 이력은 후속 범위입니다.',
     'routes':[('inventory:ingredient_list','재고 현황'),('procurement:workflow_transaction','선입고·사용·폐기·조정 기록'),('procurement:workflow_ledger','주간 수불현황'),('meals:cooking_index','조리지시서 조회·수정·출력')]},
    {'number':6,'title':'정산 및 운영 분석','why':'발주와 실제 검수 합격량을 대조해 월별 운영 자료를 검토합니다.',
     'tasks':'기간과 업체를 선택해 발주 금액·검수 합격 비례금액·미검수 품목을 확인하고 관련 문서를 출력합니다.',
     'inputs':'조회 월·기간, 업체, 확인할 발주·검수·수불 내역',
     'result':'월간 검토용 정산 자료와 업무 문서',
     'next':'누락된 입력이나 재검토 사항을 확인하고 다음 기간의 식단 계획을 준비합니다.',
     'warning':'발주 대상일과 검수 확정일의 월 기준이 다를 수 있습니다. 세금 기준이 없으면 지급액은 미확정입니다. 회계 마감·세금계산서 대사·식수당 원가를 완료 기능으로 안내하지 않습니다.',
     'routes':[('procurement:workflow_settlement','월말 정산 검토'),('procurement:doc_monthly_settlement','월간 발주 정산서'),('docs_index','문서·보고서 모음')]},
]


def steps_for(user):
    return [{**{key:value for key,value in step.items() if key!='routes'},
             'links':[{'url':reverse(name),'label':label} for name,label in step['routes']
                      if can(user,required_capability(name,'GET'))]} for step in STEPS]
