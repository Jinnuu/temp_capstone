# 기능 검증 결과

## 요약과 집계

- 기준 코드: `e21478b` 통합 완료 상태. 코드 변경 전 분석 커밋: `ab5ed57`.
- 참조: D01~D05 Markdown 5개. 원본 파일 SHA-256 및 내장 그림 두 개 확인. PDF/DOCX/HWPX 원본은 제공되지 않았다.
- 추적 항목: **196행** (UC 15, US 30, O 6, TK 140, 추가 요구 5). 상하위/중복 태스크를 포함한 추적 수이며 독립 기능 수로 부풀리지 않는다.

| 상태 | 최초 | 구현 후 |
|---|---:|---:|
| COMPLETE | 0 | 78 |
| PARTIAL | 123 | 64 |
| MISSING | 18 | 1 |
| BROKEN | 1 | 0 |
| UNVERIFIED | 54 | 53 |
| 합계 | 196 | 196 |

최초 COMPLETE 0은 기존에 기능이 없었다는 뜻이 아니다. 기존 48개 회귀 테스트는 통과했지만 최신 문서의 전체 수용 기준과 예외까지 완료됐다는 증거는 없었다. 각 행의 초기/현재 상태·출처·코드·수용 기준은 추적표와 requirement_catalog.json에 보존했다.

필수 UC 15개는 현재 **9 COMPLETE / 6 PARTIAL**이다. PARTIAL은 UC-001, UC-002, UC-004, UC-009, UC-011, UC-013이며 상세 한계는 REMAINING_ISSUES.md에 기록했다.

## 실제 구현 내용

1. **식수 확정**: 날짜·끼니별 수동 예상과 AI 참고, 최종 식수·확정시점을 분리한다. 0명 허용, 음수/비정수/NaN 차단. AI가 없어도 직접 확정한다. 변경 시 관련 발주에 재검토 표시.
2. **레시피/기준정보**: 1인분 단위·조리 정보 저장, g/kg 등 명시 변환. 기존 파일/API 업로드 보존. 레시피 업로드가 식재료의 재고 기준 단위를 바꾸지 않도록 수정. 일간 편집에서 기존 식단 ID·예측 참조 보존, 빈 메뉴 선택 반영.
3. **발주예정서/업체별 구매발주서**: 최종 식수×레시피, 동일 재료 합산, 재고와 안전재고, 금요일·주말 묶음, 포장 내용량·발주 간격 올림, 수량 조정·저장, 규격/업체 누락 차단, 변경 감지 스냅샷 및 요청 키 중복 방지.
4. **검수/재고**: 실제 납품/합격량·규격·상태·사유·유통기한을 저장하고 합격량만 입고한다. 검수 전 완료 버튼의 자동입고를 제거하고 검수 화면으로 안내한다. 검수 중복·상충 수정 및 부족 출고를 차단.
5. **수불/FIFO**: kg 선입고·사용·조정, 주간 수불, 신규 lot·유통기한·FIFO 배정. 기존 lot 미배정 이력은 추정하지 않는다.
6. **관리·문서**: 관리자 업체/납품규격/카테고리 및 오분류 정정 UI, 월별 업체 발주/실검수 금액과 수불 연결. 문서명·업체명 정렬·카테고리 중복 보정. 발주예정서 비고 저장·빈 입력란 출력 모드.
7. **인증**: 내부 업무는 인증된 사용자만 접근하며 공급업체 역할의 직접 업무 조작을 제한한다. 기준정보 변경은 staff/ADMIN에 한정한다.

신규 화면은 상단 **영양사 업무 흐름**에서 연결된다. 기존 간편 발주/식단 발주 저장도 공통 발주예정서 검토 단계로 이어진다. 주문을 최종 발행하기 전에 포장규격과 수량을 검토하는 단계가 추가된 것은 최신 문서 수용 기준을 적용한 의도적 동작 변경이다.

## 환경 및 실행 증거

- 기존 `capstone-web:sprint7` 이미지, Python 3.12.13 및 기존 AI 패키지 버전 유지. requirements와 모델 파일은 이번 작업에서 변경하지 않았다.
- 단위/회귀 테스트 앱은 `--network none --read-only --tmpfs /tmp`이며 통합 디렉터리만 읽기 전용 마운트했다.
- SQLite 및 별도 `mariadb:10.6`의 tmpfs 데이터 디렉터리/새 Unix socket을 사용했다. 기존 DB·볼륨·네트워크에 연결하지 않았다.
- 브라우저 앱은 별도로 만든 내부 테스트 네트워크에서 폐기용 SQLite를 사용했다. 외부 CDN을 차단하고 로컬 CSS로 화면을 검증했다. 호스트에서 이 테스트 앱의 전용 내부 주소로만 접근했다.
- Playwright는 `/tmp/snp-browser`에만 설치했으며 애플리케이션 requirements를 수정하지 않았다.

