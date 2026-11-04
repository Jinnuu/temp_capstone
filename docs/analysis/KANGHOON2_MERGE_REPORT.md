# Sprint-final × comprehensive-improvement2 통합 보고서

작업일: 2026-11-04. 이 문서는 과거 통합 보고서·시험 결과를 대체하지 않는다.

## 1. 시작 상태와 복구 지점

- 작업 경로: `/home/woohyeak/sprint7-integration`.
- 원본 브랜치: `sprint-final`, HEAD `1aa6302` (`mid-presentation`). 시작 시 추적/미추적 작업 변경 없음, stash 없음.
- `git fetch origin` 후 대상: `origin/feat/kanghoon/comprehensive-improvement2`의 `4cb648f`.
- 팀원 커밋: `27f0edc`(공급업체·문서/UI), `4cb648f`(식단·예측). 공통 조상 `3b01dc8`.
- 복구 브랜치: `backup/sprint-final-before-kanghoon2-20261104` → `1aa6302`.
- 통합 브랜치: `integration/sprint-final-kanghoon2-20261104`. `sprint-final`과 이전 통합 브랜치 포인터는 유지한다.
- 팀원 측 공통 조상 대비35파일, 2,998줄 추가/726줄 삭제. 이 수는 순수 신규 기능 수가 아니다.
- 백업 브랜치로 원본 상태를 별도 checkout/worktree에서 재현할 수 있다. 현재 통합 브랜치를 덮어쓰거나 파괴적 reset할 필요 없다.

## 2. 기능별 결정

| 영역 | 양쪽 차이 | 통합 결과 |
|---|---|---|
| 공급업체 | 기존 User 역할/FK·납품규격과 새 Supplier 연락처 테이블 | 기존 FK를 바꾸지 않고 OneToOne 연락처를 추가. 기존 공급업체 계정을 명시 선택하거나 로그인 불가 SUPPLIER 계정을 생성. 조회는 무변경, 관리자만 변경, 연락처 삭제 시 계정/발주 유지 |
| 식재료 | 수정 링크가 등록 화면을 가리킴 | 실제 PK 기반 수정 URL/View/화면 연결. 연결된 재고·레시피·규격의 기준 단위 직접 변경과 음수 값 차단, 발주 재검토 표시 |
| 발주·규격 | 기존 명시 규격/확정 식수 vs 자유문자 파싱·단위 추정 | 기존 workflow 계산·안전재고·금요일 묶음·발주 간격·스냅샷 유지. utils의 함수 이름은 유지하되 자유문자 추정 없이 명시적 SupplySpecification을 받을 때만 포장 환산 |
| 검수 | 기존 합격량 입고/중복 방지 vs 문서 변경 | 거래 로직은 기존 유지. 팀원의 검수 문서 헤더 레이아웃 반영. 납품량·합격량·원장 연결은 기존 서비스 사용 |
| 재고·수불 | 기존 주/월 원장·FIFO vs 기간 조회·거래 품목만 표시 | 기존 원장/FIFO 유지. 기간 조회 추가, 기존 month/year 쿼리 유지. 거래 없는 기초잔량을 숨기지 않으며 activity_only=1일 때만 실거래 필터 적용 |
| 식단 | 미등록 이름 생성·다음 월요일 편집 vs 등록 메뉴만 허용·해당 영역 제거 | 기존 API와 주간 검색/다음 월요일 편집 유지. 일간 화면 글자·중복 메뉴 입력 경고 보완 반영. 신규 메뉴는 레시피 없으면 기존 발주 검증에서 경고 |
| 예측 | 기존 날짜별 실행 vs 같은 날짜 전체 실행 차단·캘린더 상세 | 끼니별 기존 결과를 유지하면서 누락 끼니만 실행. 모두 있으면 안내 후 결과로 이동. 캘린더에 끼니별 예측/합계 표시. 모델·학습·의존성 변경 없음 |
| 조리지시서 | 기존 저장/수정/Excel/명시 단위 vs 기간 인쇄 문서·500명 기본값 | 새 기간 인쇄 양식이 기존 cooking_sheet를 호출. 최종 식수·0명·미확정·단위 경고·재료별/문서 비고 유지. 기존 편집·Excel에 연결. 재고 자동 차감 없음 |
| 월간 정산서 | 기존 합격량 월말 참고집계 vs 새 발주/카테고리 문서 | 기존 정산 URL 유지하고 별도 발주 참고 문서 추가. 명시 target_date 우선, 날짜 없을 때만 주문 생성일 사용. 단위별 수량 구분·0원 보존·빈 결과 샘플 제거 |
| 문서·내비게이션 | 신규 URL·템플릿·CSS와 기존 workflow/문서 메뉴 | 모든 기존 URL 유지, 새 업체현황·기간 조리지시서·월간 발주 문서 링크 추가. 기존 구입요구서 분류 묶음·업체별 주문 스냅샷 계산 유지 |

