# 식수센스(SNP) 최종발표 — 실제 화면 검증·스크린샷

작업일: 2026-10-19(Asia/Seoul). 신규 산출물이며 기존01~05 조사 문서·애플리케이션 코드·AI 모델은 수정하지 않았다.

## 1. 브랜치 생성과 변경 보존

| 항목 | 실제 결과 |
|---|---|
| 기존 브랜치 | integration/sprint7-kanghoon |
| 신규 작업 브랜치 | sprint-final (기존에 없었음) |
| 기준 HEAD | a8d9faecef04da2368543984fe304d157b25dd16 |
| 기존 branch ref | 동일 HEAD 유지, 이동/덮어쓰기 없음 |
| 기존 stash | 비어 있음. 새 stash도 만들지 않음 |
| 미커밋 변경 | 추적 수정11개·미추적46개 파일을 모두 보존 |
| 보존 확인 | 기존615파일 SHA-256 동일. 원본 참고 자료와 모델 포함 |
| 백업 | /tmp/snp-finalprep-wisanw0k/ (0700), tracked-changes.patch·untracked-before.tar.gz·hashes-before.json·git-status-before.txt |
| 커밋/원격 | 새 커밋·push·PR 없음 |

처음 브랜치 생성은 샌드박스의 .git 읽기 전용 제한으로 실패했고 승인된 동일 `git switch -c sprint-final`로 성공했다. reset/clean/stash 적용은 하지 않았다. **브랜치 생성은 미커밋 파일을 Git 커밋으로 저장하지 않는다.** 작업 트리의 변경이 그대로 따라온 상태이며, 별도 영구 보존을 위한 커밋 여부는 이번 작업에서 결정하지 않았다. .git 메타데이터 외 기존 파일은 그대로다. AGENTS.md의 기본 브랜치 문구는 수정하지 않고 사용자 지정 sprint-final을 따랐다.

전체 보존 목록과 모델/원본 해시는 [preservation.json](demo_artifacts/preservation.json)에 있다. 임시 백업 경로는 재부팅·/tmp 정리 시 없어질 수 있으므로 영구 백업으로 간주하지 않는다.

## 2. 기존 조사·검증 산출물 확인

- docs/presentation/01~05: 모두 존재, 읽기 전용으로 재사용.
- docs/analysis/DIETITIAN_FEEDBACK_VERIFICATION.md, FUNCTIONAL_TEST_REPORT.md, REMAINING_ISSUES.md: 존재.
- **docs/analysis/FINAL_READINESS_REPORT.md, DEMO_SCENARIO.md: 존재하지 않음.** 내용을 추정해 복원하거나 새로 만들지 않았다.
- 기존 SQLite/MariaDB 각117개 통과 로그: verification/cooking-format/sqlite.log·mariadb.log. 이번에는 코드 변경이 없어 전체 회귀를 반복하지 않았다.
- 기존 거래 E2E: verification/requirements/browser.json. 조리지시서 E2E·생성 XLSX/PDF: verification/cooking-format/. 과거 실행 증거로 분류한다.

## 3. 이번 새 브라우저 검증

Chromium148, viewport1920×1080, DPR1. 새 테스트 앱의 tmpfs SQLite에만 가상 데이터를 구성했다. 소스/모델/wheels는 읽기 전용으로 마운트, 외부 HTTPS 요청은 브라우저에서 차단했다. 호스트 포트는 공개하지 않았다. 기존 운영 DB/.env에 연결하지 않는 config.test_settings만 사용했다.

- 임시 컨테이너: snp-finaldemo-web-20261019
- 새 내부 네트워크: snp-finaldemo-20261019
- 소유 라벨: snp.task=final-presentation-20261019
- 실행 중 주소: http://192.168.80.2:8000 (이번 폐기용 앱 내부 주소, **현재는 정리되어 유효한 시연 주소가 아님**)
- 정상 실행: 핵심 흐름13개 체크포인트 통과, page error0. 보충 캡처 시나리오도 성공.
- 로그: [browser_result.json](demo_artifacts/browser_result.json), [browser.log](demo_artifacts/browser.log), [supplement.json](demo_artifacts/supplement.json).
- 시작 당시 한 번은 스크립트가 헤더에 이름이 표시된다고 잘못 가정해 중단됐다. 실제 UI는 계정ID를 표시하므로 **/tmp의 검증 스크립트만** 조정했고 전체 흐름을 다시 실행해 성공했다. 제품 코드 오류로 세지 않았다. demo_artifacts/failure.png는 첫 시도의 진단용이며 PPT 사용 대상이 아니다.

