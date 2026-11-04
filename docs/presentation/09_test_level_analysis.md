# 식수센스(SNP) — 소프트웨어 테스트 레벨별 분석

조사일: 2026-10-19 / 브랜치: sprint-final / HEAD: a8d9fae 및 보존된 미커밋 변경.

이번 작업은 테스트 소스 AST, 실행 스크립트, 기존 로그·JSON을 읽은 조사다. 테스트·서버·DB·Docker·AI 추론을 새로 실행하지 않았고 코드/모델/기존 산출물을 수정하지 않았다. 새 결과는 이 문서·10번 요약·CSV뿐이다.

## 1. 집계 단위와 조사 범위

**발견 항목125개 = Django 테스트 메서드117 + Node 테스트4 + 실제 브라우저 시나리오4.** 이 중123개는 저장소 안의 파일에 정의되어 있고,2개는 발표 준비 당시 /tmp에 만든 스크립트이며 이번에 해당 코드도 읽을 수 있었다. 마지막2개는 Git 관리 테스트가 아니고 재현성에 제약이 있어 별도 표시한다.

- Django 메서드1개를1케이스로 센다. subTest, for-loop 데이터, 여러 assert, 여러 URL, 조·중·석식 반복을 각각 별도 케이스로 늘리지 않는다.
- JS의 `test(...)` 등록1개를1케이스로 센다. 테스트 파일1개를4개 대신1개로 세거나, Django117 안에 넣지 않는다.
- 브라우저 IIFE 스크립트의 완결 시나리오1개를1개로 센다. 화면·단계·스크린샷 수는 케이스 수가 아니다. 서로 유사한 업무를 반복하는 시나리오도 있으므로125개가 독립 요구사항125개라는 뜻은 아니다.
- 요구사항에 맞춰 개발자가 작성한 시험과 실제 영양사가 수행/승인한 인수시험을 구분한다. 사용자가 제공한 Excel로 구조를 비교했다는 이유만으로 Acceptance가 되지는 않는다.
- `scripts/verify_integration.sh`는 환경 준비/검사와 테스트 실행을 묶는 **하네스**다. 스크립트1개·migration1개·check1회를 위 케이스 수에 더하지 않는다.

## 2. 대표 레벨 판정 기준

| 레벨 | 이번 조사에서의 기준 | 실제 배정 |
|---|---|---|
| Unit | DB·View·UI 없이 독립 계산 함수의 입력/반환값 검증 | calculateSmartOrderQuantities의 Node4개 |
| Integration | View/폼/서비스/ORM/DB 또는 실제 artifact·loader·모델 등 구성요소 계약 연결 | Django117개 |
| System | 실제 Chromium이 화면·JS·폼·서버·DB·다운로드를 잇는 사용자 관점 시나리오 | 브라우저4개 |
| Acceptance | 실제 영양사/권한 있는 사용자 참여, 사전 인수 기준, 실제 수행·판정/승인 기록 | 확인된 케이스0개. 통과0개 |

### 모호한 사례와 분류 이유

1. `test_explicit_mass_conversion_and_seven_can_example`은 convert 단언뿐 아니라 DB fixture→식수 확정→계획 저장→ORM 조회를 함께 수행한다. 한 메서드를 쪼개지 않고 Integration에만 배정했다.
2. 조리지시서의 `test_zero_is_valid`, `test_confirmed_count_units_and_explicit_package`도 cooking_sheet가 실제 식단/레시피/규격을 ORM으로 읽는다. ‘계산’이라는 제목만 보고 Unit으로 세지 않았다.
3. `test_three_persisted_estimators_load_and_predict`는 DB는 쓰지 않지만 실제 pkl·joblib loader·저장 estimator·pandas 입력의 호환성을 연결한다. 이 기준에서는 Integration이다. 순수 모델 단위 시험으로 분류하는 다른 기준과 혼동하지 않도록 명시한다.
4. `test_preserved_release_patch_routes`는 DB fixture를 실제로 쓰지 않아도 URL registry의 reverse/resolve와 View 연결을 검증하는 구성 통합 계약이다. `test_migration_graph_has_no_conflicts`는 MigrationExecutor/DB 적용 이력/loader를 연결한다.
5. `test_complete_ui_headcount_snapshot_order_inspection_usage_flow`는 넓은 업무 흐름이지만 Django client로 HTTP/ORM을 호출하고 실제 브라우저·JS를 실행하지 않아 Integration이다.
6. 이름이 RequirementWorkflows이거나 실무 원본 비교를 하더라도 개발자 자동화이므로 Acceptance로 중복 배정하지 않는다.