## 3. 충돌 및 migration

`git merge --no-commit --no-ff`에서16파일 충돌을 확인했다. 단순히 한쪽을 최종본으로 선택하지 않고 기존 동작을 복원한 뒤 팀원의 독립 기능을 다시 연결했다.

| 충돌 파일 | 해결 이유/방식 |
|---|---|
| forecasting/views.py | 기존 모델 호출 유지 + 끼니별 중복 처리/캘린더 상세 결합 |
| inventory/urls.py, inventory/views.py | 업로드/차감/원장 경로 유지 + 식재료 수정 추가 |
| meals/views_new_docs.py | 확정 식수·명시 단위 계산 유지, 표시 정밀도 보완 |
| procurement/urls.py, procurement/views.py | 기존 발주/검수 workflow 그대로 유지, 새 View 모듈로 URL 확장 |
| procurement/views_new_docs.py | 기존 분류 묶음·검수 수량·업체 정렬 유지, 새 조리지시서는 공통 계산 어댑터 사용 |
| templates/docs/doc_inventory_status.html | 팀원 기간 입력 UI + 기존 월 조회 호환·기초재고 보존 |
| templates/docs/doc_menu_overview.html | 기존 확정값/비고/수기 빈 양식 보존 |
| templates/docs/doc_purchase_requisition.html | 기존 카테고리 regroup/중복 표시 제거 보존 |
| templates/docs/index.html | 기존 문서 메뉴 유지 + 새 메뉴 추가 |
| templates/docs/vendor_procurement_report.html | 기존 규격·발주량 표시 계약 보존 |
| templates/inventory/ingredient_form.html | 수정/등록 분기 양식 반영 |
| templates/meals/weekly_mealplan_create.html | 다음 월요일 조중식 편집·메뉴 검색 보존; 제거하는 팀원 레이아웃 보류 |
| templates/partials/top_nav.html | 기존 메뉴 유지 + 업체현황 링크 |
| templates/procurement/order_from_mealplan.html | 기존 발주 요일/수량 계산·확정 UI 보존 |

마이그레이션:

- 팀원 원본 `procurement/0005_supplier.py`를 파일명/의존성 그대로 유지한다. 기존 `0005_alter_purchaseorder_status.py`와 서로 다른 분기이며 같은 숫자 자체는 오류가 아니다.
- 신규 `procurement/0009_merge_supplier_workflow.py`: `0005_supplier`와 기존 `0008_procurementplanline_order_increment_and_more`를 연결하는 **operations=[]** 병합 migration.
- 기존 meals/0005·0006 조리지시서 migration 및 inventory 기존 이력은 수정하지 않았다.
- 격리 DB에서 신규 적용, 적용 완료 검사, 기존 데이터 업그레이드 보존 회귀를 실행했다. 실제 운영 DB에 적용하지 않았다.
- 중간 테스트에서 임시로 변경한 migration 이름을 원복한 뒤 task DB의 기존 중간 테이블과 충돌했다. 이 task에서 생성한 tmpfs DB 컨테이너만 폐기하고 새 이름으로 생성해 최종 그래프를 검증했다. 기존 DB/볼륨에는 접근하지 않았다.

