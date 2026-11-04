# 2026-11-04 후속 통합 실행 증거

- sqlite-baseline.log: 복구 브랜치 1aa6302를 /tmp에 git archive로 추출한 수정 전 실행. 117개 중115 통과/1 실패/1 skip. 참조 Excel은 Git archive에 포함되지 않아 구조 비교1개 skip. 만료 테스트의 고정10월 식단/실행일 상대 날짜 불일치 실패를 재현했다.
- sqlite-first.log, sqlite-tests.log, mariadb-tests.log: 충돌 통합 및 신규 테스트 보완 중간 실패 이력. 최종 결과로 사용하지 않는다.
- sqlite-final.log, mariadb-final.log: 최종139개(기존117+신규22), 각각139 통과/0 실패/0 skip. check, makemigrations --check --dry-run, migrate, migrate --check도 포함.
- javascript.log: 기존 Node4개 통과.
- browser_cooking.cjs: 기존 integration_tests/browser_cooking.cjs에서 산출물 경로만 이 폴더로 바꾼 실행본. cooking/에 Excel/PDF/JSON/PNG 보존.
- browser_workflow.cjs: 기존 시나리오의 산출물 경로와 테스트 날짜만 11월6일/11월2~8일로 변경. 오래된10월 출고일과11월 입고일을 섞지 않기 위한 격리 fixture 조정. 실제 기존 테스트 원본은 변경하지 않았다.
- browser-fixture-date.log: 이번에 생성한 임시 SQLite의 테스트 식단 날짜 변경만 수행. 실제 DB 접근 없음.
- browser-team2.cjs/json/log: 새 업체·월간 문서·품목 수정·기간 조리지시서의 저장/재조회/연결/재고 불변 검증.8 checkpoints는1개 시나리오다.
- browser-cooking.log, browser-workflow.log, browser-team2.log는 모두 최종PASS. 호스트 포트의 첫 접속 실패는 내부 Docker 네트워크 IP로 접속하여 해결했다.
- preservation.json: 기존 핵심 계산·AI 모델3개·requirements·업로드·차감·조리지시서 서비스의 바이트 동일성 확인.

Docker image capstone-web:sprint7 / Python3.12.13 / Django6.0.3. 테스트 시 pip는 컨테이너/tmp/deps에만 로컬 xlrd/xlwt wheel을 설치했다. 호스트 Python/Conda 패키지는 수정하지 않았다. DB는 새 tmpfs MariaDB10.6와 컨테이너/tmp SQLite뿐이다. 브라우저는 headless Chromium이며 외부 HTTPS와 모델 다운로드를 차단했다. 실제 영양사 인수, 온라인 SBERT 전체 경로, 동시 부하, 실제 프린터 품질은 이 결과로 보장하지 않는다.