Python에 독립 Unit이0개라는 분류는 계산 로직 검증 자체가 없다는 뜻이 아니다. 현재 계산 검증의 상당 부분이 DB 통합 메서드에 포함되어 있다.

## 3. 전체 수와 실제 결과

### 3.1 통합 집계(임시 코드2개를 명시적으로 포함)

| 테스트 레벨 | 테스트 케이스 수 | 통과 | 실패 | 미실행 | 대표 테스트 |
|---|---:|---:|---:|---:|---|
| Unit | 4 | 4 | 0 | 0 | JS-U-01 안전재고 예약 |
| Integration | 117 | 117 | 0 | 0 | DJ-AI-02, DJ-REQ-08, DJ-REQ-20 |
| System | 4 | 4 | 0 | 0 | SYS-01~04; 저장소2＋임시2 |
| Acceptance | 0 | 0 | 0 | 0* | 영양사 실제 인수 증거 없음 |
| 합계 | **125** | **125** | **0** | **0** | 실행 정의/로그를 연결한 조사 항목 수 |

\* Acceptance 행의 미실행0은 **이미 정의된 실행 케이스가0**이기 때문이다. 인수 검증이 필요 없거나 이미 완료됐다는 뜻이 아니다. 영양사 UAT는 ‘미실시/증거 없음’ 영역으로 별도 남긴다. 현재 코드로 식별한125항목은 성공 기록과 연결됐지만, 식별되지 않은 요구사항·부하·인수 시험까지 모두 통과했다는 뜻도 아니다.

Git 저장소 안의 코드만 집계하면 Unit4＋Integration117＋System2=**123개**다. /tmp SYS-03/04를 제외한 숫자이며 두 기준을 발표 중 섞지 않는다.

### 3.2 환경별 중복 실행 구분

| 집합 | 코드에서 확인 | 선택한 최종 로그의 결과 | 다른 집합과 관계 |
|---|---:|---|---|
| Django | 117메서드 | SQLite117/117, MariaDB117/117 | 같은117개를 DB2종에서 실행.234개 독립 테스트가 아님 |
| 조리지시서 | 16메서드 | 두 DB 모두16개 이름과ok 확인 | **위117에 포함**.117＋16 금지 |
| JavaScript | 4등록 |4pass/0fail | Unit4이며 Django117 바깥. Unit표에 이미 포함 |
| 저장소 브라우저 | 2스크립트 |2개 성공JSON＋PASS로그 | System4 중2개 |
| 임시 브라우저 | 2스크립트 |주 시나리오와보충 모두 성공 | System4 중2개. 브라우저 단계/이미지 수는 미가산 |

### 3.3 Django 파일별 조사 결과

| 파일 | 메서드 수 | 대표 레벨 | 기존 실행 대조 |
|---|---:|---|---|
| `integration_tests/test_ai.py` | 2 | Integration | SQLite 2/2, MariaDB 2/2 |
| `integration_tests/test_cooking.py` | 16 | Integration | SQLite 16/16, MariaDB 16/16 |
| `integration_tests/test_migrations.py` | 1 | Integration | SQLite 1/1, MariaDB 1/1 |
| `integration_tests/test_requirements.py` | 53 | Integration | SQLite 53/53, MariaDB 53/53 |
| `integration_tests/test_workflows.py` | 31 | Integration | SQLite 31/31, MariaDB 31/31 |
| `meals/tests.py` | 10 | Integration | SQLite 10/10, MariaDB 10/10 |
| `procurement/tests.py` | 4 | Integration | SQLite 4/4, MariaDB 4/4 |
| 합계 | **117** | Integration | 동일 이름117개가양쪽 로그에 모두 존재 |