| 검증 | 결과 | 증거 |
|---|---|---|
| 기준 코드 회귀 테스트 | 48개 통과 | `verification/requirements/baseline.log` |
| Django check | 두 DB 설정 모두 통과 | `sqlite.log`, `mariadb.log` |
| makemigrations --check --dry-run | 두 DB 모두 변경 없음 | 같은 로그 |
| migrate / migrate --check / graph | 두 DB 모두 통과 | 같은 로그 |
| 전체 Django 테스트 | **SQLite 101개 / MariaDB 101개 통과** | 같은 로그 |
| 이전 스키마 데이터 업그레이드 | 사용자·재료·수불·발주·품목·날짜·금액 보존 | `test_migrations.py`, 같은 로그 |
| JavaScript 재고 계산 | **4개 통과** | `javascript.log` |
| 실제 3개 저장 모델 로드·predict | 통과 | `test_ai.py`, 같은 로그 |
| 실제 전처리→모델→예측 저장 | 오프라인 fallback 경로 통과 | 같은 로그 |
| 실제 Chromium UI 전체 업무 | 통과, page error 0 | `browser.log`, `browser.json` |
| 화면 캡처·PDF 생성 | 단일 업무 사례 성공 | `browser-ledger.png`, `order-preview.pdf` |
| 원본/참조/모델/기존 컨테이너 보존 | 해시·시작시각·재시작 횟수 일치 | `preservation.json` |

기존 테스트는 삭제하지 않았다. 인증 보호에 맞게 정상 사용자 세션을 추가했고, 완료 버튼 자동입고/AI 직접 채택 가정은 최신 문서의 확정·검수 기준으로 바꿨다. 별도 신규 테스트에서 미인증 접근·검수 전 입고 금지·기존 발주 진입 경로도 검증한다. 총 테스트 수는 기준 48개에서 101개로 늘었다.

## 실제 브라우저 시나리오

1. 영양사 로그인, 상단 업무 흐름 진입.
2. 2026-10-16 석식 직접 351명·최종 351명 확정.
3. 1인분 100g → 총 35.1kg, 5kg/캔 → 8캔으로 올림.
4. 9캔으로 수량 조정하고 업체별 구매발주서 4,500원 발행.
5. 45kg 납품 중 40kg 합격, 5kg 품질 이상 사유 기록.
6. 합격 40kg만 입고, 식사 완료 후 35.1kg 차감.
7. 수불/lot 잔량 4.9kg 확인, 문서 PDF 생성.

정상 경로는 실제 HTML 폼과 CSRF 토큰, 클릭 및 화면 이동으로 수행했다. 테스트 데이터는 실제 DB에서 가져오거나 수정하지 않았다. 실제 프린터와 다량 데이터 페이지 나눔 검증은 수행하지 않았다.

## 경계값 및 실패 처리

0명, 음수/비정수/NaN/무한 식수, AI 실패, 미확정, 레시피 누락, g/kg/EA 불일치, 재고 0/부족/충분, 동일 재료 중복, 공급업체/포장규격 누락, 35kg/5kg 및 700g 포장, 소수 kg 발주 간격, 금요일/주말, 수량 조정 과소/비정상, 재요청·상충 검수, 합격량 초과·유통기한, 재고 부족, FIFO·폐기, 기존 업로드/URL/문서·Excel을 테스트했다.

AI 실패 테스트는 의도적으로 RuntimeError를 주입한다. 이때 기존 예측 View가 출력한 traceback은 예상된 실패 처리 증거이며 전체 테스트 실패가 아니다. 최종 로그의 `Ran 101 tests / OK`와 구분한다.

## 미검증 및 후속 범위

- 정상 SBERT/임베딩+KMeans 경로, OOF/Holdout 정확도/데이터 누수·현업 예측 비교.
- 기존 재고 lot 대사, 운영 데이터/계정 역할/스키마 검증.
- 조리지시서 별도 소스 확보·통합, 분할 납품/검수 정정·취소/대체발주·회계 확정 정책.
- 월간 전용 작성, 독립 구입요구서 초안, 칼로리·영양소 원천 데이터.
- 동시 부하·장애 복구·모든 레거시 입력 조합·실제 프린터·현장 인수.

이 항목은 자동화 테스트 통과에 포함시켜 완료 처리하지 않았다. 배포 전 조치는 REMAINING_ISSUES.md를 따른다.

## 재현

