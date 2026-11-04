# 영양사 피드백 후속 검증 (2026-10-16)

> 최신: 실제 Excel 전체6시트 분석, 양식 개선 후 SQLite/MariaDB 각각117개 및 실제 브라우저 검증 통과. 아래 마지막 절 참조.

> 이전 재검증: SQLite/MariaDB 전체 각각 113개 통과. 아래 마지막 「실제 테스트 실패 수정 및 격리 재검증」 절이 현재 결과이며 이전 미실행 기록은 이력이다.

작업 브랜치 integration/sprint7-kanghoon, 기준 a8d9fae. 과거 완료 표시는 제공받은 피드백을 그대로 기록하며 현행 완료 판정과 구분한다. 이번에는 소스/URL/템플릿 정적 확인을 수행했다. 기존 실행 증거는 verification/requirements이며, 신규 실행 증거는 verification/feedback이다. 이전 101개 테스트 통과를 이번 변경본의 통과로 주장하지 않는다.

| 번호 | 요구 / 과거 완료 표시 | 현재 확인한 구현·경로 | 이번 검증·판정 / 수정 |
|---|---|---|---|
| 1 | 업체현황 문서 / 예 | workflow/suppliers/ 관리 화면은 존재하나 전용 업체현황 문서 경로는 확인하지 못함 | PARTIAL. 관리 화면과 출력 문서는 다름. 필수 출력 열/양식 확인 후 구현 필요 |
| 2 | 식단 작성 글자 확대 / 예 | templates/meals/mealplan_create.html, weekly_mealplan_create.html 및 공통 CSS | UNVERIFIED. CSS 존재만으로 현업 가독성 완료 판정 불가. 실제 화면 비교 미실시; 수정 없음 |
| 3 | 발주예정서→검수일지 / 원문 미완성 | templates/workflow/plan.html의 발행 주문→workflow_inspections 링크; workflow.py:inspect_item | 기존 연결 보존. 이전 핵심 브라우저 검증 있음. 이번 실행 재검증 불가 |
| 4 | 조리지시서 / 별도 검증 | 신규 meals/cooking.py, cooking_views.py, CookingInstruction, meals/cooking/ 및 cooking/<pk>/ | UNVERIFIED. 신규 코드·12개 테스트 작성. Django 실행 못함. 참고 XLSX도 없음 |
| 5 | 업체별 구매발주서 명칭 / 예 | templates/docs/vendor_procurement_report.html 및 workflow/plan.html | 명칭 정적 확인, 기존 문서/출력 보존. 전체 Excel 명칭 재실행 미실시 |
| 6 | 카테고리 재분류 / 미표기 | workflow/categories/, IngredientCategory, 분류 정정 서비스 | 기존 category rename 테스트 존재. 실제 품목 오분류 대사는 영양사 확인 필요 |
| 7 | 실제 납품규격 환산 / 예 | SupplySpecification.base_quantity/base_unit/order_unit/order_increment, workflow.py | 기존 명시적 규격 계산 유지. 35kg / 5kg/통=7통은 신규 조리지시서 테스트에도 명시. 실행 미검증 |
| 8 | 만두 개별 중량·업체 기반 계산 / 미표기 | 공급업체별 포장 총중량과 레시피 질량 단위 사용 가능 | PARTIAL. 자유문자에서 개별 중량 추정 안 함. 1인분 개수→개당 중량→kg 변환은 별도 구조 미구현. g 기준 레시피는 명시 포장량으로 환산 |
| 9 | 검수일지 업체명 오름차순 / 예 | procurement/views_new_docs.py:doc_inspection_log order_by supplier__name | 기존 실제 이름 정렬 및 테스트 보존. 이번 재실행 불가 |
| 10 | 구입요구서 품목 묶음·분류 반복 제거 / 예 | views_new_docs.py 품목 집계·정렬 + doc_purchase_requisition.html regroup | 이전 category once 테스트 보존. 이번 출력 재실행 불가 |
| 11 | 요일·식사별 식수 / 예 | workflow 허브 날짜·끼니별 입력, save_headcount 및 최종 확정 | 기존 수동/AI/최종 구분 보존. 이번 변경 없음 |
| 12 | 주간 수불 / 미표기 | workflow/ledger/, workflow_views.py:ledger | 기존 주간 opening/waste/adjustment/closing 테스트 보존. 실제 DB 확인 안 함 |
| 13 | 김치·쌀 kg 선입고 / 미표기 | workflow/transactions/, record_inventory, convert | kg 원장 및 신규 lot 유지. 기존 lot 대사 미완료. 실제 품목 데이터는 조회/변경 안 함 |
| 14 | 식단조견표→발주예정서 / 예 | docs/index.html 기존 참고 양식 명칭 및 workflow/preview/ | 정적 명칭 확인. 레거시 참고 양식과 확정 발주예정서 구분 유지 |
| 15 | 날짜·식수·메뉴·재료·1인분·총량·비고, 초기 빈칸 / 예 | workflow/plan.html 7개 열, ?blank=1 모드 | PARTIAL. 빈 출력 모드는 존재하나 기본 화면은 확정 식수를 표시함. 초기 빈칸은 인쇄 양식인지 업무 입력 화면인지 현업 확인 필요. 계산에 쓰는 확정값은 지우지 않음 |

