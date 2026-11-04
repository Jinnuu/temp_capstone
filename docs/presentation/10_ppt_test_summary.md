# 식수센스(SNP) — PPT용 테스트 결과

조사일: 2026-10-19. 기존 코드·로그 분석 결과이며 이번 작업에서는 테스트를 새로 실행하지 않았다. 상세 근거는 [09_test_level_analysis.md](09_test_level_analysis.md), 개별 입력·단언·실행 위치는 [test_case_inventory.csv](test_case_inventory.csv)를 참조한다.

## A. 본 발표용 1장

### 슬라이드 제목: 계산부터 검수·재고까지, 업무 연결을 검증했습니다

| 대표 테스트 레벨 | 확인한 케이스 | 기존 최종 성공 기록 |
|---|---:|---:|
| Unit | 4 | 4 |
| Integration | 117 | 117 |
| System | 4* | 4 |
| Acceptance | 0 | 실제 영양사 인수 증거 없음 |

**Django 동일 117개를 SQLite·MariaDB에서 각각 117/117 통과. JavaScript 계산 4개와 Chromium 시나리오 4개도 성공 기록 확인.**

- 식수: AI 예측 저장과 영양사 최종 확정값 우선 적용 검증.
- 발주: 351명 × 100g = 35.1kg → 명시적 5kg/통 규격으로 최소 8통, 사용자 조정 9통 저장 검증.
- 검수: 납품 40kg 중 합격 35kg만 입고, 같은 요청을 다시 보내도 추가 입고 없음.
- 조리지시서: 확정 식수에 따른 총량·포장 환산, Excel 출력과 수식 삽입 방어 검증.

**한계:** 실제 영양사 인수, 성능·부하 시험 증거 없음. 예측 정확도와 실제 프린터 출력은 이 결과로 보장하지 않음.

발표 설명: “단순 화면 접근뿐 아니라 식수·규격·합격량이 다음 단계의 데이터로 정확히 이어지는지 확인했습니다. 다만 실제 사용자 인수와 부하 검증은 별도 과제입니다.”

발표자 주석:

- *System 4개는 저장소 코드 2개와 임시 발표 검증 코드 2개. 임시 코드는 Git 관리 밖이므로 재현성 한계가 있다. 저장소 코드만 집계하면 System 2개, 전체 123개다. 임시 코드까지 포함한 조사 항목은 125개다.
- 브라우저 시나리오 하나의 여러 단계·이미지를 별도 테스트로 세지 않았다.
- SQLite/MariaDB 중복 실행을 합쳐 독립 234개라고 발표하지 않는다. 조리지시서 16개는 Django 117개에 포함되며 JavaScript 4개는 표의 Unit에 이미 포함된다.
- “125개 통과”보다 위 레벨·환경별 수치를 함께 제시한다. 요구사항 125개 완료나 시스템 무결함을 뜻하지 않는다.

## B. 부록 1장: 레벨별 상세 결과와 대표 사례 1~4

### 슬라이드 제목: 업무 데이터의 계산·저장·연결 검증

| 구분 | 코드에서 식별 | 기존 실행 결과 | 근거 |
|---|---:|---|---|
| Python Integration | 117 | SQLite 117통과 / 실패0, MariaDB 117통과 / 실패0 | cooking-format 두 DB 로그의 개별 이름·ok 대조 |
| JS Unit | 4 | 통과4 / 실패0 | javascript-direct.log의 tests4/pass4/fail0 |
| Chromium System | 저장소2 + 임시2 | 시나리오4 성공 | 각 스크립트와 JSON/PASS 기록 대조 |
| 실제 사용자 Acceptance | 확인0 | 승인 증거 없음 | 개발자 요구사항 시험을 UAT로 계산하지 않음 |

| 사례 / 레벨 | 입력 → 기대 결과 | 기존 실제 결과 | 테스트 코드 / 로그 |
|---|---|---|---|
| 1. AI 예측 저장 / Integration | 날짜·조중석 메뉴 → 식사별 예측 저장, 음수 없는 식수·입력 feature 기록 | PASS. 기존 오프라인 파이프라인 범위 | test_ai.py: test_offline_prediction_pipeline_persists_three_meals / 두 DB 로그 |
| 2. 최종 식수 우선 / Integration | AI999·직접300·확정350 → 업무 계산에는350 | PASS | test_requirements.py: test_final_confirmation_overrides_ai / 두 DB 로그 |
| 3. 포장규격 환산·조정 / Integration | 35.1kg·5kg/통 → 최소8통,9통 조정 →45kg·4,500원 저장 | PASS | test_requirements.py: test_round_up_and_manual_adjustment_snapshot / 두 DB 로그 |
| 4. 업체별 발주 분리 / Integration | 서로 다른 업체의 품목2개 → 발주2건, 업체명 순서 확인 | PASS. 정렬 단언은 HTML 문자열 위치 비교 | test_requirements.py: test_two_suppliers_split_orders_and_sort_by_real_name / 두 DB 로그 |