```bash
cd /home/woohyeak/sprint7-integration
python3 scripts/prepare_integration_wheels.py
bash scripts/verify_integration.sh
node --test integration_tests/smart_order.test.cjs
```

MariaDB는 MERGE_REPORT.md의 전용 tmpfs 테스트 컨테이너 명령으로 새로 준비하고 `bash scripts/verify_integration.sh config.test_mysql_settings`를 실행한다. 브라우저 테스트는 `integration_tests/seed_browser.py`를 **폐기용 config.test_settings DB에서만** 실행한 전용 서버, 별도 Playwright/Chromium이 필요하다. `SNP_BROWSER_BASE`, `SNP_PLAYWRIGHT_MODULE`, `SNP_CHROMIUM`으로 테스트 위치를 지정한다. 기존 서비스 주소를 테스트 대상으로 지정하지 않는다.

## 신규 마이그레이션 (8개)

```text
inventory/migrations/0008_ingredientcategory_supplyspecification.py
inventory/migrations/0009_alter_inventorylog_quantity.py
inventory/migrations/0010_stocklot_stockallocation.py
inventory/migrations/0011_supplyspecification_order_increment.py
meals/migrations/0004_dietplan_final_headcount_and_more.py
procurement/migrations/0006_orderitem_order_unit_orderitem_package_quantity_and_more.py
procurement/migrations/0007_alter_goodsinspection_accepted_qty_and_more.py
procurement/migrations/0008_procurementplanline_order_increment_and_more.py
```

기존 이력 파일은 수정하지 않았다. nullable 확정값·새 테이블·소수 정밀도 확대·발주 간격 추가이며, 과거 최종 식수/포장계수/lot를 추정해 채우는 데이터 마이그레이션은 없다.

## 수정·추가 파일 목록

```text
.gitignore
MERGE_REPORT.md
config/business_access.py
config/settings.py
docs/analysis/FUNCTIONAL_TEST_REPORT.md
docs/analysis/IMPLEMENTATION_PLAN.md
docs/analysis/REMAINING_ISSUES.md
docs/analysis/REQUIREMENT_TRACEABILITY_MATRIX.md
docs/analysis/requirement_catalog.json
forecasting/services/ingredient_calc.py
integration_tests/browser_workflow.cjs
integration_tests/seed_browser.py
integration_tests/test_requirements.py
integration_tests/test_workflows.py
inventory/forms.py
inventory/lot_services.py
inventory/migrations/0008_ingredientcategory_supplyspecification.py
inventory/migrations/0009_alter_inventorylog_quantity.py
inventory/migrations/0010_stocklot_stockallocation.py
inventory/migrations/0011_supplyspecification_order_increment.py
inventory/models.py
inventory/views.py
meals/migrations/0004_dietplan_final_headcount_and_more.py
meals/models.py
meals/recipe_file_views.py
meals/release_patch_views.py
meals/tests.py
meals/views.py
meals/views_extra.py
meals/views_new_docs.py
procurement/apps.py
procurement/migrations/0006_orderitem_order_unit_orderitem_package_quantity_and_more.py
procurement/migrations/0007_alter_goodsinspection_accepted_qty_and_more.py
procurement/migrations/0008_procurementplanline_order_increment_and_more.py
procurement/models.py
procurement/signals.py
procurement/tests.py
procurement/urls.py
procurement/views.py
procurement/views_new_docs.py
procurement/workflow.py
procurement/workflow_forms.py
procurement/workflow_views.py
static/css/workflow.css
templates/docs/doc_menu_overview.html
templates/docs/doc_purchase_requisition.html
templates/docs/index.html
templates/docs/vendor_procurement_report.html
templates/inventory/inventory_log_form.html
templates/meals/menu_list.html
templates/partials/top_nav.html
templates/procurement/order_create.html
templates/procurement/order_from_mealplan.html
templates/workflow/base.html
templates/workflow/form.html
templates/workflow/hub.html
templates/workflow/inspections.html
templates/workflow/ledger.html
templates/workflow/master.html
templates/workflow/plan.html
templates/workflow/preview.html
templates/workflow/recipes.html
templates/workflow/settlement.html
verification/requirements/baseline.log
verification/requirements/browser-ledger.png
verification/requirements/browser.json
verification/requirements/browser.log
verification/requirements/javascript.log
verification/requirements/mariadb.log
verification/requirements/order-preview.pdf
verification/requirements/preservation.json
verification/requirements/sqlite.log
```

검증 종료 후 `snp-requirements-browser-app`, `snp-requirements-db`, `snp-requirements-test`를 정리했다. 기존 서비스에는 정리 명령을 실행하지 않았다.