## 조리지시서 설계와 양식 제약

`docs/reference/(8.7~8.9)조리지시서.xlsx`는 이번에도 존재하지 않았다(디렉터리 직접 열람). 시트/셀/병합/행열 크기/인쇄영역/그림은 분석 불가이며 어떤 셀 구조도 추정하지 않았다. 신규 Excel은 요구 항목을 담은 기본 A4 가로형이며 제공 양식과 유사하다고 판정하지 않는다.

기존 weekly_recipe_report는 GET 공통 인원(기본 100)을 사용하는 별도 참고 문서다. 새 조리지시서는 이를 호출하지 않고 식단의 최종 확정 식수만 사용한다. 0명은 0, 미확정은 총량 계산 불가. 메뉴별 조리 정보와 문서별 현장/재고 사용 지시를 표시한다. 동일 재료가 여러 메뉴에 있으면 메뉴별 행을 유지한다.

명시된 재료 기준 단위로 환산한 총량과 공급업체별 포장 내용량을 이용한 **사용 포장 환산량**을 표시한다. 발주 올림량과 다르므로 35.1kg / 5kg은 7.02통이다. 발주는 기존 서비스에서 8통 등 올림 처리한다. 규격이 없으면 계산 가능한 총량은 유지하되 포장 환산을 경고한다. 재고 사용 지시 저장은 출고를 만들지 않는다. 실제 차감은 기존 업무로 처리한다.

현장 지시사항은 식단별 저장, 버전 확인으로 상충 저장 거부. 총량은 조회 때 재계산하므로 문서는 발행 당시 동결 이력 문서가 아니다. 변경 후 재인쇄 시 현재값임을 표시한다. Excel은 입력 문자열을 문자 셀로 기록해 수식으로 실행되지 않도록 한다.

## 실행 결과

- `node integration_tests/smart_order.test.cjs`: **4개 통과**, verification/feedback/javascript-direct.log.
- `node --test integration_tests/smart_order.test.cjs`: 파일 단위 1개 통과로 보고되어 별도 직접 실행의 4개 결과를 기록함.
- Python AST 파싱: 신규/변경 Python 6개 문법 검사 통과. Django 동작 검증을 대체하지 않음.
- `bash scripts/verify_integration.sh`: **실행 실패**, Docker socket 접근 거부. Django check, migration, 신규 12개 테스트, 기존 전체 회귀는 이번에 실행하지 못함.
- 로컬 Python에도 Django가 없어 대체 실행 불가. /tmp로 의존성 다운로드를 시도했으나 Django 6.0.3을 확보하지 못함. 프로젝트 패키지 버전은 변경하지 않음.
- 신규 UI 브라우저·Excel 열기/인쇄·MariaDB 동시성 검증 미실시.


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