코드 기본 경로: `integration_tests/`. 두 DB 로그: `verification/cooking-format/sqlite.log`, `verification/cooking-format/mariadb.log`.

AI 설명 주의: 기존 저장 모델 호환성·추론·저장 및 오프라인 fallback 검증이다. 최신 Optuna 연구 모델의 웹 통합, 정상 SBERT 온라인 경로 전체, 예측 정확도 개선을 입증하는 시험이 아니다.

## C. 부록 2장: 대표 사례 5~8와 남은 검증

### 슬라이드 제목: 재고 정합성과 출력·권한 검증, 그리고 한계

| 사례 / 레벨 | 입력 → 기대 결과 | 기존 실제 결과 | 테스트 코드 |
|---|---|---|---|
| 5. 합격량 입고·중복 방지 / Integration | 납품40·합격35, 요청2회 → 재고35·로그1건 | PASS. 순차 재전송이며 동시 부하 시험 아님 | test_requirements.py: test_inspection_partial_acceptance_and_duplicate_receipt |
| 6. FIFO·주간 수불 / Integration | 오래된 lot3 + 새 lot4에서5 출고 →3+2 배분. 기초10+입고2−폐기1 →기말11 | 두 메서드 PASS. 시간대별 거래일 경계도 검증 | test_requirements.py: test_fifo_allocates_oldest_receipt_and_tracks_expiry; test_weekly_ledger_opening_waste_adjustment_and_closing |
| 7. 조리지시서 Excel / Integration | 350명×100g →35kg,5kg/통→7통; 비고에 =1+1 | PASS. 셀 값·세로 설정 확인, 수식 셀 없음 | test_cooking.py: test_excel_numeric_total_and_literal_formula_text |
| 8. 익명·공급업체 권한 / Integration | 조회·수정·Excel 요청 → 로그인 이동 또는403, 업무 데이터 생성 없음 | PASS. 전체 보안 진단을 뜻하지 않음 | test_cooking.py: test_supplier_and_anonymous_access_denied |

사례6은 기존 메서드2개를 묶어 설명한 것으로, 새로운 케이스를 더한 것이 아니다. 정확한 메서드명·위치는 CSV와 상세 분석의 대표 사례 절을 기준으로 확인한다.

| 비기능 영역 | 증거 기반 판정 |
|---|---|
| 성능·부하 | 미실시/증거 없음. 회귀 실행 시간은 성능 목표 충족 증거가 아님 |
| 보안 | 권한·수식 삽입 등 특정 경계 검증 있음. 전체 취약점 진단·침투 시험 증거 없음 |
| 사용성·인수 | 개발자 브라우저 흐름 검증 있음. 실제 영양사 참여·승인 기록 없음 |
| 호환성 | SQLite/MariaDB, 기존 모델 로드, Chromium 및 Excel 파일 구조 검증 있음. 다중 브라우저·실제 Excel/프린터 동작은 미보장 |
| 데이터 무결성 | 합격량 입고·중복 처리·FIFO·수불·수정 충돌 검증 있음. 병렬 경쟁 부하 시험은 없음 |
| 회귀 | 기존 최종 Django117×DB2종, JS4 및 브라우저 시나리오 기록 있음 |

실행 증거:

- Django: `verification/cooking-format/sqlite.log`, `verification/cooking-format/mariadb.log`.
- JS: `verification/feedback/javascript-direct.log`.
- 저장소 브라우저: `verification/requirements/browser.json`, `verification/cooking-format/browser.json` 및 각 browser.log.
- 임시 브라우저: `docs/presentation/demo_artifacts/browser_result.json`, `supplement.json`, `browser.log`, `supplement.log`. 소스는 `/tmp/snp-finalprep-wisanw0k/demo/`에 있으며 영구 보존되지 않을 수 있다.
- 원본 양식 비교와 출력 구조 검증은 실제 프린터 인쇄 품질이나 사용자 승인과 다르다.

발표 전 추가 확인 권장: 실제 영양사 인수 기준·승인 기록, 정상 AI 운영 경로와 정확도 근거, 동시 검수·수정 경쟁, 실제 발표 PC의 Excel·인쇄 호환성. 성능·부하 수치는 측정 없이 발표하지 않는다.