accounts/tests.py, forecasting/tests.py, inventory/tests.py에는 import와 생성 안내 주석만 있고 test_ 메서드는0개다. 이것을 미실행3개로 세지 않는다. 해당 앱의 인증·예측·재고 시험은 integration_tests에 존재하므로 앱 전체가 무시험이라고 단정하지도 않는다. config/test_settings.py와 test_mysql_settings.py는 실행 설정이지 테스트 메서드가 아니다.

## 4. 각 테스트의 상세 인벤토리

[test_case_inventory.csv](test_case_inventory.csv)에125행을1케이스1행으로 기록했다. UTF-8 BOM CSV이며 줄바꿈이 있는 코드 발췌가 셀 안에 들어 있으므로 물리적 파일 줄 수로 행 수를 세면 안 된다.

| CSV 열 | 내용 |
|---|---|
| test_id / representative_level / source_scope | 고유 ID, 대표 레벨1개, repository 또는temporary_source |
| file / class_name / function / source_line | 파일·클래스·메서드와 현재 소스 줄 번호 |
| purpose | 실제 메서드가 확인하는 목적. 메서드명보다 좁은 assert 한계를 별도 기록 |
| input_conditions | 공통 fixture 설명＋정적 메서드 입력/조작 코드. **이 코드를 실행한 것이 아님** |
| expected_result / major_assertions | 실제 assert의 기대값/예외 및 원문. 새 기대값을 만들어 채우지 않음 |
| environment | 실제 기록의 DB·이미지·브라우저 등. Node와브라우저는Django117과 별도 |
| latest_evidenced_result / sqlite_result / mariadb_result | 선택한 기존 실행 증거와 연결한 상태. 플랫폼이 해당 없으면N/A |
| execution_logs | 정확한 로그 파일·테스트 시작/ok 줄 또는브라우저 JSON/PASS로그 |
| classification_reason / limitations | 각 케이스의 레벨 판단 이유 및 미검증 범위 |

### 하네스·보조 파일(케이스 수에 미가산)

- `scripts/verify_integration.sh`: offline wheels를 임시 /tmp에만 설치→check→makemigrations --check --dry-run→migrate→migrate --check→showmigrations→manage.py test. `--network none --read-only --tmpfs /tmp`, 소스/wheels 읽기 전용. MariaDB는전용 소켓 설정.
- `integration_tests/seed_browser.py`, `seed_readiness.py`: 임시 데이터/계정 준비. 환경 보호 assert는 있지만 개별 소프트웨어 동작을 판정하는 등록 테스트가 아님.
- `scripts/prepare_integration_wheels.py`, `audit_integration_environment.py`: 의존성/환경 증거 준비 도구, 독립 케이스로 세지 않음.
- `verification/environment/model-compatibility.log`: Conda에서3개 artifact의smoke 결과/버전 경고가 있으나 별도 보존된 등록 테스트 메서드가 아닌 실행 증거. 조·중·석식3번을 새3케이스로 더하지 않음.

## 5. 브라우저 System 시나리오별 근거

