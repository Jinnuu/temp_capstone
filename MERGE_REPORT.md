# Sprint 7 · 강훈 브랜치 통합 보고서

> 최신 결과: 문서 기반 보완 후 SQLite/MariaDB 각각 101개 테스트 통과. 현재 기능 상태는 docs/analysis/FUNCTIONAL_TEST_REPORT.md와 본 문서 하단 추가 작업 절을 따른다. 아래 기존 통합 기록은 변경 이력으로 보존했다.

작성일: 2026-10-15 (Asia/Seoul)

## 작업 범위와 보존 확인

- 작업 디렉터리: `/home/woohyeak/sprint7-integration`
- 통합 브랜치: `integration/sprint7-kanghoon`
- Sprint 7 기준: `a8f5adbe3c971e00f7c14a60160ee926abf7a0e2`
- 강훈 기준: `3b01dc8cf8ab229313e959c8b067d62deff8253d`
- 공통 조상: `c92461275c1beb6f96df80db00a6ed3428e9f39c`
- 원본 `/home/woohyeak/sprint7`에는 파일·브랜치·커밋 변경을 수행하지 않았다.
- 원본 미커밋 4개 파일은 내용 그대로 복사한 후 `eac48a0` 보존 커밋으로 먼저 기록했다.
- 대시보드 전체 부족 재고 수, 간편 발주 연동, 자동 선택·강조·상단 배치 기능을 통합본에 유지했다. 발주 연동 계산은 아래 오류 수정을 적용했다.
- 원본 네 파일의 SHA-256, HEAD, 작업 트리 상태, 기존 컨테이너 상태는 `verification/original-preservation.json`에 기록했다.
- 기존 `my-capstone`(8000), `my-capstone-sprint7`(8007) 및 연결 DB·볼륨·네트워크는 변경하지 않았다. 기존 두 컨테이너의 시작 시각과 재시작 횟수도 유지됐다.
- 기존 DB에 migrate, flush, loaddata, seed, 업체 초기화 명령을 실행하지 않았다.
- 원격 push, PR 생성, 기존 서비스 배포는 수행하지 않았다.

## 충돌 해결 내역

실제 병합에서 충돌한 12개 파일을 수동 조정했다. 미커밋 수정이 더해져 조사 당시 커밋 비교보다 간편 발주 템플릿 충돌이 추가됐다.

| 파일 | 해결 방식 |
|---|---|
| `inventory/urls.py` | 기존 `ingredient_upload_flexible` 및 legacy URL을 유지하고 신규 재고 문서 URL 추가. 강훈 브랜치의 중복 URL 이름은 도입하지 않음. |
| `inventory/views.py` | 기존 재고 집계·부족 우선 정렬 기본값을 유지. 최신순·이름순·업체순 선택, 페이지당 15개를 제공. 업로드는 release patch 진입점으로 통일. |
| `meals/urls.py` | 기존 레시피 업로드 화면/API·재고 차감의 release patch 연결 유지. 신규 문서·삭제 API 연결 추가. |
| `meals/views_extra.py` | Sprint 7의 행/가로형 파일 및 식수 파싱과 강훈의 달력형·안내문 제외·메뉴 분류/정렬 파서를 결합. CSV/XLSX/XLSM/XLTX 지원. |
| `procurement/urls.py` | 기존 발주·보고서·Excel URL과 신규 구입요구서·검수일지 URL 병존. |
| `procurement/views.py` | 강훈의 발주일 묶음·업체 보고서를 유지하면서 미커밋의 재고 ID/이름·수량/날짜 연동을 결합. POST 날짜 보정 및 안전재고 계산 수정. |
| `requirements.txt` | 기존 패키지 버전 전부 유지, XLS 파싱용 `xlrd==2.0.2`만 추가. UTF-16에서 UTF-8로 정규화. |
| `templates/inventory/ingredient_upload.html` | 신규 다중 형식 안내/입력 UI와 기존 업로드 URL 사용. |
| `templates/meals/mealplan_bulk_upload.html` | Sprint 7 안내·화면 유지, XLTX 허용 추가. |
| `templates/meals/mealplan_create.html` | 기존 메뉴 선택과 새 이름 직접 입력을 지원하는 강훈의 배지/datalist UI 채택. |
| `templates/meals/weekly_mealplan_create.html` | Sprint 7의 검색 추천·토큰 삭제 UI 유지. Enter로 새 메뉴 추가, 차주 월요일 조·중식 편집 영역 추가. |
| `templates/procurement/order_create.html` | 자동 선택·강조·상단 정렬과 강훈의 행 클릭 선택을 모두 유지. 빈 목록 안내 복원. |

