# SNP 통합 서비스 종합 검증 보고서

검증일: 2026-11-04(KST). 기준 브랜치 `integration/sprint-final-kanghoon2-20261104`, 시작 HEAD `42f1fe5`.

## 1. 판단

**현재 수정본은 격리된 환경에서 핵심 영양사 업무를 실제 브라우저로 시연할 수 있다.** 업무 데이터가 없는 DB에서 공급업체·재료·규격·메뉴·레시피를 화면으로 등록하고, 기존 AI 예측→최종 확정→발주→합격량 입고→사용/폐기→수불→조리지시서/정산까지 완주했다. 시작 시139개 테스트는 모두 통과했지만, 기존 시험이 놓친 문서 누락·수량·레시피 단위·보안 결함을 추가 재현하여 수정했다.

**외부 공개 운영 준비 완료라는 판정은 아니다.** 개발용 배포 보안 설정, 실제 데이터 대사·사용자 인수, 온라인 AI 전체 경로, 부하/실물 프린터 검증은 남는다. 기존8000/8007/8010 컨테이너는 수정본을 배포하거나 업무 테스트하지 않았다. 이 보고서의 시연 가능 판정은 **현재 작업 트리의 코드를 격리 실행한 결과**다.

수정본은 현재 브랜치의 미커밋 변경이다. push·PR·배포·원본 브랜치 변경을 하지 않았다. 시작 시 존재했던 미추적 `OCTOBER_2026_COMMIT_AUDIT.md`는 수정하지 않았다.

## 2. 환경·보호 경계

| 항목 | 실제 사용 환경 |
|---|---|
| 코드 | `/home/woohyeak/sprint7-integration`,42f1fe5＋본 작업 수정 |
| Docker | `capstone-web:sprint7`, 소스 read-only mount, 컨테이너/tmp만 쓰기, 로컬 xlrd/xlwt wheel 사용 |
| Python/Django | Python3.12.13 / Django6.0.3 |
| AI 관련 환경 | NumPy2.4.3, pandas3.0.1, sklearn1.7.2. 설치/다운그레이드 없이 기존 이미지 사용 |
| SQLite | config.test_settings, 새 컨테이너의 `/tmp/sprint7-integration.sqlite3` 및 Django 테스트 DB |
| MariaDB | 새 mariadb:10.6 컨테이너, network none, 데이터/tmpfs, task 전용 Unix socket |
| 브라우저 | Playwright 실제 Chromium148.0.7778.96,1920×1080, 주 컨텍스트 외부HTTPS 차단 |
| 앱 연결 | 새 internal Docker network의 task 앱. 운영 포트/DB에 연결하지 않음 |
| 보호 | 기존 ~/sprint7·운영 컨테이너/DB/볼륨/네트워크, AI 모델3개,requirements,참고 문서 보존 |

`config.test_settings`는 환경 파일 로드를 차단하고 DB 설정을 격리한다. `config.test_mysql_settings`는 task 전용 socket에만 연결했다. 실제 DB에 migrate/flush/reset/seed를 실행하지 않았다. `reset_and_assign_suppliers`, docker compose, 강제 Git 명령은 사용하지 않았다.

환경 증거: [runtime.json](../../verification/comprehensive-20261104/runtime.json), [보호 파일 해시](../../verification/comprehensive-20261104/protected-files-before.json), 서비스 시작/종료 상태·보존 결과는 동 폴더의 preservation.json/cleanup.json.

## 3. 자동화 실행 결과

| 실행 | 발견/실행 대상 | 통과 | 실패/오류 | 건너뜀 | 증거 |
|---|---:|---:|---:|---:|---|
| 수정 전SQLite 기준 |139 |139 |0 |0 | sqlite-baseline.log |
| 수정 전MariaDB 기준 |139 |139 |0 |0 | mariadb-baseline.log |
| 추가 결함 재현 최초 |21메서드 |3 |18메서드에서 결함 재현 |0 | defects-before-fix.log |
| 수정 후 초기 집중 검사 |21 |21 |0 |0 | defects-after-fix.log |
| 최종SQLite 전체 |166 |164 |0 |2 | sqlite-final.log |
| 최종MariaDB 전체 |166 |166 |0 |0 | mariadb-final.log |
| JavaScript 기존 회귀 |4 |4 |0 |0 | javascript-final.log |
| 실제 DB 행 잠금 경합 별도 검사 |2 |2 |0 |0 | concurrency-deploy.log |
| Chromium 전체 업무 |1시나리오/22checkpoints |PASS |pageErrors0/server500응답0 |0 | browser-result.json |
| Chromium 월간 인쇄 재검증 |1시나리오 |PASS |pageErrors0 |0 | browser-print.json |