| ID | 소스·목적 | 입력/주요 단언 | 실제 결과·로그 | 집계/한계 |
|---|---|---|---|---|
| SYS-01 | integration_tests/browser_workflow.cjs, 단일재료 거래 |351명·100g,8→9캔,45납품/40합격,4500원·4.9kg·pageerrors0 |verification/requirements/browser.json와browser.log 성공 |JSON11단계=1시나리오.4.9는body텍스트 단언. JSON의FIFO lot 문구만으로lot배정 순서를 입증하지 않음 |
| SYS-02 | integration_tests/browser_cooking.cjs, 조리지시서 |351→352명,35.1→35.2kg,비고보존·다운로드·print호출/CSS·PDF |verification/cooking-format/browser.json와browser.log 성공 |8단계=1시나리오. 실제 프린터/모든 Excel셀의 완전 일치 검증 아님 |
| SYS-03 | /tmp/snp-finalprep-wisanw0k/demo/capture.cjs, 발표용 전체흐름 |실제AI133·수동360·최종351,업체2건,입고전0,합격40/36,중복검수40유지,잔량4.9/14.9/0.9,문서저장후원장동일 |docs/presentation/demo_artifacts/browser_result.json와browser.log 성공 |13체크포인트·12캡처=1시나리오. /tmp 코드·중간 상태에 의존,Git 미관리 |
| SYS-04 | /tmp/snp-finalprep-wisanw0k/demo/supplement.cjs, 보충 |선택날짜메뉴,주기간10/19~25의쌀기초50/입고0/기말14.9,인쇄화면캡처 |docs/presentation/demo_artifacts/supplement.json와supplement.log 성공 |3PNG=1후속시나리오.독립초기화/인쇄실물 검증 아님 |

/tmp 파일은 이번 조사 시 실제로 존재해 읽었다. 향후 /tmp 정리 후에는 이 두 시나리오의 로그는 남아도 소스가 사라질 수 있다. 코드를 저장소로 옮기거나 재실행하지 않았다. 이 제약 때문에 보수적 발표 집계는 저장소System2＋임시보충2처럼 분리 표기한다.

## 6. 선택한 로그와 과거 실패 기록

### 현재 코드의 케이스 이름과 대조한 기준 로그

- [SQLite](../../verification/cooking-format/sqlite.log):117개의 test_name(Class.method)와각ok 확인, Ran117/OK,8.562초.
- [MariaDB](../../verification/cooking-format/mariadb.log):동일117개와각ok 확인, Ran117/OK,9.854초.
- [Node 직접 실행](../../verification/feedback/javascript-direct.log):명명된4개의Subtest와pass4/fail0 확인.
- [System01](../../verification/requirements/browser.json), [System02](../../verification/cooking-format/browser.json), [System03](demo_artifacts/browser_result.json), [System04](demo_artifacts/supplement.json):각passed=true및대응PASS로그.

AI·오류 주입 테스트는 실행 중 메시지/RuntimeError traceback이 출력된 뒤 해당 케이스가ok로 끝난다. traceback 단어만으로ERROR로 분류하지 않고 **케이스별종료 상태와전체summary**를 함께 읽었다. 반대로 이름만 등장하고ok가 없으면 성공으로 처리하지 않는 방식으로 대조했다.

### 과거 실행 이력(현재 집계에 누적하지 않음)