`meals/views.py`는 Git 자동 병합이 가능했지만 Sprint 7에 반복 삽입된 동일 함수/처리 블록이 있었다. 강훈의 정리된 구현을 사용해 중복을 제거하고 기존 레시피 생성·수정 기능을 유지했다. 기존 실제 재고 차감 URL은 계속 `meals/release_patch_views.py`를 사용한다.

## 기능 보존 및 보정

### 재고·발주

- `calc_stock`은 모델 필드가 아닌 집계 속성이다. 간편 발주에 `get_ingredient_stock_queryset()`를 사용해 입고 − 출고 − 폐기 + 조정의 실제 재고로 부족량을 계산한다.
- 단일 ID, 쉼표 구분 ID, 반복된 `items` ID를 지원한다. 중복 ID는 재고 쿼리에서 합쳐지며 잘못된 토큰은 제외한다.
- 재고가 충분하면 강제 최소 발주량 1을 넣지 않는다.
- 명시적 품목명/수량이 있으면 날짜 계산으로 덮어쓰지 않는다. 숫자로 된 품목명도 수량과 함께 전달되면 이름으로 취급한다.
- 대시보드는 전체 부족 품목 수를 표시하고 사이드바만 8개로 제한한다.
- 월~목 발주 묶음은 당일 석식 + 다음 날 조식·중식이다.
- 금요일 묶음은 금요일 석식 + 토·일 전체 + 다음 월요일 조식·중식이다. 토·일은 별도 발주일 그룹을 만들지 않는다.
- `days`는 발주일 필터다. 따라서 조회 종료일 이후의 식단이 묶음에 포함될 수 있다.
- 안전재고 중복 방지: `가상 잔고 = 이전 잔고 + 이번 보충량 - 이번 소비량`. 같은 식재료가 여러 메뉴·끼니·발주일에 나와도 보충량을 다음 계산에 이월한다.
- 예: 실재고 8kg, 안전재고 5kg, 필요량 10kg 세 번이면 발주는 7 + 10 + 10 = 27kg이다.
- 화면의 일괄 식수 변경도 같은 순차 계산을 사용한다. 재적용 시 서버가 준 최초 실재고에서 다시 시작한다.
- 계산은 화면 내 가상 재고 시뮬레이션이다. 실제 재고 변경은 발주 완료 입고/식사 완료 출고 시 수행한다. 기존 미입고 발주 예약량을 별도로 차감하는 기능은 추가하지 않았다.

### 업로드·재고 차감

- `inventory.release_patch_views.ingredient_upload_flexible` 진입점과 두 업로드 URL을 유지했다. 내부 공통 서비스에서 제목행 탐색, 헤더 공백·괄호 정리, 다중 시트, 시트명 분류, 공급업체 username/name/first_name 연결을 지원한다.
- 생략된 컬럼은 기존 기준정보를 보존한다. 알 수 없는 공급업체나 잘못된 숫자가 있으면 업로드 전체를 롤백한다.
- 기존 레시피 Excel 업로드 화면과 별도 API, 메뉴별 레시피 조회·식재료 검색 URL을 유지했다.
- 기존 재고 차감 preview/confirm 기능을 유지했다. 이미 `is_served=True`인 식단은 제외하며 확정 시 트랜잭션 안에서 식단을 다시 잠가 조회한다. 순차 중복 확정이 재차 출고를 만들지 않는 것을 검증했다. 동시 요청 부하 테스트는 별도 미검증이다.
- 새 메뉴 개별 삭제와 식단 일괄 삭제를 연결했다. 일괄 삭제는 POST만 허용하도록 보정했다. 단순 GET 조회가 데이터를 삭제하지 않는다.
- 재고 목록의 기존 부족 우선 기본 정렬은 유지했다. 최신순도 선택할 수 있다. 강훈의 이름에 `테스트`가 포함된 품목 제외 규칙도 공통 재고 집계와 일부 발주·문서 조회에 반영됐다. 운영에서 이 문자열이 들어간 실제 품목을 사용하는지는 별도 확인이 필요하다.