최종166개는 **기존139＋신규 서비스25＋동시성2**다. 기존139개 테스트 코드·기대값은 수정하지 않았으며, 기준 로그의139개 dotted identity가 최종 로그에도 모두 존재하는지 대조했다. 같은166개를 DB2종에서 실행한 것이므로332개 독립 케이스가 아니다. SQLite의2개 skip은 `has_select_for_update` 미지원 때문이며 동일2개가 MariaDB에서 실제 병렬 실행·통과했다.

최초 결함 재현 로그의 `failures=22, errors=18`은 subTest의 여러 조건 결과다. 이를40개 독립 테스트로 세지 않는다.21개 메서드 중18개에 실패/오류가 있었고3개는 이미 정상인 제어 사례였다. 브라우저22단계도22개 테스트나 사용자 인수 완료로 세지 않는다.

최종 두 DB 실행 모두 다음을 통과했다.

- `manage.py check`:0 issues.
- `makemigrations --check --dry-run`:No changes detected.
- 격리 DB 신규 migration 적용, `migrate --check`, showmigrations.
- 기존 데이터 업그레이드 보존 시험, 기존 AI 모델3개 로드/추론, 기존139개 회귀.
- 이번 작업에 **신규 migration은 없다**. OrderItem 추가 속성은 표시용 Python property이며 DB 필드 변경이 아니다.

실제 명령:

```bash
bash scripts/verify_integration.sh
SPRINT7_DB_SOCKET_DIR=/tmp/snp-comprehensive-db-socket-20261104 bash scripts/verify_integration.sh config.test_mysql_settings
node --test integration_tests/smart_order.test.cjs
SNP_BROWSER_BASE=<task-only app URL> node verification/comprehensive-20261104/browser-service.cjs
SNP_BROWSER_BASE=<latest task-only app URL> node verification/comprehensive-20261104/browser-print.cjs
docker exec snp-comprehensive-browser-20261104 python -B /workspace/verification/comprehensive-20261104/audit_business_data.py
```

새 DB/네트워크를 생성하고 검사한 후 정리했으므로 위 socket/URL은 현재 운영 접속 경로가 아니다. 재현 시 새 격리 환경을 준비해야 한다. 직접 실행한 집중검사와 병렬 검사는 증거 README의 컨테이너/설정 범위를 따른다.

## 4. 기능별 시나리오와 판정

