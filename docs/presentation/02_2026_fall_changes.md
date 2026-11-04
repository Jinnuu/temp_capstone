# 2026년 4학년 2학기 추가·개선 기능 — Git 근거

조사일 2026-10-19 / 브랜치 `integration/sprint7-kanghoon` / HEAD `a8d9fae`.

## 날짜와 비교 방법

`git log --all --since=2026-09-01`, `git show`, 부모 커밋 대비 diff, `git diff` 및 현재 미추적 파일을 읽었다. 원격 fetch나 이력 변경은 하지 않았다. 날짜는 Git AuthorDate/CommitDate의 +09:00 기준이다. **커밋 날짜는 반영 기록일이지 실제 개발 착수일·영양사 피드백 수집일이 아니다.**

9월1일 이후 로컬 이력에서 확인한 커밋은 아래5개다. 9월8일 기능 브랜치는 10월15일에 통합됐다. 마지막 기존 Sprint7 기준 `a8f5adb`의 날짜는 2026-06-05다. 따라서 ‘9월 이후 작성’과 ‘9월 이후 보존·통합’도 구별해야 한다.

| 커밋 | 확인 날짜 | 의미 |
|---|---|---|
| `3b01dc8` | 09-08 18:13:38 | 식단 기반 발주·문서·업로드·UI 변경. 부모 대비45파일 diff 존재 |
| `eac48a0` | 10-15 22:18:49 | 기존 미커밋4파일 보존. 코드 최초 작성 날짜는 확인 불가 |
| `e21478b` | 10-15 22:32:54 | 부모 eac48a0/3b01dc8의 병합·회귀/검증 기반 구축 |
| `ab5ed57` | 10-15 22:40:41 | 요구사항 분석·구현 계획 문서. 사용자 기능 추가 커밋으로 세지 않음 |
| `a8d9fae` | 10-15 23:19:26 | 확정 식수·명시 규격·검수·lot·업무권한·공통 화면 구현 |