### 문서

신규 재고 수불현황, 식단조견표, 구입요구서, 검수일지, 주간 레시피 명세서와 기존 주·월간/업체별 문서 및 Excel 경로를 유지했다. 검수서 Excel의 제목 병합 영역이 결재 영역과 겹쳐 `MergedCell` 쓰기 오류가 발생하던 부분을 분리했다.

## 마이그레이션 검증

브랜치 간 기존 마이그레이션 파일 충돌은 없었다. 그러나 실제 `makemigrations --check --dry-run`에서 **기존 양쪽 소스에 이미 있던 모델/마이그레이션 상태 불일치** 두 건이 발견됐다.

| 추가 마이그레이션 | 내용 |
|---|---|
| `inventory/0007_alter_inventorylog_transaction_date` | 이미 모델에 있던 `default=timezone.now`와 migration state의 `auto_now_add=True`를 일치시킴. |
| `procurement/0005_alter_purchaseorder_status` | 이미 모델에 있던 대기/승인/완료 choices와 migration state를 일치시킴. |

Drop/DeleteModel/RunPython 데이터 삭제나 상태값 일괄 치환은 없다. 격리 SQLite 및 MariaDB에서 신규 DB 전체 적용과, 이전 migration state에 사용자·재료·수불 로그·발주·품목을 만든 뒤 업그레이드하는 테스트를 수행했다. 수량·날짜·관계·금액·기존 `배송완료` 문자열이 보존됨을 확인했다.

운영 DB의 적용 이력이나 스키마 일치 여부는 검증하지 않았다. 조사 시 기존 컨테이너의 `nextcloud-db` 이름 해석이 실패했던 문제도 변경하지 않았다. 위 두 마이그레이션은 기존 서비스 DB에 적용하지 않았다.

## 격리 검증 환경

- Python 3.12.13, 기존 `capstone-web:sprint7` 이미지 사용.
- 이미지 ID: `sha256:8b128d4a45565b0a80c623b923c83d0441632ecfd759fb20f768be0da91947b3`.
- 앱 테스트 컨테이너: `--network none --read-only --tmpfs /tmp`, 통합 소스만 읽기 전용 마운트. 호스트 포트 공개 없음.
- SQLite: `/tmp`의 폐기용 DB 및 Django 전용 테스트 DB.
- MariaDB: 기존 DB와 무관한 신규 `mariadb:10.6` 컨테이너, `--network none`, 데이터 디렉터리는 tmpfs. 새 Unix socket 경로만 테스트 앱에 마운트. 기존 Docker 네트워크·볼륨에 연결하지 않음.
- `config.test_settings`는 배포 `.env` 읽기를 차단하고 DB를 SQLite로 대체한다. `config.test_mysql_settings`는 새 테스트용 Unix socket만 지정한다.
- XLS용 `xlrd`와 테스트 파일 생성용 `xlwt`는 오프라인 wheel로 컨테이너 `/tmp/deps`에만 설치했다. `xlwt`는 운영 requirements에 추가하지 않았다.
- wheel 다운로드만 별도 호스트 준비 단계에서 수행했다. 테스트 앱은 계속 네트워크 차단 상태다.

## 최종 테스트 결과

| 검증 | SQLite | 격리 MariaDB |
|---|---|---|
| Django `check` | 통과 | 통과 |
| `makemigrations --check --dry-run` | 변경 없음 | 변경 없음 |
| `migrate`, `migrate --check`, migration graph | 통과 | 통과 |
| 전체 Django 테스트 | 48개 통과 | 48개 통과 |
| 이전 스키마 데이터 보존 업그레이드 | 통과 | 통과 |