| 기능 | 이번에 실제 확인한 조건/행동 | 판정 | 근거·한계 |
|---|---|---|---|
| 로그인·대시보드·이동 | 관리자 로그인→메뉴 이동, 비로그인 업무 URL은 로그인 화면 |PASS | Chromium. 기존 운영 서비스 로그인은 미수행 |
| 공급업체 | 기존 SUPPLIER 계정 명시 연결＋새 업체, 저장/재조회, 발주 계정 유지 |PASS | 브라우저 신규2업체, 기존/추가 회귀 |
| 식재료 |2품목 kg 직접 등록, 검색→수정 화면 재조회, 단위/음수/재고 보존 회귀 |PASS | UI＋DB 감사. 식재료 Excel 자체 UI는 이번엔 직접 조작하지 않고 기존 자동화 재실행 |
| 규격 |5kg/캔500원,3kg/판600원 저장. 재고 단가123/777원과 일부러 다르게 입력 |PASS | 실제 규격 화면/최종 주문/Excel 대조 |
| 메뉴·레시피 | 메뉴 생성→2재료 추가→각100g로수정→레거시 메뉴 편집 재저장 |PASS | 단위g 유지. -1/NaN/Infinity 입력은400, 기존행 보존 |
| 삭제 | 미사용 메뉴를 실제POST 버튼으로 삭제. GET/CSRF없음/사용확정 식단 삭제는 차단 |PASS | UI＋새 회귀. 기존 기능 삭제 없이 안전한 진입점 추가 |
| Excel 업로드 | 레시피XLSX·식단XLSX를 UI로 업로드,100g/77명 저장 확인 |PASS | business-data-audit.json. 기존CSV/XLS 등의 경계는 기존 회귀 |
| 식단 | 일간 등록/저장/재조회, 주간 다음 월요일 추가·삭제 AJAX |PASS | CSRF 유효 토큰으로 실제 화면 조작. 월간 생성 전체 UI는 미완주; 월간 조회/잘못된 월 입력 검증은 수행 |
| 기존 AI | UI에서 조중석 예측 실행·DB저장 |PASS(기존 오프라인 경로) | 조40/중210/석133, 저장된best_model 파일 사용. 정확도 지표 아님; 정상 온라인SBERT 전체는미검증 |
| 영양사 식수 | AI참고/직접360/최종351 구분, 미확정 계산 경고 |PASS | 브라우저 저장/재조회와 DB 필드 감사.0명·음수 등은 자동화 |
| 소요량·발주 |351×100g=35.1kg씩, 참치최소8→9캔 조정, 두부12판, 업체별2발주 |PASS | 날짜/금요일/안전재고/중복재료 회귀 포함 |
| 업체별 구매발주서 | 새workflow 항목과 주말 수동 발주 표시, 포장량·단가·금액 Excel |PASS | 참치9캔×500=4500, 두부12판×600=7200. 레거시 식사 묶음도 기존 회귀 유지 |
| 검수·입고 | 검수 전 재고0,45납품/40합격과36/36, 동일검수 재제출 |PASS | 입고는합격량만, 검수2/로그2. 별도 실제 동시 검수도 중복 입고0 |
| 사용·FIFO·폐기·수불 | 추가선입고2kg,35.1kg씩 사용, 참치1kg폐기, 주간조회 |PASS | 참치5.9/두부.9 및 lot3.9+2 검증. 동시초과출고는1건만저장 |
| 조리지시서 | 비고·현장지시 저장/재조회,Excel/PDF, 기간문서 연결 |PASS |100g×351=35.1kg,포장 사용량과 발주 올림량 구분,원장 불변 |
| 월간 정산 문서 | 발주11700/81kg와합격비례11200 분리,실제0/빈달·세금미정 표시 |PASS(참고 집계) | DB/화면/PDF. 세금·청구 확정/정식 회계 정산은 아님 |
| 문서 인쇄 | 업체발주1p,조리지시서1p,월간수정후1p,텍스트값 확인 |PASS(해당샘플) | PDF텍스트/이미지·인쇄버튼/CSS 확인. 실제 프린터/대량 문서는미검증 |
| 권한·신규가입 | 공급업체 내부조회403, 익명은로그인, 가입신청 비활성→관리자승인→로그인 |PASS | 실제 별도브라우저컨텍스트. 기존 승인계정은변경하지않음 |
| CSRF/XSS/Excel문자 | 토큰없는변경403,유효AJAX정상,악성모양메뉴가문자그대로,Excel수식차단 |PASS(검사한경계) | 보안 전체 침투시험 완료 의미는 아님 |
| 개발/운영 배포설정 | `check --deploy` |WARN/외부운영 미준비 | 경고6개. 아래 잔여위험 참조 |

핵심 흐름의 데이터 전달·입력·저장·재조회·출력까지 검사했다. 모든 화면/모든 대안 흐름이 검증됐다는 뜻은 아니다. 특히 여러 차수의 분할검수·반품정산·과거lot대사 등 원래 미완성 영역은 이 PASS 표로 완료 처리하지 않는다.

## 5. 발견 결함과 실제 수정