## 2026-10-16 실제 Excel 양식 분석 및 개선 — 최신 결과

원본 `(8.7~8.9)조리지시서.xlsx`를 확인하고 모든 시트·비어 있지 않은 셀·스타일·병합·열 너비·행 높이·인쇄 설정을 openpyxl로 조사했다. 파일 SHA-256은 `edbb8fcdbd7e6030b9aced075ef6035f3ca350c372f6fa0a35b473cfa2d003c7`이며 작업 후 동일하다. 상세 좌표/값/캐시값/서식/스타일 사전은 verification/cooking-format/reference-analysis.json에 있다. 이전의 ‘파일 부재’ 표기는 그 당시 이력이다.

### 모든 시트와 문서 구성

| 시트 | 저장 범위 | 실제 내용 |
|---|---|---|
| 목 | A1:H41 | 제목 8/7(목) 입고분, 2014-08-07 석식 및 08-08 조식·중식 |
| 금 | A1:H34 | 제목 8/8(금) 입고분, 2014-08-08 석식 및 08-09 조식·중식 |
| 토 | A1:H35 | 제목 8/9(토) 입고분, 2014-08-09 석식 및 08-10 조식·중식 |
| 토 (1) | A1:H34 | 제목은 8/9(토) 입고분이나 본문은 2014-08-10(일) 석식. 실제 값은 17행까지, 나머지 저장 범위는 서식. 제목/본문 불일치를 자동 보정 규칙으로 해석하지 않음 |
| Sheet2 | A1:A1 | 값 없는 빈 시트 |
| Sheet3 | A1:A1 | 값 없는 빈 시트 |

4개 업무 시트의 공통 구조는 A1:H1 제목 병합, A2:F2 `날짜/예상식수/메뉴/재료/총량/비고`, G·H 숨김이다. 날짜 열은 한 식사 구간의 첫 세 행에 날짜·요일·식사를 나누어 입력했고 메뉴는 최초 재료 행에만 기입했다. B열에는 100 외에 11도 있어 메뉴/대상별 식수가 섞여 있다. 이를 전체 식사의 확정값으로 일괄 채택하지 않았다.

- 열 너비 A:F: 목 5/6.25/16.625/16.75/7.5/26.75, 금 5/5.5/20/17.5/8.375/23.75, 토·토(1) 5.625/5.5/20/16.75/8.375/23.375. G/H는 전부 8.875/9, 숨김.
- 제목 높이26.25pt, 기본 행 높이16.5pt, 본문은 목17.25pt·다른 업무 시트20.25pt. 제목/머리글 맑은 고딕11pt, 본문 목12pt·나머지14pt. 표 테두리는 thin. 날짜 숫자 서식 `m"/"d;@`, E열에는 `General\ "kg"` 서식과 봉/판/캔/개 등 문자 총량이 혼재한다.
- 4개 업무 시트는 A4(paperSize9) 세로, 여백 좌우0.7/상하0.75인치, 머리·꼬리말0.3인치. print area, 반복 머리글, fit-to 설정 및 수동 페이지 구분은 명시되지 않았다. 이미지/차트는 없고 나머지 빈 시트의 페이지 설정도 비어 있다.
- **계산 수식은 전 시트 0개**다. 수량·범위(예: 1~2), 재고 사용·적당량·배식 지시는 모두 저장된 리터럴 입력이다. 1인량 전용 열은 없다. 예시 총량/식수로 1인량이나 포장 내용량을 역산하지 않았다. 계산값임을 증명할 수 없는 셀은 계산값으로 분류하지 않았다.

### 원본·이전 구현·개선 결과 비교