JavaScript 순차 재고 계산 테스트: **4개 통과** (`node --test integration_tests/smart_order.test.cjs`).

주요 테스트 범위:

- `calc_stock` 실제 집계, 단일/복수 ID, 재고 충분, 명시 수량/날짜 우선순위
- 대시보드 8개 초과 부족 품목 전체 수
- release patch 실제 URL 연결
- 제목행/다중 시트/XLS/CSV 업로드, 공급업체 회사명 연결, 누락 컬럼 보존, 실패 롤백
- 레시피 업로드 → 식단/식수 → 차감 미리보기 → 확정 → 재확정 시 중복 출고 방지
- 월~목, 금요일·주말·다음 월요일, 요일 필터, 식단 중복 방지, 안전재고 중복 방지, 예측 식수 사용
- 발주 생성 → 완료 입고 → 완료 재요청 시 중복 입고 방지
- 실제 저장 모델 추론 → 식단 발주 → 입고 → 식사 출고 → 안전재고 잔량 → 레시피 명세서의 전체 업무 흐름
- 주요 화면·문서 25개 URL 렌더링, 5개 Excel의 실제 workbook 재열기
- 기존/신규 식단 업로드 테스트, 새 메뉴명 API·개별 삭제·POST 일괄 삭제, 주간 검색/차주 월요일 영역

증거 파일:

- `verification/sqlite-final.log`
- `verification/mariadb-final.log`
- `verification/javascript.log`
- `verification/environment.json`
- `verification/original-preservation.json`
- `verification/test-db-isolation.txt`

`verification/tests-initial.log`, `verification/tests-second.log`에는 수정 전 실패를 남겼다. upstream의 `verification_output.txt`는 이번 검증 결과로 간주하지 않았다.

## AI 호환성 결과와 한계

- 기존 requirements 53개 패키지를 모두 유지하고 `xlrd`만 추가했다. 현재 요구사항 54개의 설치 버전이 모두 일치한다 (`verification/environment.json`).
- NumPy 2.4.3, scikit-learn 1.7.2, pandas 3.0.1, sentence-transformers 5.3.0을 유지했다. 강훈의 일괄 다운그레이드/Flask 등 무관한 패키지는 반영하지 않았다.
- 조식·중식·석식 `.pkl`은 변경하지 않았다. 실제 세 모델 로드 및 `.predict()` 실행이 통과했다.
- 실제 DataProcessor → 모델 → AttendancePrediction 저장 경로도 세 끼니 모두 통과했다. 지정 데이터/날짜의 오프라인 예측은 조식 46명, 중식 219명, 석식 132명이었다.
- **SBERT 원격 가중치가 격리 환경 캐시에 없어 텍스트 특성을 제외하는 기존 fallback이 사용됐다. 정상 SBERT 임베딩 및 저장 KMeans와의 결합 경로, 예측 정확도는 미검증이다.** 이 경로를 성공으로 표시하지 않는다.
- artifact에 `feature_columns` 메타데이터가 없으므로 모델 자체의 feature names를 사용해 직접 로드/추론 테스트를 했다. 기존 예측 코드의 feature 구성은 변경하지 않았다.
- requirements 전체를 새 기반 이미지에서 처음부터 설치하는 빌드는 수행하지 않았다. 검증 환경은 기존 이미지의 일치하는 패키지에 `xlrd`를 추가한 환경이다.

## 조리지시서 조사: 시스템 통합 미완료

두 기준 커밋의 Python/HTML/Markdown에서 조리지시서 및 cooking instruction/order 관련 명칭과 구현·URL·모델을 조사했다. **전용 조리지시서 구현은 찾지 못했다.** 현재 브랜치 외부에서 개별 구현된 소스의 위치는 확인되지 않았다.

강훈 브랜치에는 `weekly_recipe_report`와 `docs/weekly_recipe_report.html`이 있다. 이는 식단 → 메뉴 → 레시피와 사용자가 명시한 식수를 곱하는 **주간 레시피 소요량 명세서**다. 이 연결 및 수량은 테스트했다. 조리 절차·작업 지시·완료 처리 기능은 없으며, 기본 인원은 100명이고 예측/식단 식수를 자동 선택하지 않는다. 조리지시서 통합 완료로 대체 판정하지 않는다.