| ID | 재현된 문제/원인 | 수정 | 회귀 증거 |
|---|---|---|---|
| V01 |3개식단API csrf_exempt,월/주AJAX는토큰헤더없음 |exempt제거,정상폼/GET토큰과X-CSRFToken연결 |토큰없음403·유효토큰200＋실제주간추가/삭제 |
| V02 |메뉴삭제 GET이실제삭제 |POST전용＋목록에CSRF있는삭제폼 |GET405/데이터유지·실제미사용메뉴삭제 |
| V03 |사용완료식단을API/일괄삭제로변경해조리지시서·이력손실가능 |행잠금/사용확정검사,bulk전체차단,빈메뉴때확정메타/지시서보존 |served변경409,bulk보존,기존동작회귀 |
| V04 |bulk_delete redirect_url로외부사이트이동 |현재호스트/스킴검사후내부목록으로복귀 |evil.invalid 리다이렉트차단 |
| V05 |잘못된식사값이DB에저장,잘못된월/업체ID에500 |허용식사/JSON검증,공통월쿼리검사,정수ID검사 |invalid입력400/404·새행없음 |
| V06 |레거시편집이Recipe.unit를잃고100g→100kg해석. 오류행삭제후기존레시피소실/NaN500 |이전/명시단위전달,폼숨김단위/표시,전체검증/트랜잭션복구 |g유지·비정상입력400·기존행보존,UI재저장 |
| V07 |업체문서가식사기준으로만필터해meal_type없는새발주/주말수동발주누락 |새스냅샷은발주일기준직접표시,레거시끼니묶음별도유지 |문서행·총액·주말품목/기존금요일회귀 |
| V08 |Excel에9캔대신부족분35.1,명시포장단가대신재료단가123표시 |OrderItem표시property로저장포장수/단가/규격사용,월간재고단위환산단가일치 |9캔/500/4500,12판/600/7200·월간45kg×100 |
| V09 |사용자명/품목명이Excel수식으로출력,업체명[]/:등에시트생성오류 |문자형literalization,시트명정규화/31자제한,Content-Disposition안전생성 |여러다운로드수식셀0·특수문자업체xlsx열람 |
| V10 |메뉴명을innerHTML로넣어DOM/저장XSS가능 |일/주/월편집기의동적값을textContent/DOM필드로작성 |실제<img onerror>문자저장/검색/열기,실행0 |
| V11 |공개회원가입만으로활성NUTRITIONIST자체발급 |가입화면유지,신규계정은비활성·승인안내,기존계정불변 |요청role/staff무시,승인전로그인불가·Django관리자승인후성공 |
| V12 |월간PDF에웹푸터/상단이동버튼·297mm최소높이/여백이인쇄되어2p발생 |해당문서print CSS에서웹요소숨김/부모여백·최소높이해제 |동일샘플2p→1p,버튼/CSS/내용/PDF재검사 |

모든 결함을 ‘이번 강훈 통합이 처음 만들었다’고 단정하지 않는다. V07/V08/V06은 새workflow/단위와 레거시 화면 사이 계약 불일치다. 기존부터 존재한 보안/입력 결함도 이번 검증에서 함께 고쳤다. 실패를숨기거나필요량/잔고기대값을오류결과에맞추지않았다.

브라우저시나리오의초기중단2건은 제품결함과구별한다. attempt-1은검증스크립트의 `/specifications/` URL오기를실제 `/specs/`로수정했고, attempt-2는정확히같은값인35.100000/5.900000을문자서식으로비교한문제를숫자비교로수정했다. 두번모두task전용컨테이너/DB만새로만들었고최종실행은처음부터완주했다. FIFO샘플의선입고2kg는초단위입력시각이앞검수보다명확히뒤가되도록시간을분리했다. 실수량기대값은변경하지않았다.

## 6. 원장·문서 직접 대조

[business-data-audit.json](../../verification/comprehensive-20261104/business-data-audit.json)의독립ORM/Excel단언이통과했다.

- PurchaseOrder2 / OrderItem2 / GoodsInspection2 / InventoryLog6. 중복검수가추가입고를만들지않음.
- 직접예상360 / 최종351 / 사용확정True. AI조40·중210·석133은다른저장값.
- 메인레시피2개각100g유지. 업로드메뉴100g,업로드식단77명실제저장.
- 참치:검수40＋선입고2−사용35.1−폐기1＝5.9kg.두부:36−35.1＝0.9kg.
- FIFO참치lot잔량3.9＋2kg.요청순서가아닌거래일순배분을검증.
- 발주합11700원.합격량비례4000＋7200＝11200원.세금확정액이아님.
- 구매Excel9캔×500/12판×600와저장주문일치.조리계산근거시트35.1kg씩.수식셀0.
- 조리지시서지시사항저장/다운로드전후수불화면동일＋최종ORM잔액일치.

