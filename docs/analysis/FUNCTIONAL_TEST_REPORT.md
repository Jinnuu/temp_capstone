# 기능 검증 결과

> 이전 재검증: SQLite/MariaDB 전체 각각 113개 통과. 아래 마지막 「실제 테스트 실패 수정 및 격리 재검증」 절이 현재 결과이며 이전 미실행 기록은 이력이다.

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

## 2026-10-16 후속 변경본 — 이전 통과 결과와 구분

위 101개씩의 통과는 a8d9fae 기존 코드의 증거다. **이번 수정본 전체 회귀가 통과했다는 뜻이 아니다.** 이번에는 전용 조리지시서 코드와 신규 테스트 12개를 추가했다. TK-09-004는 MISSING에서 UNVERIFIED로 변경했으며 현재 196행 집계는 COMPLETE 78 / PARTIAL 64 / MISSING 0 / BROKEN 0 / UNVERIFIED 54다. 누락 0은 전 기능 완료라는 뜻이 아니다.

- 직접 실행 `node integration_tests/smart_order.test.cjs`: 4개 통과.
- Python 6파일 AST 문법 검사와 git diff --check 통과.
- `bash scripts/verify_integration.sh`: Docker socket 접근 거부로 실패. check/makemigrations/migrate/전체 Django/신규 조리지시서 테스트 실행 못함.
- 브라우저·신규 Excel 출력·AI·MariaDB 재검증 못함. 이전 AI 파일/패키지는 수정하지 않았다.
- 상세: DIETITIAN_FEEDBACK_VERIFICATION.md, verification/feedback/ 로그.

추가 migration: `meals/migrations/0005_cookinginstruction.py` (기존 8개와 별도, 신규 테이블). 실제/테스트 DB 어디에도 이번 migration을 적용하지 않았다.