## 4. 실제 검증 결과

| 검증 | 결과/증거 |
|---|---|
| 수정 전 baseline | 1aa6302 archive,117개 중115통과/1실패/1skip. 만료 검사 테스트의 고정10월 날짜와 실행일 상대 만료일 불일치 재현. Git 밖 참조 Excel 미포함으로 양식 시험1개 skip |
| Django system check | SQLite/MariaDB 모두0 issues |
| makemigrations --check --dry-run | 양쪽 모두 No changes detected |
| migrate / migrate --check | 양쪽 모두 적용/완료 검사 통과. Supplier 생성 및 병합 노드 포함 |
| SQLite 전체 | **139/139 통과, 실패0, skip0** = 기존117 + 신규22 |
| MariaDB 전체 | **139/139 통과, 실패0, skip0**. 같은 케이스 재실행이므로278개 독립 케이스가 아님 |
| 기존 JS | **4/4 통과** |
| Chromium 조리지시서 | 기존 스크립트 출력경로만 분리해 실행:351→352명,35.1→35.2kg, 저장/재조회,Excel,인쇄CSS/PDF 통과 |
| Chromium 핵심 흐름 | 기존 스크립트 테스트 날짜를11월6일/11월2~8일로 조정:351명→35.1kg→최소8캔/조정9캔→4,500원→납품45/합격40kg→사용35.1→잔고4.9kg 통과 |
| Chromium 신규 문서/업체 | 업체 계정 명시 연결/수정·재조회/연락처 삭제 후 주문 유지, 실제 월간45kg·4,500원/빈 달 샘플 없음, 식재료 수정, 기간 조리지시서→기존Excel, 수불 불변 통과.8 checkpoints=1시나리오 |
| 원본 보존 | requirements,AI 모델3개/processor/prediction_service,workflow,lot,release_patch,기존 cooking 서비스,JS 계산 파일 바이트 동일 |

명령:

```bash
bash scripts/verify_integration.sh
SPRINT7_DB_SOCKET_DIR=/tmp/snp-kanghoon2-db-final-socket-20261104 bash scripts/verify_integration.sh config.test_mysql_settings
node --test integration_tests/smart_order.test.cjs
SNP_BROWSER_BASE=<이번 작업의 격리 앱 주소> node verification/kanghoon2-20261104/browser_cooking.cjs
SNP_BROWSER_BASE=<이번 작업의 격리 앱 주소> node verification/kanghoon2-20261104/browser_workflow.cjs
SNP_BROWSER_BASE=<최종 코드로 로드한 격리 앱 주소> node verification/kanghoon2-20261104/browser-team2.cjs
```

기존117개 중 만료 시나리오1개의 날짜 준비만 현재 기준으로 수정했다. 알고리즘/기대 거부 결과는 유지했다. 신규22개는 `integration_tests/test_kanghoon2.py`에 있으며 업체/계정/권한·월별 날짜·단위·0원·조리지시서·단위변경·예측 재시도를 확인한다. 중간 실패와 최종 로그를 구별한다. 모든 실행 증거: `verification/kanghoon2-20261104/README.md`.

## 5. 보류·남은 문제