PDF는텍스트값대조＋실제페이지렌더확인. `cooking-print.png`의표/지시/비고는읽을수있었으며월간문서의불필요한두번째페이지는발견후수정했다.실물프린터의여백/폰트와동일하다고주장하지않는다.

## 7. 남은 위험·미검증

1. **공개 배포 보안은미완료.** check --deploy가W004(HSTS),W008(HTTPS리다이렉트),W009(검사설정의개발용secret),W012/W016(secure cookies),W018(DEBUG)6개경고를반환했다. 소스기본설정에도개발용키/DEBUG/광범위ALLOWED_HOSTS가있어운영키외부화·호스트제한·HTTPS·쿠키설정을별도로확정해야한다. test_settings의의도적테스트키경고와실제운영환경점검은구별한다. 기존운영환경변수/서비스설정은변경하지않았다.
2. 가입정책은승인제로바뀌었다. 전시계정은미리활성화하고, 신규가입승인은Django사용자관리권한이있는관리자계정으로수행해야한다. 역할ADMIN만있고권한없는계정은별도확인이필요하다.
3. 정상온라인SBERT/외부모델다운로드경로·예측정확도·최종실험모델교체는미검증/범위밖이다. 로컬모델추론과오프라인대체특성처리의통과를연구모델성과로확대하지않는다.
4. 실제운영품목분류·공급업체연락처·납품규격·세금·과거입출고와미배정lot는대사하지않았다. 부분합격은검증했지만여러차수누적납품/검수정정·취소/환불회계전체는미완성이다.
5. 오래된식단을현재레시피로조회하는문서의역사적스냅샷정책, 이미사용된메뉴의레시피자체개정정책은추가합의가필요하다. 이번served식단구성삭제차단이과거레시피버전관리를구현한것은아니다.
6. 월간식단생성전체UI·모든문서의모든필터조합·실제사용자인수·성능/부하·다중브라우저·실물프린터·대량/긴문서전체는검증하지않았다. MariaDB경합2개로모든동시성문제가없다고단정하지않는다. 전역업무권한과특정공격경계시험은전체침투시험이아니다.
7. E2E샘플은검증일11월4일과업무일11월6일/해당주를명시한다.다른날짜에재현할때는업무일·거래일·조회기간이일치하도록샘플날짜를같이준비해야한다. 실제DB를샘플로초기화해서는안된다.
8. 기존실행컨테이너가새작업트리와동일한코드/환경인지배포검증하지않았다. 새수정본을전시서비스에적용하려면별도배포승인과백업/환경확인이필요하다.

## 8. 전시 권고

- **로컬/격리시연:가능.** 승인된영양사로그인→식단/100g레시피→AI참고/최종351→35.1kg/포장올림→업체발주→합격량→수불→조리지시서/정산을추천한다.
- 시연전최소준비:수정본을반영한별도환경,활성전시계정,명시규격/레시피단위,시연일과일치하는식단·거래일,기존모델파일/의존성,다운로드/인쇄사전확인.
- 네트워크/AI장애시수동식수확정흐름과이번PDF/스크린샷을대체자료로쓴다.연구최종모델/실제운영데이터로속여시연하지않는다.
- **현재기존8000/8007/8010서비스에서수정본을즉시시연가능하다고보장할수없다.** 이번에는배포하지않았고,공개운영은보안/데이터/업무규칙후속조치가필요하다.

## 9. 변경 파일·증거·Git 상태

신규핵심파일: `config/export_safety.py`, `config/input_validation.py`, `integration_tests/test_service_verification.py`(25개), `integration_tests/test_concurrency.py`(2개). 기존애플리케이션변경은아래파일별목록에기록한다. 새로운DB필드/migration/AI모델/requirements변경없음.

보고서/실행증거는이문서와 `verification/comprehensive-20261104/`에저장했다. 원래미추적10월조사보고서는보존했다. 전체변경은리뷰가능한미커밋작업트리이며원격push/PR/배포없음. task전용컨테이너/네트워크/socket정리결과는cleanup.json,기존서비스시작시각/모델·문서보존은preservation.json에기록한다.


