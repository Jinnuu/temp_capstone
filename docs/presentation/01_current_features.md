# 식수센스(SNP) — 현재 구현 기능 조사

조사일: 2026-10-19. 작업 브랜치 `integration/sprint7-kanghoon`, HEAD `a8d9fae`.

## 조사 기준과 증거의 한계

사용자가 지정한 발표 명칭은 ‘식수센스(SNP)’다. 코드·일부 화면에는 S&P/Smart Nutritionist Program 명칭이 남아 있다. 본 문서는 현재 **작업 트리**를 조사하며 HEAD만의 기능 목록이 아니다. 조리지시서 및 실제 양식 개선 등 미커밋·미추적 파일도 포함한다.

- 완료: 명시한 좁은 기능 범위에서 화면→View/서비스→DB 연결과 해당 저장·계산·예외 테스트의 과거 실행 증거가 함께 확인됨.
- 부분 구현: 주요 경로는 있으나 요구 범위 일부, 정상 모델 경로, 독립 문서 또는 업무 예외 등이 미완성/미검증.
- 미구현: 요구를 충족하는 핵심 모델·경로·화면을 발견하지 못함.
- 실행 증거는 **기존 로그/산출물 열람**이다. 이번 조사에서는 서버·테스트·모델 추론·DB 접근을 실행하지 않았다. 과거 로그는 현재 배포 상태나 실데이터 인수 증거가 아니며, 모든 로그가 소스 트리 해시에 묶여 있지는 않다.

### 증거 색인

| ID | 실제 근거 | 의미와 한계 |
|---|---|---|
| T1 | [SQLite 전체 로그](../../verification/cooking-format/sqlite.log), [MariaDB 전체 로그](../../verification/cooking-format/mariadb.log) | 각각 Ran 117 tests / OK. 신규 조리지시서16개 포함. 정확도·실운영·동시 부하 검증과 다름 |
| T2 | [업무 회귀](../../integration_tests/test_requirements.py), [기존 통합 회귀](../../integration_tests/test_workflows.py) | 입력→저장·재조회, 부족재고·규격·중복·권한·FIFO 등 구체적 단언 확인 |
| T3 | [업무 브라우저 결과](../../verification/requirements/browser.json), [실행 코드](../../integration_tests/browser_workflow.cjs) | 로그인→식수 확정→발주→검수→차감→수불·PDF. 이 시나리오는 식재료·메뉴를 화면에서 신규 등록하는 시험은 아님 |
| T4 | [조리지시서 결과](../../verification/cooking-format/browser.json), [실행 코드](../../integration_tests/browser_cooking.cjs), [테스트](../../integration_tests/test_cooking.py) | 저장·다운로드·인쇄 CSS/PDF·식수 변경 시 총량 재계산. 실제 프린터 시험 아님 |
| T5 | [JavaScript 로그](../../verification/feedback/javascript-direct.log) | 재고 예약·안전재고·반복 재료 등 4개 통과 |
| T6 | [중단된 전수 점검의 baseline](../../verification/final-readiness/sqlite-baseline.log) | 117개 OK만 확인. 전체 14단계 브라우저 전수 점검 성공 로그는 발견하지 못함 |

## 기능별 조사

프론트 ‘있음’은 Django Template/HTML 폼·JS의 존재와 URL 연결이다. DB ‘있음’은 ORM/모델 연결이며 실제 운영 DB를 조회했다는 뜻이 아니다.