1. 자유문자 spec에서 통/봉 중량 추정, mL≈g 가정, 미확정500명 대입은 기존 업무 규칙을 훼손하므로 통합하지 않았다. 기존 명시 규격 입력을 사용한다.
2. 팀원의 미등록 메뉴 생성 금지·주간 다음 월요일 영역 제거는 기존 기능과 직접 충돌하여 보류했다. 정책 변경은 영양사 확인 후 별도 적용해야 한다.
3. 세율10%·과세 포함가 가정은 데이터 근거가 없어 적용하지 않았다. 월간 새 문서는 발주 참고 집계이며, 실제 세금/청구/대금 확정은 아니다. 합격량 정산 화면은 기존대로 별개다.
4. 실제 공급업체 연락처·기존 User 대사는 자동 시딩하지 않았다. 관리자가 명시 연결해야 한다. 기존 User와 연결한 프로필의 계정 재할당은 막았다.
5. 검수 여러 차수 누적 입고·수정/환불·취소 정산은 기존의 단일 검사 모델 한계가 남는다. 이번에 임의 확장하지 않았다.
6. 기존 미배정 재고는 FIFO 이력을 가정하지 않는다. 실제 DB migration 적용 전 별도 백업·적용 이력/lot 대사가 필요하다.
7. 실제 영양사 인수·동시 등록/검수 부하·온라인 SBERT 전체·실제 프린터 품질은 미검증이다. PDF 생성 성공을 실물 인쇄 보증으로 표현하지 않는다. 기간 양식의 긴 단일 식단 인쇄 분할도 현장 확인이 필요하다.
8. `fix_ingredient_categories`, `seed_workflow_test`, 기존 reset 명령은 **실행하지 않았다**. 명령 파일 존재가 실제 데이터 정정/검증 완료를 뜻하지 않는다.

## 6. 보호 경계 및 후속 작업

- 기존 ~/sprint7, 8000/8007/8010 서비스, 운영 DB·볼륨·네트워크를 수정/재시작하지 않았다. docker compose 사용 없음.
- 호스트 Python/Conda/AI 모델 변경 없음. 검증은 capstone-web:sprint7, Python3.12.13/Django6.0.3 및 새 tmpfs MariaDB10.6/SQLite에서 실행했다.
- 이번 task 이름의 DB/app 컨테이너·새 internal network만 사용 후 정리한다. 기존 snp-readiness-db 등은 건드리지 않는다.
- push·PR·배포 없음. 원본 브랜치에 직접 커밋하지 않는다.
- 배포 전: 운영 DB 별도 백업/실제 migration 적용 이력 확인, 기존 공급업체 명시 연결, 규격/세금 기준 합의, 발표 환경에서 최종 수동 검증. 승인을 받은 배포 단계에서만 수행한다.


## 7. 변경 파일과 이유