| 변경 파일 | 이유 |
|---|---|
| `accounts/views.py` | 新規가입만관리자승인전비활성;기존계정불변 |
| `forecasting/views.py` | 월입력오류400/Excel문자안전;AI추론서비스불변 |
| `inventory/views.py` | 월입력오류400/원장Excel문자안전 |
| `meals/views.py` | CSRF·served보호·POST삭제·입력/리다이렉트검증·레시피단위/트랜잭션·월/Excel검증 |
| `procurement/models.py` | DB필드없이주문표시용수량/단위/규격/단가property추가 |
| `procurement/team_document_views.py` | 월간재고단위환산단가가실제발주금액과일치 |
| `procurement/views.py` | 업체문서신규/레거시날짜분리·실발주스냅샷·Excel/ID안전 |
| `templates/accounts/signup.html` | 승인절차사용자안내 |
| `templates/docs/doc_monthly_settlement.html` | 환산단가표시와실물페이지의여백/푸터인쇄회귀수정 |
| `templates/docs/vendor_procurement_report.html` | 부족분/재료단가대신실발주포장수/단가/규격표시 |
| `templates/meals/mealplan_create.html` | 동적메뉴명의DOM문자처리와월/주AJAX의CSRF헤더연결 |
| `templates/meals/mealplan_list.html` | 동적메뉴명의DOM문자처리와월/주AJAX의CSRF헤더연결 |
| `templates/meals/menu_create.html` | 레시피단위를숨김필드/표시로전달 |
| `templates/meals/menu_list.html` | CSRF있는POST삭제버튼연결 |
| `templates/meals/menu_update.html` | 레시피단위를숨김필드/표시로전달 |
| `templates/meals/recipe_create.html` | 레시피단위를숨김필드/표시로전달 |
| `templates/meals/weekly_mealplan_create.html` | 동적메뉴명의DOM문자처리와월/주AJAX의CSRF헤더연결 |
| `templates/procurement/order_detail.html` | 부족분/재료단가대신실발주포장수/단가/규격표시 |
| `config/export_safety.py` | 수식삽입방어와유효시트명공통처리 |
| `config/input_validation.py` | 월쿼리/정수ID의입력오류처리 |
| `integration_tests/test_service_verification.py` | 서비스결함/보안/문서25개회귀 |
| `integration_tests/test_concurrency.py` | MariaDB실제병렬검수/출고2개회귀 |


기존 분석 문서의 이력은 보존하고 FUNCTIONAL_TEST_REPORT.md, REQUIREMENT_TRACEABILITY_MATRIX.md, REMAINING_ISSUES.md에 이번 검증 증거/해결·잔여 사항만 덧붙였다.


## 10. 종료 확인

- 기존 서비스4개(my-capstone, my-capstone-sprint7, snp-presentation, snp-readiness-db-20261016)의 Running/StartedAt가 시작 때와 동일했다. 운영 DB 내용 조회/수정은 하지 않았다.
- 보호 대상11개 파일(원래10월보고서·requirements·모델3개·참조파일)의 SHA256가 모두 동일했다. 기존139개 테스트 파일도 수정하지 않았다.
- 전체 회귀에 사용한 소스 SHA256와 최종 작업 트리가 일치했다.
- task 앱/DB/정리 컨테이너·신규 내부 네트워크·socket 디렉터리는 모두 제거했다. 기존 자원을 정리하지 않았다.
- 기존 추적 파일21개 수정(앱/템플릿18개＋분석 문서3개), 신규 소스/시험4개와 본 보고서/실행 증거를 남겼다. 이전 미추적10월보고서도 그대로 남아 있다. 커밋·push·PR·배포는 수행하지 않았다.


## sprint-final 원격 반영 준비 기록

검증 보고서 작성 당시 미커밋이던 수정은 이후 `04db7c1`에 이미 커밋되어 있었다. 원격 반영 준비에서는 그 커밋과42f1fe5 통합 이력을 유지하며 코드/테스트를 다시 수정하지 않았다. 최종166개 검증의 소스 SHA25622개가 현재 소스와 일치한다. 최종 증거는 유지하고 중간·중복 산출물은 로컬 보존/추적 제외했다. 과거 이력을 삭제한 것은 아니며 구체 보관 범위는 verification/comprehensive-20261104/README.md와.gitignore를 따른다. 이 단계에서 Docker/DB/배포 작업이나 새 테스트 실행은 하지 않았다.