후속 작업:

1. 별도 구현된 조리지시서의 브랜치/커밋 또는 소스 위치 확보.
2. 문서 대상 날짜·끼니와 DietPlan/DietMenu/Recipe 연결 정의.
3. 예측 식수/목표 식수/수동 확정 식수의 우선순위, 단위 및 총량 검증.
4. 기존 주간 레시피 명세서와 조리지시서의 관계 및 진입 화면 결정.
5. 원래 구현의 조리 지시·인쇄·확정 업무 흐름 통합 테스트 후 완료 판정.

## 미검증·후속 사항

- 운영 DB 이력/실데이터, 운영 DNS, 기존 서비스 응답에 대한 검증·수정은 수행하지 않았다.
- 실제 브라우저의 클릭·키보드 이벤트 및 인쇄 레이아웃/PDF 페이지 나눔은 미검증이다. 서버 렌더링·Excel·계산 함수 테스트 통과와 구분한다.
- 동시 확정 요청, 대규모 업로드/문서 성능 부하 테스트는 미실시다.
- 기존 `배송중`/`배송완료` 기록의 운영 전환 정책은 별도 확인 대상이다. 보정 마이그레이션은 기존 값을 삭제하거나 변환하지 않는다.
- 신규 관리 명령 `reset_and_assign_suppliers`, `merge_suppliers`, `assign_suppliers`, `seed_ingredients` 및 기존 seed/덤프/패치 스크립트를 실행하지 않았다. 특히 초기화 명령은 일반 사용자 삭제·업체 관계 변경을 포함하므로 통합/배포 절차에 포함하지 않는다.
- push·PR·배포·운영 DB 마이그레이션은 별도 승인 범위다.

## 재현 방법

```bash
cd /home/woohyeak/sprint7-integration
python3 scripts/prepare_integration_wheels.py
bash scripts/verify_integration.sh
node --test integration_tests/smart_order.test.cjs
```

MariaDB 테스트는 전용 컨테이너가 필요하다. 아래 이름과 경로는 통합 테스트 전용이며 기존 컨테이너를 가리키지 않는다.

```bash
mkdir -p /tmp/sprint7-integration-db-socket
docker run -d --name sprint7-integration-db-audit --network none \
  --tmpfs /var/lib/mysql:rw,size=512m \
  -v /tmp/sprint7-integration-db-socket:/run/mysqld \
  -e MARIADB_ROOT_PASSWORD=isolated-test-password \
  -e MARIADB_DATABASE=sprint7_integration mariadb:10.6
# 전용 DB 로그에서 ready for connections 확인 후:
bash scripts/verify_integration.sh config.test_mysql_settings
# 전용 DB 컨테이너만 정리:
docker rm -f sprint7-integration-db-audit
```

검증 종료 후 테스트 전용 DB 컨테이너는 제거했다. 앱 테스트 컨테이너는 `--rm`으로 자동 제거됐다. 기존 서비스 컨테이너는 그대로 실행 중이다.

테스트 당시의 패키지 버전·모델 해시는 environment manifest를 기준으로 한다. 이미지 태그가 변경됐다면 동일 이미지 ID로 `SPRINT7_TEST_IMAGE`를 지정한다.

# 2026-10-15 추가 작업: 문서 기반 기능 검증·보완

이 절은 위 e21478b 통합 당시의 결과와 구분되는 후속 작업이다. 당시의 48개 테스트/조리지시서 미통합 기록은 역사적 결과이며, 현재 검증은 `docs/analysis/FUNCTIONAL_TEST_REPORT.md`와 `verification/requirements/`를 기준으로 한다.