| ID·기능명 | 실제 동작 방식 | 프론트 | 백엔드 | DB | 상태 | 관련 소스와 판단 근거 |
|---|---|---|---|---|---|---|
| F01 일간 식단 작성·수정 | 날짜의 조·중·석식 메뉴를 저장하고 기존 식단 ID를 유지하며 변경 후 최종 식수를 해제 | 있음 | 있음 | DietPlan/DietMenu | 완료(일간 경로) | `meals/views.py:mealplan_create`, `meals/urls.py`, `templates/meals/mealplan_create.html`; T2의 daily_edit_preserves_plan_identity, empty_selection 단언 |
| F02 주간 식단 편집 | 주간 날짜·끼니 칸에서 메뉴 검색·추가·삭제, 차주 월요일 조·중식 영역 제공 | 있음 | 있음 | 있음 | 완료(기본 편집) | `meals/views.py:weekly_mealplan_create/add_diet_menu_api/remove_diet_menu_api`, `templates/meals/weekly_mealplan_create.html`; T2의 weekly_page_keeps_search_and_next_monday_editing 및 메뉴 API 테스트. 모든 브라우저 조합을 시험한 것은 아님 |
| F03 월간 식단 관리 | 월간 조회·날짜별 접근·파일 업로드, 전용 신규 일괄 작성은 안내 화면 중심 | 일부 | 일부 | 있음 | 부분 구현 | `meals/views_extra.py:monthly_mealplan_create`, `meals/views.py:mealplan_list/monthly_meal_plan_document`; 월간 독립 일괄 입력 폼 미완성 |
| F04 식단 파일 업로드 | 행형·가로형·달력형 데이터를 읽어 날짜/끼니별 식단 갱신, 변경 시 확정 해제 | 있음 | 있음 | 있음 | 완료(지원 형식 범위) | `meals/views_extra.py:mealplan_bulk_upload`, `templates/meals/mealplan_bulk_upload.html`; `meals/tests.py` CSV/XLSX/XLTX·날짜/끼니 오류·덮어쓰기 회귀, T1 |
| F05 메뉴 CRUD·레시피 연결 | 메뉴와 재료를 Recipe로 연결, 검색·목록·변경·삭제 | 있음 | 있음 | Menu/Recipe | 완료(기본 경로) | `meals/views.py:menu_create/menu_update/menu_delete/recipe_create`, `templates/meals/`; T2의 new_menu_name_api_and_delete_endpoint와 레시피 API 테스트. 모든 메뉴 편집 예외의 완전 검증은 아님 |
| F06 1인량·단위·조리정보 관리 | 레시피 기준량·단위와 메뉴 조리정보 저장, 비정상 수량·단위 환산 거부 | 있음 | 있음 | Recipe/Menu | 완료(공통 업무 화면) | `procurement/workflow_forms.py:RecipeDetailForm`, `workflow_views.py:recipe_detail`, `templates/workflow/recipes.html`; T2의 recipe_unit_and_cooking_notes_ui 및 nonpositive_amounts 단언 |
| F07 레시피·식재료 업로드 | Excel/CSV 식재료, Excel 레시피 업로드와 API 연결. 레시피 단위가 식재료 재고 단위를 덮지 않도록 처리 | 있음 | 있음 | 있음 | 완료(검증 형식 범위) | `inventory/release_patch_views.py`, `inventory/services.py`, `meals/release_patch_views.py`, `meals/recipe_file_views.py`; T2 업로드·rollback·중복 갱신·단위 보존 테스트 |
| F08 AI 식수 예측 생성·조회 | 날짜별 조·중·석식 저장 모델 추론→AttendancePrediction 저장→목록/달력/상세 조회 | 있음 | 있음 | AttendancePrediction | 부분 구현 | `forecasting/views.py`, `services/prediction_service.py/model_loader.py/processor.py`; T1·`test_ai.py` 실제 모델 추론·DB 저장 성공. 정상 SBERT 경로/정확도/모든 외부 데이터 경로 미검증 |
| F09 수동 식수와 최종 확정 | 수동 예상·AI 참고·최종 식수/확정시점을 구분. 0명 허용, 음수/비정수 제한, 변경 시 발주 재검토 | 있음 | 있음 | DietPlan/ProcurementPlan | 완료(확정 흐름) | `procurement/workflow.py:save_headcount/invalidate_plans`, `workflow_views.py:hub`, `templates/workflow/hub.html`; T2 수동/AI/0명/해제·T3/T4 실제 폼 저장 |
| F10 식재료 소요량·부족분 | 확정 식수×명시 단위 1인량, 동일 재료 합산, 재고·안전재고 반영 | 있음 | 있음 | 조회/계획 저장 | 완료(공통 발주 경로) | `procurement/workflow.py:build_preview`, `forecasting/services/ingredient_calc.py`; T2 repeated_ingredient_aggregated_safety_applied_once, stock_surplus. 레거시 조회에는 재료명을 키로 합산하는 코드가 있어 동명 이종 품목까지 보편 보장한다고 발표하면 안 됨 |
| F11 식재료 기준정보 | 이름·분류·업체·규격·단위·단가·안전재고 등록/목록/검색/정렬 | 있음 | 있음 | Ingredient | 부분 구현(관리 전체) | `inventory/views.py:ingredient_create/ingredient_list`, `inventory/forms.py`; 등록·분류 정정은 T2. `inventory/urls.py`에 일반 식재료 편집 경로 없음. 전면 CRUD 완성으로 부르면 안 됨 |
| F12 카테고리·오분류 정정 | 관리자가 분류를 만들고 선택 품목 재분류 또는 기존 이름을 일괄 변경 | 있음 | 있음 | IngredientCategory/Ingredient | 완료(관리 도구) | `workflow_views.py:categories`, `workflow_forms.py:CategoryForm`, `templates/workflow/master.html`; T2 category_rename_reclassifies_and_duplicate_shows_error. 실제 전 품목 정분류 여부는 미확인 |
| F13 재고 원장·kg 선입고 | 입고/출고/폐기/조정 수량·거래일자 기록, 재고 부족·중복 요청 제한 | 있음 | 있음 | InventoryLog/InventoryTransactionKey | 완료(신규 거래) | `procurement/workflow.py:record_inventory`, `workflow_views.py:stock_transaction`; T2 idempotency_and_shortage, same_legacy_stock_form_request. 김치·쌀은 등록된 기준 단위가 kg인 경우 지원 |
| F14 식사 완료 재고 차감 | 식사별 확정 소요량을 출고하고 is_served와 거래 잠금으로 반복 차감 제한 | 있음 | 있음 | DietPlan/InventoryLog/StockAllocation | 완료(검증 경로) | `meals/release_patch_views.py:deduct_inventory_view`; T2 부족 차단·T3 35.1kg 차감·idempotent 회귀. 실제 배식 인원 오차를 자동 측정하는 기능은 아님 |
| F15 FIFO·유통기한 | 신규 입고 lot 생성, 거래일 순 출고 배정, 만료 lot의 사용 차단·폐기 허용 | 있음(잔량 표) | 있음 | StockLot/StockAllocation | 부분 구현(기존 데이터 포함) | `inventory/lot_services.py`, `templates/workflow/ledger.html`; T2 FIFO/expiry 단언. lot가 없는 과거 재고에는 배정 이력을 만들지 않고 원장 차감만 허용 |
| F16 주간 수불 조회 | 기간 전 원장=기초, 기간 중 입고−사용−폐기+조정=기말, 서울 업무일 기준 | 있음 | 있음 | 원장 조회 | 완료(조회 계산) | `workflow_views.py:ledger`, `templates/workflow/ledger.html`; T2 weekly_ledger의 UTC/서울 경계값, T3 4.9kg 결과 |
| F17 발주예정서·발주일 묶음 | 월~목 석식+다음 조중식, 금요일은 주말·월요일 조중식 포함, 계획 스냅샷 저장 | 있음 | 있음 | ProcurementPlan/Line | 완료(기본 생성) | `workflow.py:build_preview/create_plan`, `templates/workflow/preview.html/plan.html`; T2 금요일/주말·확정 누락·중복 저장, T3 |
| F18 포장규격 환산·수량 조정 | 등록된 업체별 내용량/단위/발주 간격으로 올림. 최소 이상·간격에 맞는 조정 후 확정 | 있음 | 있음 | SupplySpecification/PlanLine | 완료(명시 규격) | `workflow.py:convert/confirm_orders`, `SpecificationForm`; T2 5kg·700g·소수kg 테스트, T3 35.1kg→8캔→9캔. 문자열에서 개당 중량을 추정하지 않음 |
| F19 공산품 개수→질량 자동 계산 | ‘1인당3개’와 개당70g·포장10개 등을 별도 구조로 연결 | 별도 없음 | 일반 질량 계산만 | 개별 중량 전용 필드 없음 | 부분 구현 | SupplySpecification은 포장 총량·기준 단위 중심. 1인량 g과 포장 총중량은 지원하지만 개별 중량/대상별 배식량 자동 해석은 없음 |
| F20 업체별 구매발주서 | 발주일·공급업체별 주문 분리, 가격·규격·수량 스냅샷과 발행 정보 저장 | 있음 | 있음 | PurchaseOrder/OrderItem | 완료(내부 발행) | `workflow.py:confirm_orders`, `templates/workflow/plan.html`, `procurement/views.py:vendor_procurement_report`; T2 two_suppliers_split_orders, T3. 업체에 이메일/전자발주 전송하는 기능은 아님 |
| F21 변경 감지·발주 재검토 | 식단/식수/레시피/규격이 바뀌면 계획을 재검토로 표시하고 검수 제한 | 있음 | 있음 | fingerprint/needs_review | 부분 구현 | `procurement/signals.py`, `workflow.py:invalidate_plans/inspect_item`; T2 changed_headcount_recipe_or_spec. 취소·대체 관계의 완결 UI는 후속 |
| F22 검수·합격량 입고·중복 방지 | 실제 납품/합격량/품질/사유/기한 기록, 합격량만 입고, 같은 재전송은 재입고하지 않음 | 있음 | 있음 | GoodsInspection/InventoryLog | 완료(품목당1회) | `workflow.py:inspect_item`, `workflow_views.py:inspection`; T2 partial_acceptance/duplicate/conflicting_reinspection, T3 45kg 중40kg 합격 |
| F23 분할 납품·확정 검수 정정 | 여러 차례 납품/반품·재입고/정정 전표 | 독립 흐름 없음 | 1품목1검수로 제한 | OneToOne | 미구현(다회 업무) | GoodsInspection.order_item OneToOne 및 inspect_item의 상충 수정 거부. F22의 부분 합격을 분할 납품 완성으로 표현하면 안 됨 |
| F24 업체·납품규격 관리 | 관리자 업체 생성/수정 및 품목별 업체·포장규격 관리 | 있음 | 있음 | User/SupplySpecification | 완료(기준정보 UI) | `workflow_views.py:suppliers/specifications`, `templates/workflow/master.html`; T2 supplier_and_spec_edit_from_ui. 독립 공급업체 포털은 아님 |
| F25 조리지시서 | 날짜·끼니별 확정 식수→총량·포장 사용량, 재료별/문서별 지시 저장, Excel/인쇄, revision 충돌 거부 | 있음 | 있음 | CookingInstruction＋식단/레시피 | 부분 구현(원양식 전체 요구) | 미커밋 `meals/cooking.py/cooking_views.py/cooking_export.py`, `templates/workflow/cooking_*.html`; T1/T4. 입고일 묶음·메뉴별 대상집단 식수·실프린터 인수는 남음 |
| F26 월말 정산 참고자료 | 업체별 발주액·합격 수량 비례 금액·미검수 경고·수불 연결 | 있음 | 있음 | 주문/검수/원장 조회 | 부분 구현 | `workflow_views.py:settlement`, `templates/workflow/settlement.html`; T2 inspection_ui_and_actual_monthly_settlement. 세금/운송비/실제 소비원가·회계 확정 기능과 다름 |
| F27 로그인·세션·업무 권한 | Django 로그인/로그아웃/가입, 내부 업무 인증, 일반 공급업체 차단, 관리자 기준정보 제한 | 있음 | 있음 | User/session | 부분 구현(인증 체계 전체) | `accounts/views.py`, `config/business_access.py`, `workflow_views.py:_can_manage`; T2 및 조리지시서 권한 테스트. 공개 가입·기본 영양사 역할, staff 예외, 일부 csrf_exempt API가 남아 ‘완전한 보안’ 주장 불가 |
| F28 대시보드 | 부족 재고 총수·일부 목록, 발주 진입 및 현황 표시 | 있음 | 있음 | ORM 집계 | 완료(검증된 집계) | `config/views.py:home`, `templates/home.html`; T2 dashboard_total_is_not_capped_at_eight. 상위8개 목록과 전체 부족 수를 분리 |
| F29 업체현황 전용 출력 | 업체 관리 화면과 별개 업체현황 문서 | 전용 없음 | 전용 없음 | 업체 정보는 존재 | 미구현 | 문서 index·URL·View에서 독립 출력 경로를 찾지 못함. `doc_inventory_status`는 재고 수불 문서이므로 대체 아님 |
| F30 영양소·칼로리/실시간 외부API/완전자동발주 | 영양 분석, 실시간 기상 API, 공급업체 자동 통보 등 | 요구별 전용 흐름 없음 | 일부 연구/로더만 | 전용 영양 모델 없음 | 미구현 또는 확인 불가 | 현재 웹 업무 코드에서 완결 경로 없음. 자료 문구·설치 라이브러리만으로 기능 존재를 주장하지 않음 |