| 항목 | 실제 Excel | 이전 구현 | 개선 결과·유지한 차이 |
|---|---|---|---|
| 표 머리글 | 날짜/예상식수/메뉴/재료/총량/비고 6열 | 메뉴·재료 중심 10열 가로 출력 | 웹/주 출력 시트 6열로 구성 |
| 제목·병합 | A1:H1, 입고분 | A1:J1 조리지시서 | A1:H1 병합, 다만 제목은 실제 생성 날짜·식사의 ‘조리지시서’로 유지 |
| 날짜·끼니 | 입고분 시트에 당일 석식+다음날 조·중식 | 식사별 단건만 제공 | 식사별 문서 유지 + 날짜별 전체 식사 Excel 다운로드(끼니별 별도 시트). 입고일 묶음으로 바꾸지 않음 |
| 예상식수 | 행/메뉴별100·11 등 | 식사별 확정값 | 최종 확정 식수 유지, 미확정 경고·0명 지원. 대상집단별 식수는 별도 요구사항 확인 필요 |
| 1인량 | 전용 열 없음 | 표시함 | 주 표 재료 셀에 1인량 추가 표시, 별도 계산근거 시트에 수치·단위를 보존. 원본과 의도적 차이 |
| 총량·단위 | 숫자 kg 표시 및 문자 포장량 혼재 | 기준 단위 총량 + 포장량 | 명시 기준 단위 총량과 등록 규격의 사용 포장량 표시. 35.1kg/5kg=7.02통, 발주 8통과 구분. 6자리 표시에서 반올림될 때 ≈ 표시, 계산근거에 수치 보존 |
| 비고 | 재료 행마다 재고·조리·배식 지시 | 메뉴 조리정보와 문서 공통 지시만 | 레시피 ID별 비고 입력·저장·재출력 추가, 공통 지시도 보존 |
| 포장 규격·업체 | 별도 구조화된 열 없음 | 명시 규격 사용 | 웹 비고/Excel 계산근거에 규격·업체 표시 유지. 원문 자유문자에서 추정하지 않음 |
| 서식 | 시트마다 너비·글자 크기 차이 | 전열18자, 가로 방향 | 금 시트 너비/제목 높이/숨김열/여백·세로 A4 채택. 본문12pt 및 줄바꿈·가변 높이는 가독성을 위한 의도적 변경 |
| 인쇄 | 영역·반복행·수동 구분 미설정 | 가로 한페이지 너비 | A:F 인쇄영역, 1:2행 반복, 너비1페이지·높이자동, 긴 비고 계속 행/페이지 구분, 한글 폭 고려 |
| 빈 시트·예시 | 빈2개 및 예시 데이터 | 신규 데이터 사용 | 빈 시트와 예시값을 복제하지 않음. 실제 DB의 해당 날짜/끼니 자료만 출력 |

### 구현 및 안전

- `meals/cooking_export.py`: 주 문서와 계산근거 시트 분리, 문서별6열·병합/서식·표시 단위·페이지 구분. 긴 비고는 나눠서 이어 쓰며 원문은 계산근거 시트에도 보존한다. 입력 문자열은 명시적 문자열 셀로 써 수식 실행을 막는다.
- `CookingInstruction.line_notes`: 식단별 JSON에 레시피 ID를 키로 한 비고 저장. 신규 `meals/0006_cookinginstruction_line_notes.py`는 기존 문서에 빈 dict 기본값을 추가하며 기존 공통 지시를 유지한다. 기존0005와 함께 테스트 DB에서 적용했다.
- `cooking_views.py`: 재료별 비고 폼·revision 검사, 날짜별끼니 Excel 다운로드, 기본 날짜는 서울 업무일 기준. `cooking.py`: 최종 식수/명시 규격 로직 유지, 표시용 수치/비고 연결. 문서 편집은 원장 입출고를 발생시키지 않는다.
- 템플릿: 원본6열 흐름, 인쇄 시 저장된 비고·공통 지시 전체를 정적 텍스트로 표시한다. 입력 textarea 및 저장 성공 메시지는 인쇄에서 제외한다. 수정 후 저장하고 출력하도록 안내한다.
- 앱은 참고 원본을 실행 중 읽거나 복사하지 않는다. 배포 시 원본 Excel이 없어도 출력된다. 실제 원본 비교 테스트만 파일이 없으면 명시적으로 skip한다. 이번에는 파일이 있어 skip 없이 실행됐다.