### 사용한 가상 데이터와 실제 결과

| 구분 | 값 |
|---|---|
| 가상 식단 | 2026-10-16(금) 석식, 참치비빔밥·두부구이 |
| 가상 레시피 | 참치비빔밥: 참치100g＋쌀100g/인; 두부구이: 두부100g/인 |
| 식수 | 기존 웹 모델 석식 AI **133명**, 수동 **360명**, 최종 **351명** |
| 소요량 | 참치·쌀·두부 각각35.1kg |
| 선입고 | 쌀50kg, lot/기한2026-12-31. 참치/두부0, 안전재고0 |
| 명시 규격 | 참치5kg/캔·500원/캔, 두부3kg/판·300원/판, 쌀20kg/포대·1000원/포대. 금액은 시연값이며 시세가 아님 |
| 발주 | 참치 최소8캔→사용자9캔/45kg/4500원, 두부12판/36kg/3600원, 쌀0포대(선입고 활용) |
| 업체 | 가상 가나유통·가상 다온식품으로 주문2건 분리 |
| 검수 | 참치45kg 납품 중40kg 합격,5kg 품질 이상 제외. 두부36kg 합격 |
| 사용·잔량 | 각35.1kg 출고 후 참치4.9kg·쌀14.9kg·두부0.9kg |
| 실제 로그 시점 | 2026-10-19. 식단 기준일10/16과 검수/사용 기록일10/19는 다름. 가상 과거 식단 시연이며 실제 급식 실적이 아님 |

현재 저장 모델은 교체·재학습하지 않았다. 서버 로그에서 **SBERT 캐시 부재에 따른 기존 fallback**을 확인했다. 따라서133명은 이 격리 조건에서 실제 기존 모델이 반환한 참고값이며 정상 임베딩 경로의 정확도 보증이나 최신 Optuna 연구 모델의 결과가 아니다. 이번 작업의 모델 SHA-256은 기존과 동일하다.

### 화면별 확인 범위와 PPT 추천

‘신규’는 이번 실제 Chromium 조작이다. ‘기존’은 이전 자동화/브라우저 증거를 재사용했다는 뜻이다.