## 문서·보고서 출력 범위

| 문서 | 실제 접근 경로 | 데이터·출력 방식 | 상태·주의 |
|---|---|---|---|
| 주간/월간 식단표 | `/meals/document/weekly/`, `/meals/document/monthly/` | 식단 DB→HTML 인쇄, 주간 Excel 별도 | 기본 출력 구현. 전체 printer 인수는 없음 |
| 주간 레시피 명세서 | `/meals/document/weekly-recipe/` | 메뉴/재료×GET 공통 인원수(기본100) | 구현. 식사별 확정 식수를 자동 사용하는 전용 조리지시서와 다름 |
| 발주예정서 | `/procurement/workflow/preview/`→`plans/<id>/` | 확정 식수·레시피·규격 계획 저장, HTML·빈칸 출력 모드 | 구현. `/meals/document/menu-overview/`는 기존 참고 양식 |
| 업체별 구매발주서 | `/procurement/vendor-report/`, `vendor-report/excel/` | 업체별 주문 HTML·XLSX | 구현. Excel 시트명이 아직 `발주명세서_...`여서 명칭 완전 통일은 아님 |
| 급식물품 검수일지 | `/procurement/docs/inspection-log/`, `/procurement/workflow/inspections/` | 주문·검수별 실업체명 정렬 HTML 인쇄 | 구현. 기존 `/daily-report/excel/`은 별도 ‘검수서(주문)’ 양식 |
| 급식물품구입요구서 | `/procurement/docs/purchase-requisition/` | 발주 자료 품목 집계·분류 regroup HTML | 부분 구현. 독립 초안·승인 및 빈 대상 확정 정책은 후속 |
| 재고 주/월 수불·재고현황 | `/inventory/reports/weekly/`, `monthly/`, `export/excel/`, `docs/inventory-status/` | 원장·재고 집계 HTML/Excel | 구현. 공통 신규 주간 조회는 `/procurement/workflow/ledger/` |
| 주간 예측 보고서 | `/forecasting/weekly-forecast-report/`, `export-weekly-forecast-excel/` | 예측 결과/일정 표시 HTML·XLSX | 출력 경로 구현. 예측 정확도 평가 보고서가 아님 |
| 조리지시서 | `/meals/cooking/?date=YYYY-MM-DD`, `/meals/cooking/<id>/?format=xlsx` | 실제6열 양식 기반＋별도 계산근거 시트, 날짜별끼니 XLSX, 브라우저 인쇄 | T4. PDF는 브라우저가 만든 산출물이며 서버 PDF 생성 API가 아님 |

## 발표에 사용할 수 있는 검증된 계산 예

T3의 테스트 데이터에서 351명×100g=35.1kg, 5kg/캔 명시 규격으로 최소8캔, 사용자9캔 조정 후 발행했다. 45kg 납품 중40kg만 검수 합격·입고하고35.1kg 사용 후4.9kg이 남았다. T4의 조리지시서 사용량 환산은7.02캔이며 발주 올림8캔과 의미가 다르다. 실제 사업장의 절감 실적이나 예측 성능 수치가 아니다.

## 최종판정에 필요한 남은 확인

새 기능을 운영에 적용했다는 증거, 실제 영양사 인수 서명, 모델의 시간 분리 평가·정확도, 기존 재고 lot 대사, 실제 프린터 다페이지 검증은 부족하다. 따라서 ‘모든 요구사항 완성’보다 **검증된 핵심 거래 흐름과 명확하게 남긴 미완성 범위**를 성과로 설명하는 것이 근거에 맞다.