### 최종 검증 결과

| 실행 | 결과·증거 |
|---|---|
| SQLite 전체 회귀 | **117/117 통과**, 8.562초, 종료0, verification/cooking-format/sqlite.log |
| 격리 MariaDB10.6 전체 회귀 | **117/117 통과**, 9.854초, 종료0, mariadb.log |
| 조리지시서 테스트 | 기존12 + 신규4 = **16개 통과**, 위 전체에 포함 |
| 실제 원본 구조 비교 | 업무4시트 머리글/방향/용지/여백/숨김, 빈2시트, 금시트 열너비, 제목 병합/높이/폰트·테두리 비교 통과 |
| 추가 회귀 | 재료 비고 저장·수식문자·수정 충돌·비차감, 날짜별0/350/7명 별도 시트, 긴 비고의 계속행/페이지 구분 통과 |
| Django check·makemigrations·migration 적용/검사 | 양 DB 모두 통과, 모델과 migration 차이 없음 |
| Chromium 실제 UI | 로그인→최종351명 확정→35.1kg 조회→비고 저장→Excel 다운로드→인쇄 버튼/CSS·PDF→352명 변경 후35.2kg 재계산, 페이지 오류0. browser.json/browser.log |
| 다운로드 Excel·PDF 확인 | 실제 다운로드 파일을 openpyxl로 열어35.1kg·비고 확인. Chromium PDF A4세로1페이지 생성 후 이미지로 직접 가독성 확인 |
| 원본 보존 | 참조 SHA-256 동일, 참고 파일 변경 없음 |

최초 폐기용 앱은 초기화 중 종료됐고, 프로젝트 경로를 명시한 앱을 다시 준비했다. 첫 브라우저 연결은 서버 준비 전 연결 거부로 실패했으며 시작 로그 확인 후 재실행해 성공했다. 이후 표시 가독성 보완 후 두 DB와 브라우저 모두 최종 코드로 재실행했다. 실패 시도를 성공 결과로 섞지 않았다.

### 미완료·현업 확인 및 보호

- 원본의 입고일 묶음, 메뉴/대상집단별 식수, 범위/적당량/0총량 입력을 시스템의 수치 계산 규칙으로 바꾸는 작업은 하지 않았다. 현재 업무 규칙과 차이가 있어 영양사의 정책 결정이 필요하다.
- 원본의 토(1) 제목/본문 날짜 불일치는 그대로 분석 기록만 남겼다. 예시 날짜·수량·지시를 고정 데이터로 쓰지 않았다.
- 실제 Excel/LibreOffice 인쇄 엔진에서의 다페이지 실출력과 물리 프린터 검증은 미실시다. 구조·긴 비고 자동화 검증 및 브라우저1페이지 PDF와 구분한다. 임의의 모든 프린터에서 완전 동일하다고 주장하지 않는다.
- 동시 부하·분할 납품·기존 lot 대사·정상 SBERT/정확도 등 이전 잔여는 유지한다. TK-09-004는 현업 정책/인수가 남아 PARTIAL이다.
- 테스트 앱·MariaDB 컨테이너와 이번에 만든 내부 네트워크만 정리했다. 기존8000/8007서비스·DB·볼륨·네트워크·원본 ~/sprint7은 변경하지 않았다. requirements·Conda·AI모델도 변경하지 않았다. push/PR/배포/커밋 없이 기존 변경과 함께 작업 트리에 보존했다.

이번 수정 파일: meals/cooking.py, meals/cooking_views.py, meals/cooking_export.py(신규), meals/models.py, meals/migrations/0006_cookinginstruction_line_notes.py(신규), templates/workflow/cooking_detail.html, templates/workflow/cooking_index.html, integration_tests/test_cooking.py, integration_tests/browser_cooking.cjs(신규), 관련 분석/보고서·검증 증거. 전체 Git 상태는 verification/cooking-format/git-status.txt에 기록한다.