커밋은 `git show <hash> -- <file>`로 재확인할 수 있다. 공개 저장소 링크 예: [3b01dc8](https://github.com/Jinnuu/temp_capstone/commit/3b01dc8cf8ab229313e959c8b067d62deff8253d), [a8d9fae](https://github.com/Jinnuu/temp_capstone/commit/a8d9faecef04da2368543984fe304d157b25dd16). 링크의 원격 가용성은 이번에 조회하지 않았다.

## 변경 전후 비교

| 변경 날짜·분류 | 변경 전 | 변경 후 | 사용자 효과 | 파일·커밋 및 직접 근거 |
|---|---|---|---|---|
| 09-08 / 발주 흐름 | 단순 기간·끼니 기준 목록 | 발주 요일 선택, 당일 석식과 다음 식사 묶음 로직·날짜별 보고서 보완 | 실제 업무일 기준으로 발주 대상 검토 | `procurement/views.py:order_from_mealplan`, `templates/procurement/order_from_mealplan.html`; 3b01dc8 부모 diff. 현재 정식 저장 로직은 a8d9fae 공통 서비스로 추가 보강 |
| 09-08 / 업무 문서 | 기존 주간·월간·업체·검수 보고서 | 주간 레시피 명세서, 식단조견표, 실무 수불·구입요구서·검수일지 경로 추가 | 문서함에서 현장 양식 접근 | `templates/docs/index.html`, `meals/views_new_docs.py`, `inventory/views_new_docs.py`, `procurement/views_new_docs.py`; 3b01dc8의 신규 URL/View/Template diff |
| 09-08 / 식단 UI | 기본 일/주간 편집 | 메뉴 토큰·신규 이름 입력, 차주 월요일 조중식 영역, 달력·문서 레이아웃 보완 | 메뉴 조작과 주간 발주 범위 검토 용이 | `templates/meals/mealplan_create.html`, `weekly_mealplan_create.html`, `meals/views.py`; 3b01dc8. 실제 가독성 개선률은 확인 불가 |
| 09-08 / 업로드 | 기존 행형·가로형 처리 | 달력형·다중 양식·안내문 제외 등 파서 보완 | 현장 파일을 기존 화면으로 반입 | `meals/views_extra.py`, `inventory/services.py`, 업로드 템플릿; 3b01dc8 diff 및 후속 업로드 회귀 |
| 09-08 / 문서 UI | 기존 업체/월간/예측 문서 레이아웃 | 표·페이지·업체 문서 화면 구성 변경 | 출력 편집 작업 감소 가능 | `templates/docs/vendor_procurement_report.html`, monthly_report.html, weekly_forecast_report.html; diff 확인. 시간 절감 수치는 측정 안 됨 |
| 10-15 / 사용자 변경 보존 | Sprint7 작업 트리의 미커밋4파일 | 대시보드·간편발주 연동 변경을 별도 커밋으로 보존 | 통합 시 기존 개선 누락 방지 | `config/views.py`, `procurement/views.py`, `templates/home.html`, `templates/procurement/order_create.html`; eac48a0. 신규 작성일이 10-15라고 단정 불가 |
| 10-15 / 통합·재고 버그 | 두 브랜치의 단위·경로·집계 차이 | release_patch 업로드/차감 진입점 보존, calc_stock와 단일ID·안전재고 계산 보정 | 기존 기능 유지하며 부족분 발주 오류 감소 | e21478b 부모별 diff, `inventory/views.py`, `procurement/views.py`, `static/js/smart_order.js`, `integration_tests/test_workflows.py`; 수치 개선율은 없음 |
| 10-15 / 의존성·migration | 브랜치별 requirements 차이·모델/기존 migration 불일치 | 기존 AI 패키지 핀 유지＋xlrd, 거래일자 default와 발주 상태 migration 추가 | Excel 호환과 모델 환경 보존, schema 이력 일치 | e21478b `requirements.txt`, inventory/0007, procurement/0005. 모델을 재학습한 변경 아님 |
| 10-15 / 검증 기반 | 통합 핵심 회귀 증거 부족 | SQLite/MariaDB 격리 설정·모델 실제 추론·기존 데이터 migration·JS 회귀 추가 | 반복 검증 및 오류 재현 가능 | e21478b `config/test_*.py`, `scripts/verify_integration.sh`, `integration_tests/test_ai.py/test_migrations.py/test_workflows.py`, verification/. 첫 통합48개 기록 |
| 10-15 / 식수 결정 | e21478b get_serving_count에 예측값 대체 경로 | 수동 예상·AI 참고·최종 확정 식수 및 확정 시점 분리 | AI를 참고하되 영양사 결정으로 발주 | a8d9fae `meals/models.py`, meals/0004, `workflow.py:save_headcount`, `templates/workflow/hub.html`; 부모 코드와 실제 필드 diff |
| 10-15 / 레시피 단위 | 재료의 재고 단위와 레시피 1인량 단위 혼동 가능 | Recipe.unit 및 정밀도 확대, 업로드가 재고 단위 변경하지 않게 보완 | g/kg 환산을 명시하고 기존 재고 보호 | a8d9fae `meals/models.py`, `recipe_file_views.py`, `release_patch_views.py`, `workflow_forms.py`; 단위 보존 테스트 |
| 10-15 / 규격·발주 승인 | 단순 발주와 자유문자 규격 중심 | 구조화한 업체 규격/내용량/간격, 계획 스냅샷·수량 조정·확정 | 35kg/5kg=7캔 등 검토 가능한 발주량 | a8d9fae `SupplySpecification`, ProcurementPlan/Line, `workflow.py:build_preview/confirm_orders`, inventory/0008/0011·procurement/0006/0008 |
| 10-15 / 검수와 입고 | e21478b order_status_update의 ‘완료’ 변경 시 자동 입고 | 실제 납품·합격량과 사유를 저장하고 합격량만 입고 | 불합격 물량까지 재고로 세는 위험 제한 | a8d9fae `procurement/views.py`, `workflow.py:inspect_item`, GoodsInspection; 45kg중40kg 합격 브라우저 증거 |
| 10-15 / 재고 정합성 | 원장 중심, lot/요청키 근거 부족 | StockLot/Allocation·요청 UUID·중복/부족 차단·주간 수불 | 신규 거래 추적과 선입선출 근거 확보 | a8d9fae `inventory/lot_services.py`, `workflow.py:record_inventory`, inventory/0010, `templates/workflow/ledger.html`; 기존 lot 대사는 별도 |
| 10-15 / 변경 재검토 | 식단/레시피 변경 후 연결 발주 상태 전달 제한 | signals와 fingerprint로 재검토 표시·검수 제한 | 변경 전 발주를 그대로 입고하는 상황 예방 | a8d9fae `procurement/signals.py`, `workflow.py`, needs_review 필드. 취소·대체 UI 전체 완성 아님 |
| 10-15 / 권한 | 공통 내부업무 보호 미들웨어 없음 | 로그인·비직원 공급업체 업무 차단, 관리자 기준정보 화면 제한 | 업무 화면 접근 범위 구분 | a8d9fae `config/business_access.py`, settings 미들웨어 및 관리 View. 전체 보안 인증 취득 의미 아님 |
| 10-15 / 문서·운영 보완 | 업체 username 정렬/유통기한 가공·분류 반복 등 | 실제 업체명 정렬·기한 표시 보정·분류 묶음, 월말 참고자료 | 현장 용어·검수·집계 가독성 개선 | a8d9fae `procurement/views_new_docs.py`, `templates/docs/doc_purchase_requisition.html`, `workflow_views.py:settlement`; 요구별 회귀 |

## 아직 커밋되지 않은 후속 구현

아래는 현재 파일·기존 10월16일자 보고서·실행 증거로 변경 전후를 확인한 내용이다. **Git 반영 날짜는 확인 불가**이며 파일 수정시각을 개발일로 대체하지 않았다. 이전 보고서의 ‘2026-10-16’은 작업 기록일이다.

| 기록일 / Git 상태 | HEAD 상태 | 현재 작업 트리 | 사용자 효과·근거 |
|---|---|---|---|
| 10-16 기록 / 미커밋·일부 미추적 | 전용 조리지시서 모델·URL·View 없음 | CookingInstruction, 식사별 최종식수·총량, 현장/재료별 비고, revision, 날짜별/식사별 XLSX·인쇄 | `meals/cooking*.py`, `models.py`, `urls.py`, meals/0005·0006, `templates/workflow/cooking_*.html`; git show HEAD 및 현재 파일 차이、16개 테스트·브라우저 기록 |
| 10-16 기록 / 미추적 원본·코드 | 일반10열 가로 기본 출력(최초 후속 버전은 보고서로만 확인) | 실제6열·A1:H1·숨김G/H·A4세로·계산근거·긴 한글 비고 분할 | `cooking_export.py`, reference Excel, `verification/cooking-format/reference-analysis.json`; 실제 원본 구조 비교 테스트. 최초 후속 버전은 Git에 없어 완전 재구성 불가 |
| 10-16 기록 / 테스트 수정 | cooking 픽스처 safe_stock_level 누락 | 필수값0 명시, 모델 NOT NULL 유지 | `integration_tests/test_cooking.py`; 사용자 오류 기록과 후속12/16개 통과 로그 |
| 10-16 기록 / 테스트 수정 | 수불 테스트가 UTC now.date로 업무일 조회 | 고정 UTC와 서울 localdate 경계값 확인 | `integration_tests/test_requirements.py` git diff. 제품 집계 알고리즘 수정이 아니라 시간 의존 테스트 보정 |
| 10-16 기록 / 미커밋 | MariaDB 소켓 경로 고정 | SPRINT7_DB_SOCKET_DIR 선택 옵션 | `scripts/verify_integration.sh` git diff. 기존 DB와 분리한 재검증 가능 |

## AI 변경에 대한 별도 결론

`git log --all -- forecasting/services/prediction_service.py forecasting/services/processor.py ml_models`에서 서비스/모델 연동의 주요 이력은 `ded88f3`(2026-03-28, forecasting flow)다. 가을 기간에는 호출부가 최종 확정 식수/발주 흐름과 연결되고 실제 모델 호환 테스트가 추가됐다. **가을에 새 알고리즘을 학습해 정확도가 향상됐다는 비교 근거는 발견하지 못했다.**

확인되는 사항은 조·중·석식 저장 모델 사용, SBERT/KMeans 특성 처리 경로, 오프라인 fallback, 모델 로드·추론/DB 저장 시험이다. 연구 문서에 PCA·OOF·오차 보정이 등장하더라도 현재 서비스에 동일한 전체 연구 실험이 적용됐다고 단정하지 않는다.

## 발표용 기간 표현

로컬 저장소의 최초 이력은 2026-03-16 `41804d6`이다. D05는 3-2 연구/4-1 개발/4-2 현장 검증을 재구성했다고 설명한다. 이는 ‘3개 학기 프로젝트’라는 사용자 설명을 보조하지만, **3학년2학기의 실제 개발 이력 전체와 각 기능의 최초 구현일은 현재 Git만으로 확인 불가**다. PPT에서 ‘이번 학기 신규’에는 위 커밋 diff로 확인한 변경만 표시하고, 기존 기능과 통합/보존 작업을 분리한다.
