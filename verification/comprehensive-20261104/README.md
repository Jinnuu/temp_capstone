# 2026-11-04 종합 검증 실행 증거

이 디렉터리의 계정·품목·수량은 격리 검증용 합성 데이터다. 운영 DB에 연결하지 않았다.

## 실행 순서

1. 원래 코드42f1fe5의 기존139개를 `scripts/verify_integration.sh`로 SQLite/MariaDB에서 각각 재실행: sqlite-baseline.log / mariadb-baseline.log.
2. 신규 서비스21개를 컨테이너 내부 `python -B manage.py test integration_tests.test_service_verification --settings=config.test_settings --verbosity=2`로 실행: defects-before-fix.log.18개 메서드에 결함 재현; subTest 실패/오류 수를 독립 케이스 수와 혼동하지 않는다.
3. 수정 후 같은21개 집중검사 통과: defects-after-fix.log. 이후 CSRF 화면/가입권한/단가/삭제 및 실제경합 회귀를 추가했다.
4. 최초 전체160개 통과: sqlite-first.log / mariadb-first.log. 최종적으로 기존139＋서비스25＋동시성2=166개를 전체 재실행했다.
5. 최종 결과: sqlite-final.log(164pass/2행잠금skip), mariadb-final.log(166pass/0skip). test-summary.json은 각 개별ok/skip과 메서드 수를 대조한 집계다. 기존139개 identity도 모두 남아 있다.
6. concurrency-deploy.log: MariaDB 행잠금 경합2개 별도 통과 후 `manage.py check --deploy --settings=config.test_settings` 경고6개. 배포 보안 통과 로그가 아니다.
7. javascript-final.log: 기존 Node4개 통과.
8. seed_accounts.py: 빈 컨테이너/tmp SQLite와 config.test_settings만 허용. 관리자/영양사/공급업체 계정만 생성하며 실제 업무 데이터는 UI에서 입력한다.
9. browser-service.cjs/result.json: 실제 Chromium의 로그인부터 모든 업무 흐름·업로드·예측·발주·검수·원장·출력·XSS/CSRF·공급업체 차단·관리자 가입승인까지 완주.22 checkpoints는1개 시나리오다.
10. attempt-1: 시나리오 URL오기를 바로잡기 전 증거. attempt-2: 동일 수량의 소수점 문자열 형식 차이로 단언이 멈춘 증거. 제품 결함과 구분한다. 각 실패 후 이번 작업의 tmpfs DB/app만 교체해 최종 시나리오는 처음부터 수행했다.
11. audit_business_data.py/business-data-audit.json: 이번 task 앱의 DB를 읽기만 하여 주문·합격량·원장·FIFO·확정식수·업로드 저장값·다운로드Excel을 독립 단언한다.
12. cooking/vendor-order/settlement PDF 및 TXT/PDFINFO: 실제다운로드/인쇄 산출물. pdftotext로 값 대조. cooking-print.png는 PDF1페이지 렌더. 월간문서는 footer/min-height로2페이지가 생기는 문제를 발견했고, 수정 전 PDF/페이지2 이미지와 수정 후1페이지 PDF를 각각 보존한다.
13. browser-print.cjs/json: 최신 CSS로 로드한 별도 task 앱 프로세스에서 실제 인쇄버튼 호출, 인쇄매체의푸터/상단이동버튼숨김, 본문여백0, PDF 재생성 검증. 이 인쇄 수정 후에도 최종 두DB 전체166개를 재실행했다.
14. runtime.json/tested-source-sha256.json: 실제 환경과 검증 소스 지문. protected-files-before.json/preservation.json은 기존10월보고서·AI모델·requirements·참조파일 보존 및 기존서비스시작시각 대조. cleanup.json은 이번task자원만 정리한 결과.

## 실행 환경/제약

capstone-web:sprint7, Python3.12.13/Django6.0.3, MariaDB10.6/tmpfs, Chromium148.0.7778.96, Node22.22.2. 호스트 Conda/Python 설치는 변경하지 않았다. 오프라인AI 설정과 내부네트워크를 사용했다. 실제SBERT온라인/연구최종모델·정확도·실물프린터·사용자인수·부하를 완료했다고 해석하지 않는다. 업무샘플은 검증일2026-11-04,식단11-06,조회주11-02~08이다. 다른날짜에재현할때는업무일/거래일/조회기간을같이맞춘새테스트DB가필요하다.

전체 판정·수정 파일·잔여위험: `docs/analysis/INTEGRATION_VERIFICATION_REPORT.md`.