| 화면 | 접근 경로 | 이번 실제 확인·저장/연계 | PNG·추천도 | 주의·미확인 |
|---|---|---|---|---|
| 1 로그인/대시보드 | /accounts/login/ → /?date=2026-10-16 | 로그인 세션·운영현황·선택날짜 식단·현황 표시 | [01_dashboard_selected.png](screenshots/01_dashboard_selected.png) **높음** | 최초01_dashboard.png는 식단 생성 전,01_dashboard_after.png는 기본10/19 조회라 상대적으로 정보가 적음. 추천은 selected 버전 |
| 2 식단 | /meals/mealplan_create/?date=2026-10-16 → /meals/mealplan/weekly/?start_date=2026-10-12 | 메뉴2개 입력·생성→재조회→같은 구성을 재저장→주간 표 확인 | [02_mealplan.png](screenshots/02_mealplan.png) **높음** | 이번에 다른 메뉴로 교체하는 수정은 하지 않음. 수정/빈 선택/ID 보존은 기존 회귀로 구분 |
| 3 메뉴/레시피 | /procurement/workflow/recipes/1/ → /recipes/ | 1인량110g 저장·재조회 후100g 복원, 단위/메뉴별3개 레시피 표시 | [03_recipe.png](screenshots/03_recipe.png) **중간** | 메뉴 신규 등록은 준비 데이터로 구성해 이번 UI 시험 대상 아님. 폼이 길어 발표에서는 식재료/단위 표에 집중 |
| 4 AI/최종 식수 | /forecasting/predict/?date=2026-10-16 → /results/ → /procurement/workflow/ | 실제 예측 실행, 수동360/최종351 저장·재조회, AI133과 구분 | [04_headcount.png](screenshots/04_headcount.png) **높음**, [04a_ai_predictions.png](screenshots/04a_ai_predictions.png) 보조 | UI에 SBERT fallback 상태가 별도 표시되지 않으므로 발표자가 제한을 설명. 최종 저장 후 폼은 초기화되고 표에 결과가 남음 |
| 5 소요량·재고 반영 | /procurement/workflow/preview/ | 미확정 경고 먼저 확인→확정 후 재료별35.1kg·쌀50kg·포장수 확인 | [05_ingredient_requirements.png](screenshots/05_ingredient_requirements.png) **높음** | 레거시 /forecasting/requirement/의 ‘예측 식수’ 문구와 혼동을 피하려 정식 발주 미리보기 화면 사용 |
| 6 발주예정서 | /procurement/workflow/plans/1/ | 계획 저장, 필요량·날짜·메뉴·1인량·비고, 최소8/12 포장수 | [06_procurement_plan.png](screenshots/06_procurement_plan.png) **높음** | 쌀은0포대로 표에 표시되지만 실제 구매 주문에는 포함되지 않음. 소수6자리 표기는 그대로 유지 |
| 7 업체별 구매발주서 | 동일 plans/1/ 하단 | 참치9캔으로 조정·저장→실제 업체2건 분리 및 수량 재조회 | [07_purchase_order.png](screenshots/07_purchase_order.png) **높음** | 하단으로 스크롤한 실제 viewport라 상단 탐색 메뉴는 안 보임. 이메일/실업체 자동 전송은 아님 |
| 8 검수·합격량 입고 | /procurement/workflow/inspections/?date=2026-10-16 → 품목 검수 | 납품·합격량·사유·기한 저장→40/36kg 입고. 같은 검수 재전송 후 재고40kg 유지 | [08_inspection.png](screenshots/08_inspection.png) **높음** | 부분 합격을 검증. 다회 분할 납품/확정 정정은 미구현이며 시연하지 않음 |
| 9 재고 사용/주간 수불 | /meals/deduct_inventory/?date=2026-10-16&meal_type=석식 → /procurement/workflow/ledger/ | 실제 차감 버튼→4.9/14.9/0.9kg 잔량, lot 잔량·기한 재조회 | [09_weekly_ledger.png](screenshots/09_weekly_ledger.png) **높음** | 10/19~25 정확한1주: 쌀 기초50, 이번주 입고0, 사용35.1, 기말14.9. 원래09_inventory_ledger.png는10/12~25의2주 추적 범위이므로 ‘1주 화면’으로 소개하지 않음 |
| 10 조리지시서 | /meals/cooking/?date=2026-10-16 → /meals/cooking/1/ | 재료별/공통 지시 저장·재조회·Excel 다운로드·인쇄 CSS와 PDF 출력. 이후 원장 동일 확인 | [10_cooking_instruction.png](screenshots/10_cooking_instruction.png) **높음**, [10_cooking_print.png](screenshots/10_cooking_print.png) 출력 보조 | 원본의 입고일 묶음/대상집단 식수까지 동일한 것은 아님. 편집 화면 하단 공통 지시는1080px 밖이므로 출력 버전/PDF 병행 |

### 보존된 과거 증거와 이번 증거의 구별

| 구분 | 범위 |
|---|---|
| 기존117개×DB2종 | 모델·migration·권한·FIFO·업로드·계산·동시 수정의 순차 재전송 등 회귀. 이번에 재실행하지 않음 |
| 기존 거래/조리지시서 E2E | 단일참치 흐름 및 식수351→352 재계산. 이번에 변경 식수 재계산까지 반복하지 않음 |
| 이번 신규 주 흐름 | 화면10종과 계산/저장·재조회·업체분리·검수입고·차감·출력,13개 체크포인트 성공 |
| 이번 신규 보충 | 선택 날짜 대시보드, 정확한1주 수불, 조리지시서 print media 화면 |
| 이번 출력 검증 | PNG15장 모두1920×1080. 다운로드 Excel3행 총량35.1kg·포장 사용량11.7판/1.755포대/7.02캔 확인. A4세로 PDF1페이지 생성 및 직접 이미지 열람 |

## 4. 산출물 목록과 사용법

주요 PNG:01_dashboard.png,02_mealplan.png,03_recipe.png,04_headcount.png,05_ingredient_requirements.png,06_procurement_plan.png,07_purchase_order.png,08_inspection.png,09_inventory_ledger.png,10_cooking_instruction.png.

추가 PNG:01_dashboard_after.png,01_dashboard_selected.png,04a_ai_predictions.png,09_weekly_ledger.png,10_cooking_print.png. 총15장 모두 원래 Chromium viewport 그대로 저장했다. 합성·내용 가림·텍스트 교체·모델 결과 수정은 하지 않았다. 가상 계정ID와 가상 업체만 표시되며 비밀번호/API 키/실제 개인정보는 포함하지 않았다.

- [조리지시서 실제 다운로드 Excel](demo_artifacts/cooking_instruction.xlsx)
- [A4 인쇄 PDF](demo_artifacts/cooking_instruction.pdf)
- [이미지 크기·Excel 수치 검사](demo_artifacts/artifact_checks.json)
- [신규 브라우저 실행 결과](demo_artifacts/browser_result.json)
- [브랜치/원본/모델 보존 결과](demo_artifacts/preservation.json)

