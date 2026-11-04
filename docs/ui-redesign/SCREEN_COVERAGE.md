# 화면 적용 범위

공통 base를 상속하는 모든 화면에 동일한 세 모드와 모드 선택이 적용된다. 업무 템플릿의 기존 폼 action·필드·업무 스크립트를 보존했다. 아래 상속 목록은 적용 범위이며, 모든 CRUD 조합을 브라우저로 검증했다는 뜻은 아니다.

브라우저 신규 실행: 로그인·대시보드, 공급업체 등록, 식자재 등록/검색/재조회, 명시적 규격, 메뉴/레시피 작성·수정, Excel 업로드, 일간·주간 식단, 기존 AI 실행, 수동/최종 식수, 발주예정서, 업체별 발주, 검수·중복 요청, 입출고·폐기·수불, 조리지시서 저장/출력, 월 정산, 계정 승인 및 권한. 같은 시나리오를 세 모드에서 각각 실행했다.

자동 Django 렌더링 및 기존 회귀 테스트는 나머지 문서/예외 경로도 검사한다. 대용량 실데이터, 모든 검색 조건 조합, 실제 영양사 인수, 다른 브라우저는 미검증이다. Django 관리자 화면은 기본 업무 구조를 유지한 별도 테마다.

| 템플릿 | 상속/구성 |
|---|---|
| `templates/accounts/login.html` | `base.html` |
| `templates/accounts/signup.html` | `base.html` |
| `templates/admin/base_site.html` | `admin/base_site.html` |
| `templates/base.html` | `include/독립 파일` |
| `templates/docs/daily_inspection_report.html` | `base.html` |
| `templates/docs/doc_cooking_instruction.html` | `base.html` |
| `templates/docs/doc_inspection_log.html` | `base.html` |
| `templates/docs/doc_inventory_status.html` | `base.html` |
| `templates/docs/doc_menu_overview.html` | `base.html` |
| `templates/docs/doc_monthly_settlement.html` | `base.html` |
| `templates/docs/doc_purchase_requisition.html` | `base.html` |
| `templates/docs/index.html` | `base.html` |
| `templates/docs/monthly_inventory_report.html` | `base.html` |
| `templates/docs/monthly_report.html` | `base.html` |
| `templates/docs/vendor_procurement_report.html` | `base.html` |
| `templates/docs/weekly_forecast_report.html` | `base.html` |
| `templates/docs/weekly_inventory_report.html` | `base.html` |
| `templates/docs/weekly_procurement_report.html` | `base.html` |
| `templates/docs/weekly_recipe_report.html` | `base.html` |
| `templates/docs/weekly_report.html` | `base.html` |
| `templates/forecasting/predict_form.html` | `base.html` |
| `templates/forecasting/predict_result.html` | `base.html` |
| `templates/forecasting/prediction_calendar.html` | `base.html` |
| `templates/forecasting/prediction_list.html` | `base.html` |
| `templates/forecasting/required_ingredient_list.html` | `base.html` |
| `templates/home.html` | `base.html` |
| `templates/inventory/ingredient_form.html` | `base.html` |
| `templates/inventory/ingredient_list.html` | `base.html` |
| `templates/inventory/ingredient_upload.html` | `base.html` |
| `templates/inventory/inventory_log_form.html` | `base.html` |
| `templates/meals/deduct_inventory_preview.html` | `base.html` |
| `templates/meals/meal_home.html` | `base.html` |
| `templates/meals/mealplan_bulk_upload.html` | `base.html` |
| `templates/meals/mealplan_create.html` | `base.html` |
| `templates/meals/mealplan_list.html` | `base.html` |
| `templates/meals/menu_create.html` | `base.html` |
| `templates/meals/menu_list.html` | `base.html` |
| `templates/meals/menu_update.html` | `base.html` |
| `templates/meals/monthly_mealplan_create.html` | `base.html` |
| `templates/meals/recipe_create.html` | `base.html` |
| `templates/meals/recipe_upload.html` | `base.html` |
| `templates/meals/weekly_mealplan_create.html` | `base.html` |
| `templates/partials/top_nav.html` | `include/독립 파일` |
| `templates/procurement/order_create.html` | `base.html` |
| `templates/procurement/order_detail.html` | `base.html` |
| `templates/procurement/order_from_mealplan.html` | `base.html` |
| `templates/procurement/order_list.html` | `base.html` |
| `templates/procurement/procurement_home.html` | `base.html` |
| `templates/procurement/supplier_list.html` | `base.html` |
| `templates/ui/compare.html` | `base.html` |
| `templates/ui/mode_switcher.html` | `include/독립 파일` |
| `templates/workflow/base.html` | `base.html` |
| `templates/workflow/cooking_detail.html` | `workflow/base.html` |
| `templates/workflow/cooking_index.html` | `workflow/base.html` |
| `templates/workflow/form.html` | `workflow/base.html` |
| `templates/workflow/hub.html` | `workflow/base.html` |
| `templates/workflow/inspections.html` | `workflow/base.html` |
| `templates/workflow/ledger.html` | `workflow/base.html` |
| `templates/workflow/master.html` | `workflow/base.html` |
| `templates/workflow/plan.html` | `workflow/base.html` |
| `templates/workflow/preview.html` | `workflow/base.html` |
| `templates/workflow/recipes.html` | `workflow/base.html` |
| `templates/workflow/settlement.html` | `workflow/base.html` |