| 파일 | 이유 |
|---|---|
| `MERGE_REPORT.md` | 통합 결정·기능 보존·검증·보류 사항 기록 |
| `PROJECT_ARCHITECTURE.md` | 통합 결정·기능 보존·검증·보류 사항 기록 |
| `docs/analysis/FUNCTIONAL_TEST_REPORT.md` | 통합 결정·기능 보존·검증·보류 사항 기록 |
| `docs/analysis/IMPLEMENTATION_PLAN.md` | 통합 결정·기능 보존·검증·보류 사항 기록 |
| `docs/analysis/KANGHOON2_MERGE_REPORT.md` | 통합 결정·기능 보존·검증·보류 사항 기록 |
| `docs/analysis/REMAINING_ISSUES.md` | 통합 결정·기능 보존·검증·보류 사항 기록 |
| `docs/analysis/REQUIREMENT_TRACEABILITY_MATRIX.md` | 통합 결정·기능 보존·검증·보류 사항 기록 |
| `forecasting/views.py` | 끼니별 예측 중복 방지/누락 재시도와 캘린더 상세 |
| `integration_tests/test_kanghoon2.py` | 업체·문서·품목 수정·예측 재시도 신규22개 회귀 |
| `integration_tests/test_requirements.py` | 고정10월 식단과 현재 만료일이 섞이는 회귀 fixture 보정 |
| `inventory/management/commands/fix_ingredient_categories.py` | 팀원 관리 명령 파일 보존. 데이터 변경 명령은 실행하지 않음 |
| `inventory/urls.py` | 기존 경로/수불 유지, 품목 수정과 기간 조회·월 쿼리 호환 |
| `inventory/views.py` | 기존 경로/수불 유지, 품목 수정과 기간 조회·월 쿼리 호환 |
| `inventory/views_new_docs.py` | 기존 경로/수불 유지, 품목 수정과 기간 조회·월 쿼리 호환 |
| `meals/views.py` | 기존 메뉴 생성·단위 계산 유지, 등록 메뉴 context/표시 정밀도 보완 |
| `meals/views_new_docs.py` | 기존 메뉴 생성·단위 계산 유지, 등록 메뉴 context/표시 정밀도 보완 |
| `procurement/management/__init__.py` | 팀원 관리 명령 파일 보존. 데이터 변경 명령은 실행하지 않음 |
| `procurement/management/commands/__init__.py` | 팀원 관리 명령 파일 보존. 데이터 변경 명령은 실행하지 않음 |
| `procurement/management/commands/seed_workflow_test.py` | 팀원 관리 명령 파일 보존. 데이터 변경 명령은 실행하지 않음 |
| `procurement/migrations/0005_supplier.py` | 원본 Supplier 생성 migration 보존 및 기존 workflow와 병합 노드 연결 |
| `procurement/migrations/0009_merge_supplier_workflow.py` | 원본 Supplier 생성 migration 보존 및 기존 workflow와 병합 노드 연결 |
| `procurement/models.py` | 기존 User/FK 유지하며 연락처 Supplier 모델 추가 |
| `procurement/supplier_views.py` | 조회 무변경·명시 계정 연결·관리자 변경·검증·이력 보존 |
| `procurement/team_document_views.py` | 기존 cooking 계산 재사용과 단위/날짜 안전한 월간 집계 |
| `procurement/urls.py` | 기존 URL 보존하고 독립 업체/문서 View 연결 |
| `procurement/utils.py` | 명시 규격으로만 환산; 자유문자/질량-부피 추정 배제 |
| `static/css/sp_final.css` | 팀원 UI/인쇄 스타일 개선 보존 |
| `templates/docs/daily_inspection_report.html` | 팀원 검수 문서 헤더 서식 반영, 기존 계산 보존 |
| `templates/docs/doc_cooking_instruction.html` | 새 기간 양식과 저장 비고·경고·기존 편집/Excel 연결 |
| `templates/docs/doc_inspection_log.html` | 팀원 검수 문서 헤더 서식 반영, 기존 계산 보존 |
| `templates/docs/doc_inventory_status.html` | 기간 입력 양식 반영 |
| `templates/docs/doc_monthly_settlement.html` | 새 월간 양식의 샘플 값/일괄 세율 제거와 단위별 실제 집계 |
| `templates/docs/index.html` | 기존 메뉴 보존 + 업체/기간 조리지시서/월간 문서 탐색 연결 |
| `templates/forecasting/prediction_calendar.html` | 끼니별 예측 정보 표시 |
| `templates/inventory/ingredient_form.html` | 실제 수정 URL/등록-수정 양식 연결 |
| `templates/inventory/ingredient_list.html` | 실제 수정 URL/등록-수정 양식 연결 |
| `templates/meals/mealplan_create.html` | 글자 확대/중복 입력 보완, 기존 이름 입력 기능 유지 |
| `templates/partials/top_nav.html` | 기존 메뉴 보존 + 업체/기간 조리지시서/월간 문서 탐색 연결 |
| `templates/procurement/supplier_list.html` | 팀원 업체 화면에 명시 계정 연결·권한 표시·인쇄·안전한 삭제 추가 |
| `templates/workflow/hub.html` | 기존 메뉴 보존 + 업체/기간 조리지시서/월간 문서 탐색 연결 |

검증 산출물 30개는 `verification/kanghoon2-20261104/`에 별도 보존했다. 위 표의 기존 파일은 현재 통합 브랜치에서만 변경했다.


최종 자원 정리: 이번 작업의 app/DB 컨테이너3개와 internal network, baseline archive 및 socket 디렉터리2개를 정리했다. mysql entrypoint가 socket 디렉터리 소유권을 바꿔 빈 디렉터리가 남았으므로, 그2개 경로만 마운트한 일회용 컨테이너로 소유권을 되돌린 뒤 빈 디렉터리만 제거했다. 결과는 verification/kanghoon2-20261104/cleanup.json에 기록했다. 기존 자원은 정리 대상이 아니었다.