PPT에는 PNG를 원본 비율16:9로 삽입하고 제목·강조 설명은 슬라이드의 별도 설명으로 넣을 수 있다. 원본 PNG의 시스템 내용을 바꾼 것처럼 만들지 않는다. 로그인 비밀번호 입력 화면은 캡처하지 않았다.

## 5. 발표 전 반드시 확인할 것

1. 라이브 시연은 새 격리 데이터로 리허설해야 한다. **이번 임시 앱·DB·네트워크는 정리했으므로 현재 실행 중인 시연 서버가 아니다.** 스크린샷/Excel/PDF 시연은 즉시 가능하다.
2. 이미 완료한 검수·출고와 같은 날짜를 같은 DB에서 반복 시연하면 중복 방지에 걸린다. 기존 자료를 지우지 말고 매번 새 폐기용 환경을 준비한다.
3. AI133은 이번 fallback 조건의 실제 참고값이다. 최신 Optuna 연구 모델·정확도 성과와 혼동하지 않는다. 라이브에서는 사전 예측과 수동 확정 경로를 준비한다.
4. 화면 S&P/Smart Nutritionist Program과 발표명 ‘식수센스(SNP)’ 차이, 레거시 ‘예측’/‘확정’ 문구 차이, 포장 수량 소수6자리 및 일반 식재료 수정 화면 부재를 설명한다. 이번에는 코드 수정하지 않았다.
5. 실제 프린터 인쇄·본 발표 장소의 화면/네트워크·정상 SBERT 경로·실운영 DB 상태는 이번 검증 범위 밖이다.

이번 신규 테스트 앱에는 네트워크 단절과 읽기 전용 소스가 적용됐고 기존8000/8007서비스 및 운영DB/볼륨/네트워크는 접근·변경하지 않았다. 소유 라벨을 확인한 뒤 이번 컨테이너·네트워크만 제거했다. docker compose·push·PR·배포·모델 교체는 수행하지 않았다.

## 부록 A. 보존된 기존 추적 수정11개

```text
MERGE_REPORT.md
docs/analysis/FUNCTIONAL_TEST_REPORT.md
docs/analysis/IMPLEMENTATION_PLAN.md
docs/analysis/REMAINING_ISSUES.md
docs/analysis/REQUIREMENT_TRACEABILITY_MATRIX.md
docs/analysis/requirement_catalog.json
integration_tests/test_requirements.py
meals/models.py
meals/urls.py
scripts/verify_integration.sh
templates/workflow/hub.html
```

## 부록 B. 보존된 기존 미추적46개(디렉터리 확장 목록)

```text
AGENTS.md
docs/analysis/DIETITIAN_FEEDBACK_VERIFICATION.md
docs/presentation/01_current_features.md
docs/presentation/02_2026_fall_changes.md
docs/presentation/03_dietitian_feedback.md
docs/presentation/04_system_architecture.md
docs/presentation/05_ppt_evidence_summary.md
integration_tests/browser_cooking.cjs
integration_tests/seed_readiness.py
integration_tests/test_cooking.py
meals/cooking.py
meals/cooking_export.py
meals/cooking_views.py
meals/migrations/0005_cookinginstruction.py
meals/migrations/0006_cookinginstruction_line_notes.py
templates/workflow/cooking_detail.html
templates/workflow/cooking_index.html
verification/cooking-format/browser-cooking.xlsx
verification/cooking-format/browser-print.pdf
verification/cooking-format/browser-screen.png
verification/cooking-format/browser.json
verification/cooking-format/browser.log
verification/cooking-format/git-status.txt
verification/cooking-format/mariadb.log
verification/cooking-format/reference-analysis.json
verification/cooking-format/sqlite.log
verification/environment/check-attempt.log
verification/environment/cooking-tests-attempt.log
verification/environment/docker-mariadb-attempt.log
verification/environment/docker-sqlite-attempt.log
verification/environment/download.log
verification/environment/model-compatibility.log
verification/environment/pip-after.txt
verification/environment/pip-before.txt
verification/environment/pip-check-after.txt
verification/environment/pip-check-before.txt
verification/environment/status.json
verification/feedback/django-attempt.log
verification/feedback/javascript-direct.log
verification/feedback/javascript.log
verification/feedback/mariadb-recheck.log
verification/feedback/sqlite-recheck.log
verification/feedback/static.log
verification/final-readiness/files-before.json
verification/final-readiness/git-before.txt
verification/final-readiness/sqlite-baseline.log
```