| 로그 | 기록된 summary | 해석 |
|---|---|---|
| verification/tests-initial.log |Ran37,FAILED(failures8,errors2) |초기 통합의실패 이력. 같은 개발 과정의과거 버전이며 현재125개에 실패10개를 더하지 않음 |
| verification/tests-second.log |Ran45,FAILED(failures3) |후속 오류 수정 전 기록 |
| verification/sqlite-final.log, mariadb-final.log |각48/OK |초기 통합 최종 기록 |
| verification/requirements/sqlite.log, mariadb.log |각101/OK |문서기반 업무 보완 기록 |
| verification/feedback/*-recheck.log |각113/OK |조리지시서초기12개와수불fixture 보정 후 |
| verification/cooking-format/{sqlite,mariadb}.log |각117/OK |실제 양식 비교4개 추가 후의기준 |
| verification/final-readiness/sqlite-baseline.log |117/OK |추가baseline실행.117개를 새로 가산하지 않음 |
| verification/environment/*-attempt.log |Django부재/Docker접근거부 등 |환경 시작 실패여서 실행된 테스트0. 최종해당케이스 성공로그와구분 |
| verification/feedback/javascript.log |파일단위1pass |이 기록을4세부케이스 증거로 사용하지 않고 직접실행4개 로그를채택 |

발표 준비 SYS-03에는 처음 대시보드 헤더가 이름을 보일 것으로 가정해 검증 스크립트가 실패한 시도가 있다. 실제는 계정ID 표시였고 스크립트를 맞춘 후 전체 성공했다. `demo_artifacts/failure.png`는 진단 기록이며 최종 성공 증거로 사용하지 않았다. 현재의실패0은 **선택한 최종 케이스 결과 기준**이고 실패한 역사가 없다는 뜻은 아니다.

## 7. PPT 대표 사례8개

대표사례는 인벤토리의기존 케이스를 설명용으로 선정한 것이다. 사례6은기존2개를 함께 설명하므로 사례8개=새테스트8개로 더하지 않는다.

### 사례1. 실제 모델 추론 결과의 DB 저장 — DJ-AI-02

- 레벨: Integration.
- 입력:2026-10-15,조·중·석식,‘쌀밥 미역국 제육볶음’ 메뉴문자,실제저장모델/CSV전처리.
- 기대 결과:각예측의pk가있고predicted_count≥0,입력feature_columns가있음.
- 주요 assertion:`assertIsNotNone(prediction.pk)`, `assertGreaterEqual(...,0)`, `assertTrue(input_features['feature_columns'])`.
- 실제 결과:양DB에서해당메서드ok.세끼니반복은1케이스.오프라인SBERTfallback이며정확도평가는아님.
- 테스트 코드:`integration_tests/test_ai.py:PredictionCompatibilityTests.test_offline_prediction_pipeline_persists_three_meals`.
- 실행 로그:SQLite L169~222, MariaDB L124~178(위기준로그).
- PPT 설명:“저장 모델과 전처리를 실제 연결하여 예측 결과·입력 특성이DB에 저장되는지 확인했습니다.”

### 사례2. AI와 구분한 영양사 최종 식수 — DJ-REQ-05

- 레벨: Integration.
- 입력:AI999명,수동300명,최종350명.
- 기대 결과:`get_serving_count(plan)[0] == 350`.
- 주요 assertion:`assertEqual(get_serving_count(self.plan)[0],350)`.
- 실제 결과:양DB에서ok.모델을더정확하게만드는시험이아니라업무기준선택검증.
- 테스트 코드:`integration_tests/test_requirements.py:RequirementWorkflows.test_final_confirmation_overrides_ai`.
- 실행 로그:SQLite L327, MariaDB L282.
- PPT 설명:“AI값을 그대로 발주에 쓰지 않고 영양사가 확정한 식수를 사용하는지 검증했습니다.”

### 사례3. 필요량·규격 올림·사용자 조정 저장 — DJ-REQ-08

- 레벨: Integration.
- 입력:최종351명,100g/인,명시5kg/캔,500원/캔,사용자9캔조정.
- 기대 결과:35.1kg의최소8캔,조정후package_quantity9/required_qty45kg/estimated_price4500원,규격스냅샷보존.
- 주요 assertion:`line.package_quantity==8`, `(item.package_quantity,item.required_qty,item.estimated_price)==(9,45,4500)`.
- 실제 결과:양DB에서ok. 5kg/캔등록조건으로만성립한다.
- 테스트 코드:`...test_requirements.py:RequirementWorkflows.test_round_up_and_manual_adjustment_snapshot`.
- 실행 로그:SQLite L372, MariaDB L327.
- PPT 설명:“1인량×식수에서 실제 포장수로 올림한 뒤,수량 조정과 금액까지 저장되는지 확인했습니다.”

### 사례4. 업체별 발주 분리 — DJ-REQ-38

- 레벨: Integration.
- 입력:참치와쌀이서로다른업체·명시규격에연결된350명식단.업체식별자의문자순서와업체명의순서가다름.
- 기대 결과:주문2건생성,검수HTML에서가업체가하업체앞.
- 주요 assertion:`len(orders)==2`, `text.index('가업체') < text.index('하업체')`.
- 실제 결과:양DB에서ok.후자는전체HTML문자위치비교여서테이블행정렬을개별추출한시험으로과장하지않음.
- 테스트 코드:`...test_requirements.py:RequirementWorkflows.test_two_suppliers_split_orders_and_sort_by_real_name`.
- 실행 로그:SQLite L377, MariaDB L332.
- PPT 설명:“동일 계획에서 공급업체별 주문이 분리되는지 검증했습니다.”

### 사례5. 합격량만 입고·중복 검수 방지 — DJ-REQ-20

- 레벨: Integration.
- 입력:40kg납품/35kg합격/5kg품질불량,같은검수를2회요청.
- 기대 결과:같은검수pk,현재고35kg,원장1개,발주완료상태.
- 주요 assertion:`first.pk==second.pk`, `current_stock==35`, `InventoryLog.count()==1`.
- 실제 결과:양DB에서ok.브라우저시연의45/40kg예와는다른고정테스트데이터다.순차재전송이며동시부하아님.
- 테스트 코드:`...test_requirements.py:RequirementWorkflows.test_inspection_partial_acceptance_and_duplicate_receipt`.
- 실행 로그:SQLite L331, MariaDB L286.
- PPT 설명:“합격량만 재고에 반영하고 같은 검수 요청을 반복해도입고가중복되지않는지 확인했습니다.”

### 사례6. FIFO 배정과 주간 원장 계산 — DJ-REQ-33＋DJ-REQ-28

- 레벨: Integration(서로다른기존2케이스를한슬라이드에설명).
- 입력:FIFO는과거입고3kg＋나중입고4kg에서5kg출고.수불은이전기초10,기간입고2,폐기1,서울·UTC경계시각.
- 기대 결과:FIFO배정[3,2]·lot잔량[0,2].주간(기초,입고,폐기,기말)=(10,2,1,11),서울전일조회는(10,0,0,10).
- 주요 assertion:`out.lot_allocations... == [Decimal('3'),Decimal('2')]`, `remaining_quantity==0/2`, 원장4값tuple단언.
- 실제 결과:양DB에서두메서드모두ok.기존lot미대사자료까지검증했다는뜻아님.
- 테스트 코드:`...test_requirements.py:test_fifo_allocates_oldest_receipt_and_tracks_expiry`, `test_weekly_ledger_opening_waste_adjustment_and_closing`.
- 실행 로그:FIFO SQLite L326/MariaDB L281,수불SQLite L378/MariaDB L333.
- PPT 설명:“먼저 입고한 재고부터 배정하고,기간별입출고가잔량과일치하는지 확인했습니다.”

### 사례7. 조리지시서 Excel·수식 삽입 방어 — DJ-COOK-10

- 레벨: Integration.
- 입력:확정350명·100g/인·5kg/통,지시문자열‘=1+1’,ExcelGET.
- 기대 결과:주문서E3='35 kg',계산근거G2=35/I2=7,모든주문서셀에실행수식없음,세로페이지.
- 주요 assertion:`ws['E3']=='35 kg'`, `calc['G2']==35`, `calc['I2']==7`, `not any(c.data_type=='f')`.
- 실제 결과:양DB에서ok.원본서식비교DJ-COOK-13은같은16개묶음에있으며별도기존케이스다.
- 테스트 코드:`integration_tests/test_cooking.py:CookingInstructionsTest.test_excel_numeric_total_and_literal_formula_text`.
- 실행 로그:SQLite L230, MariaDB L185.
- PPT 설명:“실제로 내려받은Excel을다시열어총량·포장환산을확인하고입력문자열이수식으로실행되지않게검증했습니다.”

### 사례8. 익명·공급업체의 업무 접근 제한 — DJ-COOK-12

- 레벨: Integration.
- 입력:비직원SUPPLIER계정과익명.목록·날짜별XLSX·상세·상세XLSX의GET및POST수정.
- 기대 결과:공급업체403,익명302,문서/재고원장생성없음.
- 주요 assertion:`response.status_code == 403/302`, `not CookingInstruction.exists()`, `not InventoryLog.exists()`.
- 실제 결과:양DB에서ok.일반HTTP계정이름에supplier가있다는이유가아니라role을명시한fixture로확인했다.
- 테스트 코드:`...test_cooking.py:CookingInstructionsTest.test_supplier_and_anonymous_access_denied`.
- 실행 로그:SQLite L241, MariaDB L196.
- PPT 설명:“역할별로조회·수정·다운로드가제한되는지확인했습니다.전체보안인증을완료했다는뜻은아닙니다.”

## 8. 비기능 테스트 조사

| 분야 | 실제 코드·기존 증거 | 판정 | 발표 한계·추가 확인 |
|---|---|---|---|
| 성능 |117개실행시간8.562/9.854초,단일브라우저시간기록은있음 |**전용 성능시험 증거 없음** |테스트실행시간은응답시간SLA/throughput/p95측정아님.성능향상수치로쓰지않음 |
| 부하 |중복요청·행잠금코드·순차stale revision시험 |**동시 부하 미실시/증거 없음** |동시사용자·요청경합·장애복구·내구성시험없음 |
| 보안 |권한/인증·잘못된입력·수식문자셀·업무변경부작용assert |**제한적 자동 검증 있음** |SQLi/XSS/CSRF전체·취약점스캔·침투·세션/가입정책·인프라보안전반을검증한것아님 |
| 사용성 |개발자브라우저조작·캡처·printCSS·PDF열람 |**개발자 점검 있음,사용자 실험 증거 없음** |영양사과제완료율/소요시간·SUS·관찰/설문·접근성·모바일인수없음 |
| 호환성 |SQLite/MariaDB동일117,CSV인코딩·XLS/XLSX/XLTX,저장모델로드,Chromium |**범위 한정 검증 있음** |다른브라우저·OS/기기·실Excel/LibreOffice인쇄·프린터·정상SBERT·모든AI버전은미확인.별도Conda로그는sklearn버전경고존재 |
| 데이터 무결성 |migration보존·단위/수량·원장·검수·중복·FIFO·UUID·revision |**자동 검증 있음** |실운영데이터전수대사·과거lot·동시성·정전/rollback복구·분할납품정책전체와다름 |
| 회귀 |48→101→113→117로그,기존업로드/URL/보고서·예외추가 |**반복 회귀 증거 있음** |버전별다른모음의누적수로성공수를부풀리지않음.현재코드커버리지%측정자료는없음 |
| 실제 사용자 인수 |요구사항/피드백/실제양식은있으나영양사실행·승인결과없음 |**Acceptance완료 증거 없음** |기준·테스트데이터·참여자·수행일·실제결과·승인/보류기록확보필요 |

## 9. 현재 결과를 발표할 때 지켜야 할 범위

- ‘기존 실행 로그와 소스의 테스트 이름을 대조한 결과’라고 표시한다. 이번 조사가 새로운실행통과를만든것은아니다.
- 테스트 로그 대부분이 소스 전체해시/이미지불변ID와완전히결합되어있지않다. 이름·본문과자료가대응하지만현재미커밋트리를새로검증했다는보증은아니다.
- 최신 코드의공식적재현성에는미커밋정리·임시브라우저스크립트관리·정확한환경/데이터/아티팩트식별이필요하다. 이번조사에서는어느것도변경하지않았다.
- 이후 우선 검증:실제영양사UAT,정상SBERT및시간분리예측평가,실제동시검수/출고경합,다브라우저/실프린터,성능부하.현재근거로통과숫자를만들지않는다.