이번 수정·추가 파일: meals/models.py, meals/urls.py, meals/cooking.py, meals/cooking_views.py, meals/migrations/0005_cookinginstruction.py, templates/workflow/cooking_index.html, templates/workflow/cooking_detail.html, templates/workflow/hub.html, integration_tests/test_cooking.py, docs/analysis/DIETITIAN_FEEDBACK_VERIFICATION.md, docs/analysis/REQUIREMENT_TRACEABILITY_MATRIX.md, docs/analysis/requirement_catalog.json, docs/analysis/IMPLEMENTATION_PLAN.md, docs/analysis/FUNCTIONAL_TEST_REPORT.md, docs/analysis/REMAINING_ISSUES.md, MERGE_REPORT.md, verification/feedback/*。


## 2026-10-16 개발 환경 정비 및 검증 재개 결과

### 인터프리터·의존성 조사

실제 사용한 실행 파일은 `/home/woohyeak/miniconda3/envs/meal_pycaret/bin/python`이며 Python 3.11.15다. 새 Conda/venv를 만들지 않았다. requirements.txt 및 Dockerfile(python:3.12)을 확인했고 pyproject.toml은 없다. 운영 핀 Django 6.0.3은 Python 3.11에 설치할 수 없다. 로컬 개발 후보는 Django 5.2 계열이며 6.0과 동일 환경이라고 간주하지 않는다. Python 3.11에서 원본 requirements 전체를 설치하는 방식은 사용하지 않았다.

주요 버전 비교:

| 패키지 | 현재 Conda | 프로젝트 핀 |
|---|---:|---:|
| Django | 없음 | 6.0.3 |
| numpy | 1.26.4 | 2.4.3 |
| pandas | 2.1.4 | 3.0.1 |
| scikit-learn | 1.4.2 | 1.7.2 |
| scipy | 1.11.4 | 1.17.1 |
| joblib | 1.3.2 | 1.5.3 |
| openpyxl | 3.1.5 | 3.1.5 |

설치 전후 `pip freeze`를 verification/environment/pip-before.txt 및 pip-after.txt에 저장했으며 **내용 동일**하다. 전후 `pip check`는 모두 No broken requirements found. **이번에 설치·제거·업그레이드한 패키지는 없다.** requirements/pyproject/Dockerfile 및 다른 Python 환경을 변경하지 않았다.

현재 세션에서 쓸 수 있는 위치는 통합 디렉터리와 /tmp뿐이므로, 사용자 설치 허용과 별개로 Conda 환경 디렉터리에 쓰는 작업은 실행할 수 없다. 승인 정책도 never이므로 권한 상승 요청 수단이 없다. /tmp에 호환 의존성만 확보하는 대체를 시도했지만 `pip download 'Django>=5.2,<5.3' django-environ==0.13.0 xlrd==2.0.2 xlwt==1.3.0`은 no matching distribution으로 실패했다. 다운로드 실패의 세부 원인을 사용자 시스템 전체의 네트워크/권한 문제로 단정하지 않는다.

### Docker 접근

Codex 프로세스의 `docker ps`와 기존 검증 스크립트는 소켓 접근 permission denied로 실패했다. 샌드박스의 소켓 표시 소유권은 nobody:nogroup이며, 이 관찰을 호스트 사용자 계정의 Docker 권한 문제로 해석하지 않는다. sudo, 그룹 변경, 소켓 chmod/chown 및 기존 컨테이너 변경은 하지 않았다. 현재 approval=never이므로 승인 요청도 수행할 수 없다.

### 이번 실제 실행 결과

| 항목 | 결과 | 증거 |
|---|---|---|
| 지정 Conda Python / pip freeze / pip check | 실행, 전후 패키지 동일, 의존성 검사 통과 | verification/environment/pip-*.txt |
| 조리지시서 12개 Django 테스트 | 시작 실패: ModuleNotFoundError django, 실행된 테스트 0 | cooking-tests-attempt.log |
| Django check | 시작 실패: Django 없음 | check-attempt.log |
| SQLite 기존 전체 검증 스크립트 | 시작 실패: Docker socket 접근 거부 | docker-sqlite-attempt.log |
| 격리 MariaDB 전체 검증 스크립트 | 시작 실패: Docker socket 접근 거부 | docker-mariadb-attempt.log |
| meals/0005 적용·migration check | 미실행 | 위 제약으로 DB 생성/접근 안 함 |
| 생성·수정·저장/재계산/포장환산/상충 저장/재고 비차감 Django 테스트 | 미실행, 통과 판정 안 함 | 신규 12개 테스트 코드는 보존 |
| 브라우저·인쇄·조리지시서 Excel 생성 | 미실행 | 실행 서버를 준비하지 못함 |
| 저장 AI 모델 로드 및 0 특성 1행 추론 | 3개 모두 유한값 반환, 버전 경고 발생 | model-compatibility.log |

AI smoke는 Django 없이 원래 model_loader와 같은 sklearn `_loss` 별칭을 설정한 뒤 저장된 3개 artifact를 joblib.load하고, 저장 feature_columns로 구성한 0 입력을 predict했다. 결과는 조식 48.5097, 중식 174.1057, 석식 136.8276. sklearn 1.7.2 저장 모델을 1.4.2에서 읽는 버전 경고가 각각 16/120/285개 발생했다. 이는 모델 로드·단일 입력 실행만 입증하며 정상 전처리/DB 저장/동일 정확도/운영 호환성의 완료 판정이 아니다. 경고를 해결하려고 PyCaret 환경의 sklearn을 올리지 않았다. AI 파일을 덮어쓰지 않았다.

### 양식·잔여·Git

요청한 `(8.7~8.9)조리지시서.xlsx`는 아직 docs/reference에 없다. 모든 시트·셀 분석 및 실제 양식 일치 검증은 보류한다. 기존 미구현 사항(업체현황 전용 출력, 개별 중량 개수→질량 환산, 분할 납품/정정, 재고 lot 대사, 정상 SBERT 검증 등)과 조리지시서 UNVERIFIED 판정을 유지한다.

이번 추가 변경은 두 보고서 및 verification/environment/ 증거 파일이다. 기존 코드·신규 migration·12개 테스트·AGENTS.md의 미커밋 상태를 그대로 보존했으며 커밋/reset/stash/push/PR/배포는 하지 않았다. 통합 브랜치는 integration/sprint7-kanghoon이다. 원본 ~/sprint7과 기존 서비스·DB·볼륨은 변경하지 않았다.

검증 재개에는 Conda 환경 쓰기를 허용하는 세션 설정과 패키지 확보 경로, 승인 가능한 Docker 접근 방식이 필요하다. 이 조건이 충족되면 호환 Django 설치 후 신규/전체 SQLite 테스트, 새 MariaDB의 migration·전체 회귀, 브라우저/Excel 순서로 재검증한다. Python 3.11/Django 5.2 실행은 기존 Python 3.12/Django 6 Docker 환경 검증을 대체하지 않는다.


## 2026-10-16 실제 테스트 실패 수정 및 격리 재검증

이 절이 현재 변경본의 최신 실행 결과다. 이전의 Docker 접근 불가·테스트 미실행 기록은 당시 이력으로 보존한다. 이번에는 승인된 명령 실행으로 샌드박스 밖 Docker 접근을 사용했으며 소켓 권한·계정 그룹은 변경하지 않았다.

### 원인 및 수정

1. 조리지시서 12 ERROR: Ingredient.safe_stock_level은 default 없는 NOT NULL Decimal 필드다. test_cooking.py의 공통 픽스처에서만 safe_stock_level=0을 명시했다. 모델·NOT NULL 제약·기존 migration은 변경하지 않았다.
2. 주간 수불 FAIL: USE_TZ=True, TIME_ZONE=Asia/Seoul에서 거래일자는 UTC로 저장되고 `transaction_date__date`는 활성 시간대로 변환해 조회한다. 기존 테스트는 UTC `timezone.now().date()`를 기간 끝으로 사용했다. UTC 10/15 16:00은 서울 10/16 01:00이므로 서울 거래일 10/16의 입고·폐기가 10/15까지의 조회에서 제외되는 것이 올바르다. record_inventory는 전달받은 거래일자·입출고 유형을 그대로 기록하며 lot는 별도 배정이고 수불 집계는 lot 테이블을 join하지 않는다. 따라서 production 집계 로직과 기대값(기초10/입고2/폐기1/기말11)을 유지했다. 고정 UTC 시각으로 서울 업무일 조회(10,2,1,11), 서울 전일 제외(10,0,0,10), UTC 해당일 포함(10,2,1,11)을 같은 테스트에서 검증한다.
3. 접근 제어: config/business_access.py는 AuthenticationMiddleware 뒤에서 업무 경로를 보호한다. 익명은 로그인 이동, 공급업체 비직원 계정은 403이다. 기존 정책의 staff 예외는 유지한다. 신규 테스트를 목록·상세·Excel GET 및 지시사항 POST로 확장했고, 차단 요청 후 문서/원장 생성이 없는지도 확인했다. View를 별도 인증 정책으로 중복 구현하지 않았다.
4. 검증 스크립트: SPRINT7_DB_SOCKET_DIR 옵션을 추가해 매번 새로운 MariaDB 소켓 디렉터리를 지정할 수 있게 했다. 기본 동작과 허용 settings 제한은 유지한다.

### 실제 실행 결과

| 검증 | SQLite | 격리 MariaDB 10.6 |
|---|---|---|
| Django check | 통과 | 통과 |
| makemigrations --check --dry-run | 변경 없음 | 변경 없음 |
| migrate / migrate --check | 통과 | 통과 |
| meals/0005_cookinginstruction | 적용 성공 | 적용 성공 |
| 전체 Django | **113/113 통과**, 5.390초 | **113/113 통과**, 6.773초 |
| 조리지시서 | 전체에 포함된 **12/12 통과** | 전체에 포함된 **12/12 통과** |
| 주간 수불 날짜 경계값 | 통과 | 통과 |
| 스크립트 최종 종료 코드 | 0 | 0 |

조리지시서 12개는 확정 식수·0명·미확정, 규격 환산·누락·단위 불일치, 저장·수정·오래된 revision 충돌, URL/Template HTTP 렌더링, 실제 생성 Excel의 openpyxl 재열기·숫자 확인·수식 문자열 셀 확인, 재고 비차감, 익명/공급업체 접근 차단을 검증한다. 추가 기능 오류는 이번 12개 실행에서 발견되지 않았다. 순차 stale revision 거부를 실제 동시 부하 시험으로 과장하지 않는다.

증거: verification/feedback/sqlite-recheck.log 및 mariadb-recheck.log. SQLite 최초 실행도 113개가 통과했지만 실행 중 스크립트 수정으로 테스트 후 shell EOF 오류가 발생했다. 변경 완료 후 전체를 다시 실행한 위 로그/종료 코드만 최종 결과로 사용한다.

### 환경·보존·남은 검증

capstone-web:sprint7 이미지의 기존 Python 3.12/Django 6.0.3을 사용했다. 컨테이너는 --network none --read-only --tmpfs /tmp이며 소스/테스트 wheels는 읽기 전용이다. xlrd/xlwt는 컨테이너 /tmp에만 설치했다. Conda/시스템 Python이나 requirements는 변경하지 않았다.

MariaDB는 새 snp-cooking-db-20261016 컨테이너, tmpfs /var/lib/mysql, 신규 /tmp/snp-cooking-db.LtwUVg 소켓, --network none을 사용했고 호스트 포트·기존 DB·네트워크·named volume을 사용하지 않았다. 검증 후 이번 DB 컨테이너만 docker rm -f로 정리했다. 앱 컨테이너는 --rm으로 제거됐다.

예시 Excel 파일은 여전히 없어 실제 영양사 양식 일치는 미검증이다. 이번에는 Playwright·실제 브라우저 인쇄/PDF·동시 요청 부하를 재실행하지 않았다. SBERT는 오프라인 fallback이며 정상 임베딩 경로 완료를 의미하지 않는다. 조리지시서 핵심 HTTP/업무 테스트는 통과했지만 전체 요구 상태는 양식·현장 인수가 남은 PARTIAL로 기록한다.

이번 수정 파일: integration_tests/test_cooking.py(기존 미커밋 파일 보존 후 픽스처/보안 검증 보완), integration_tests/test_requirements.py, scripts/verify_integration.sh. 관련 문서·추적표·catalog와 검증 로그도 갱신했다. 새 migration/업무 모델 변경은 없다. 원본 ~/sprint7, 기존 8000/8007 서비스·DB·볼륨은 변경하지 않았고 push/PR/배포/커밋은 수행하지 않았다.

### 일반 터미널 재현

SQLite 전체 113개: `cd /home/woohyeak/sprint7-integration` 후 `bash scripts/verify_integration.sh`.

MariaDB는 새 전용 컨테이너를 생성한 뒤 실행한다(기존 DB 소켓 지정 금지):

```bash
socket_dir=$(mktemp -d /tmp/snp-cooking-recheck.XXXXXX)
container_name="snp-cooking-$(basename "$socket_dir")"
docker run -d --name "$container_name" --network none \
  --tmpfs /var/lib/mysql:rw,size=512m \
  -v "$socket_dir:/run/mysqld" \
  -e MARIADB_ROOT_PASSWORD=isolated-test-password \
  -e MARIADB_DATABASE=sprint7_integration mariadb:10.6
# docker logs "$container_name"에서 최종 ready for connections 확인 후:
SPRINT7_DB_SOCKET_DIR="$socket_dir" bash scripts/verify_integration.sh config.test_mysql_settings
# 이번에 만든 컨테이너만 정리:
docker rm -f "$container_name"
```


## 실제 Excel 반영 최종 검증 (2026-10-16)

실제 참고6시트 분석 및 웹/출력 양식 개선 후 SQLite117/117(8.562초), MariaDB117/117(9.854초), 양쪽 스크립트 종료0. 조리지시서 기존12+신규4=16개이며 원본 구조 비교·날짜별 다운로드·재료별 비고·긴 비고 페이지 분할 검증을 포함한다. Django check 및 migration0006 적용·검사 통과. Chromium 조회/수정/저장/다운로드/인쇄 버튼/CSS·A4 PDF/식수 재계산 모두 통과, page errors0. 로그는 verification/cooking-format/에 있다. 실제 원본 파일은 이번에 제공되어 해시 보존 및 전체 분석 완료했으며 이전 미제공 기록을 대체한다.

신규 migration: meals/0006_cookinginstruction_line_notes.py(JSON 비고 필드). 기존 데이터 삭제/모델 제약 완화 없음. 기존0005 포함 양 DB 검증 완료. 구조별 일치/차이, 수정파일, 미완료 정책과 프린터 한계는 DIETITIAN_FEEDBACK_VERIFICATION.md 최신 절을 따른다. 원본의 입고일 묶음/메뉴별 별도 식수를 임의로 구현하지 않았으며 전체 조리지시서 상태는 PARTIAL로 유지한다.


## 2026-11-04 후속 통합

후속 통합 검증은 `verification/kanghoon2-20261104/`에 별도 보존했다. 기존 117개와 신규 22개를 구분하고, 최종 로그 및 브라우저 JSON을 기준으로 후속 통합 보고서에 결과를 기록한다. 과거 실행 기록을 이번 실행으로 대체하지 않는다.


## 2026-11-04 실제 서비스 종합 재검증

실제 재실행 결과: 수정 전 SQLite/MariaDB 각각139/139. 추가 결함 수정 후 총166개(기존139＋서비스25＋동시성2), SQLite164pass/2행잠금skip, MariaDB166pass. 기존JS4pass, 실제Chromium 업무1시나리오22단계 및 인쇄보완1시나리오 통과. 과거 통과 로그로 대체하지 않았다. 상세: [종합 검증 보고서](INTEGRATION_VERIFICATION_REPORT.md), `verification/comprehensive-20261104/`. 외부공개운영 보안 경고6개와 미검증 사항은 별도다.