- 코드 변경 전 `ab5ed57`에서 요구사항 추적표·계획을 먼저 작성했다.
- 참조 Markdown 5개와 내장 그림 2개를 확인했다. 원본은 수정하거나 Git에 추가하지 않았다.
- 추적 항목 196행: 최초 COMPLETE 0 / PARTIAL 123 / MISSING 18 / BROKEN 1 / UNVERIFIED 54 → 현재 COMPLETE 78 / PARTIAL 64 / MISSING 1 / BROKEN 0 / UNVERIFIED 53. 상하위·중복 태스크를 포함한 추적 행 수다.
- UC 15개 중 9개 COMPLETE, 6개 PARTIAL. 모든 기능의 현장 인수를 완료했다는 뜻은 아니다.
- 추가 구현: 수동/AI/최종 식수 분리·확정/변경 재검토, 명시 단위/납품규격·발주 간격 환산, 저장형 발주예정서·업체별 확정·요청 중복 방지, 실제 합격량 검수 입고, 안전한 차감, 신규 lot/FIFO/유통기한, 기준정보 관리 UI, 주간 수불/월 정산 연결, 인증 보호, 문서명·정렬·분류 중복·비고/빈 입력란 출력.
- 기존 간편·식단 발주도 공통 검토 서비스에 연결했다. 기존 완료 버튼만으로 입고되는 동작은 최신 문서 O-04에 따라 검수 기록을 요구하도록 변경했다. AI 값이 최종 값을 대신하지 않도록 legacy 필요량 계산도 정리했다.
- 기존 release patch 식재료/레시피 업로드 및 재고 차감 경로를 유지했다. 재고 부족·0명·음수 입력과 레시피 업로드의 기준 단위 변경 문제를 보정했다.
- 새 migration 8개를 추가했다. 테스트 DB에서 전체 적용 및 기존 데이터 보존 업그레이드를 검증했으며 운영 DB에 적용하지 않았다.
- 최종 검증: **SQLite 101개 / 격리 MariaDB 101개 Django 테스트**, JavaScript 4개 통과. `check`, `makemigrations --check --dry-run`, `migrate --check`, migration graph 및 실제 모델 추론을 포함한다.
- 실제 Chromium 브라우저에서 최종 351명 → 35.1kg → 8캔 계산 → 9캔 조정 → 45kg 납품/40kg 합격 → 35.1kg 사용 → 4.9kg 수불 잔량/FIFO → PDF 생성까지 수행했다.
- 모델 3개와 기존 requirements 버전은 변경하지 않았다. 정상 SBERT/OOF/Holdout 정확도는 여전히 미검증이다.
- 조리지시서 전용 구현은 발견되지 않아 TK-09-004를 MISSING으로 남겼다. 조리 정보 입력 기능이나 주간 레시피 문서를 통합 완료로 대신 표시하지 않는다.
- 기존 재고 lot 대사, 취소/대체 발주·분할 납품/검수 정정·회계 정책, 월간 전용 작성·독립 구입요구서 초안·영양 데이터·현장 인수 등은 `REMAINING_ISSUES.md`에 명시했다.
- 원본 네 파일·참조 원본·AI 모델 해시와 기존 두 컨테이너의 시작시각/재시작 횟수 보존을 확인했다 (`verification/requirements/preservation.json`).
- 원격 push, PR, 기존 서비스 배포 및 기존 DB/볼륨/네트워크 변경은 수행하지 않았다.

상세 결과물:

1. `docs/analysis/REQUIREMENT_TRACEABILITY_MATRIX.md`
2. `docs/analysis/IMPLEMENTATION_PLAN.md`
3. `docs/analysis/FUNCTIONAL_TEST_REPORT.md` — 수정 파일/신규 migration 전체 목록 포함
4. `docs/analysis/REMAINING_ISSUES.md`
5. `docs/analysis/requirement_catalog.json` — 출처·수용 기준·초기/최종 상태·원본 해시

새 MariaDB 재현 시 전용 컨테이너 이름은 임의로 정하되 `/tmp/sprint7-integration-db-socket`에만 연결한다. 브라우저 검증은 `snp-requirements-test`처럼 새 내부 네트워크와 폐기용 `config.test_settings` 서버를 사용한다. 기존 서비스나 운영 DB를 테스트 대상으로 지정하지 않는다.

검증 종료 후 `snp-requirements-browser-app`, `snp-requirements-db`, `snp-requirements-test`를 정리했다. 기존 서비스에는 정리 명령을 실행하지 않았다.
