# UI 3모드 검증 보고서

검증일: 2026-11-05 KST. 작업 브랜치 `feature/ui-redesign-three-modes`; 안정 기준 `133b950221bd9cc1effaa51539abf7f88bb095c1`. 실제 ZIP 확인 후 구현했으며 MODE 2는 사용자 확인에 따라 레퍼런스를 녹색으로 해석했다. 포스터 재현을 주장하지 않는다.

## 환경과 보호

- Docker `capstone-web:sprint7`, Django 5.2.8, 기존 AI 패키지/모델 그대로. 저장소 read-only bind, 임시 `/tmp` SQLite, 네트워크 격리 MariaDB 10.6 Unix socket.
- 브라우저는 실제 Playwright Chromium, 1920×1080 데스크톱과 768×1024 태블릿. 외부 CDN 없이 동작.
- 작업 전 미커밋 코드는 없었고 사용자 ZIP 한 개가 미추적 상태였다. ZIP는 그대로 보존·Git 제외했다.
- `snp-ui-modes-20261105` 앱과 동명의 새 네트워크, `snp-ui-db-20261105` DB만 작업용으로 생성했다. 기존 서비스/볼륨/네트워크는 변경하지 않았다.
- 기존 sprint-final 브랜치 포인터, 업무/모델 파일 해시, ZIP 해시, 기존 서비스 시작 시각 비교: `verification/ui-three-modes-20261105/protection-final.json`.
- DB 모델·마이그레이션·AI·업무 계산 변경 없음. Django 추가는 비교 페이지와 제한된 같은 출처 프레임 허용 미들웨어뿐이다.

## 자동화 결과

| 검사 | 실행 결과 | 증거 |
|---|---|---|
| Django check | SQLite/MariaDB 모두 오류 0 | sqlite-final.log, mariadb-final.log |
| makemigrations --check --dry-run | 양쪽 No changes detected | 같은 로그 |
| 빈 SQLite migration / migrate --check | PASS | sqlite-final.log |
| 격리 MariaDB migration / migrate --check | PASS | mariadb-final.log |
| Django 전체 SQLite | **176개 중 174 통과, 2 skip, 실패 0** | sqlite-final.log |
| Django 전체 MariaDB | **176개 통과, 실패 0** | mariadb-final.log |
| 기존 JS 회귀 | **4 통과** | javascript-final.log |
| 모드 부팅 JS 단위 | **6 통과** | frontend-unit.log |
| TypeScript 검사 + Vite production build | PASS | frontend-build.log |
| npm audit (개발 의존성 포함) | 알려진 취약점 0 | npm-audit.json |
| 업무 E2E | 3모드 각각 1개 시나리오, 각22 확인 지점 통과 | flows/*/browser-result.json, run.log |
| UI 전용 E2E | 1개 시나리오, 16 확인 지점 통과 | ui-result.json, ui-run.log |
| 조리지시서 인쇄 | 3모드 모두 A4 1쪽, 텍스트/수량 동일 | print-validation.json, *-cooking.pdf |

동일 Django 176개를 DB별로 반복한 것이므로 고유 테스트 352개라고 합산하지 않는다. 기준 166개에서 UI 계약 10개를 추가했다. SQLite skip 2개는 DB 잠금에 의존하는 동시성 테스트이며 MariaDB에서 실행·통과했다. E2E 확인 지점은 독립 테스트 케이스 수가 아니다. 실제 영양사 사용자 인수 시험은 별도다.

## 실제 업무 시나리오 (각 모드에서 새 임시 DB)

1. 로그인·대시보드 이동 → 공급업체 2개 등록·재조회.
2. 식자재 2개 kg 기준 등록/검색/수정 폼 재조회.
3. 5kg/캔·3kg/판 명시적 납품규격, 별도 포장 단가 설정.
4. 메뉴/레시피 작성, 기준 100g 단위를 기존 메뉴 편집기로 다시 저장해 유지 확인.
5. 레시피·식단 Excel 실제 폼 업로드, 일간 저장, 주간 다음 월요일 메뉴 추가/제거.
6. 미확정 식수 발주 경고 → 기존 AI 추론 → 수동 360 / 최종 351 확정. AI 값은 별도 표시.
7. 재료별 35.1kg: 참치 최소8캔을9캔으로 조정, 두부12판. 업체별 주문/금액/Excel 확인.
8. 검수 전 재고 0 → 납품45/합격40kg, 두부36kg. 같은 검수 재제출로 중복 입고되지 않음.
9. 참치 2kg 추가입고 → FIFO 사용35.1kg → 폐기1kg. 수불 `0+42−35.1−1=5.9`, 두부 `36−35.1=0.9`.
10. 조리지시사항 저장/재조회, Excel/PDF, 재고 변동 없음. 월 정산 발주금액과 합격량 기준 금액 구분.
11. 미사용 메뉴 삭제, XSS 문자열 이스케이프, CSRF 누락403, 공급업체 업무접근403, 가입 후 관리자 활성화.

기존 업무 assertion을 그대로 유지했다. 새 공통 헤더가 추가한 검색 폼 때문에 가입 제출 locator를 해당 가입 폼으로 한정했고, 메뉴 페이지 이동 직후 hidden 단위 필드 조회는 attachment를 기다리도록 했다. 기대 계산값은 변경하지 않았다.

## UI 고유 검증

- 세 모드 레이아웃 geometry 차이 확인, 같은 업무 DOM/표 텍스트 유지.
- 저장하지 않은 407/399 입력, checkbox, 선택 파일이 전환 후 유지. 같은 입력 노드 객체임도 확인.
- Home/방향키 선택, aria-pressed, 페이지 이동·별도 Chromium 프로세스 재실행 후 선택 유지.
- 6개 업무 화면을 선택할 수 있는 비교 창: 실제 same-origin Django 화면, 프레임별 모드 고정, 폼 비활성화, 부모 저장 모드 불변.
- 768px에서 메뉴 열기/Escape 닫기 및 본문 가로 넘침 없음. 넓은 표는 영역 스크롤.
- 인쇄 시 공통 chrome 제거, 세 문서 추출 텍스트 해시 동일.
- Django admin 기본 구조/계정 활성화 보존.

### 검증 중 수정한 UI 문제

| 문제 | 해결 |
|---|---|
| 검색 버튼 줄바꿈 | 검색 입력 flex + 버튼 최소 너비 |
| 기존 스타일이 모드별 배치를 덮음 | shell 범위 selector 우선순위 명확화 |
| 레거시 파란 배경/중앙 제목 잔존 | 새 토큰 배경·모드별 제목·링크 적용 |
| 비교 iframe가 Django 기본 DENY로 차단됨 | 허용 조회 6개 + 인증 GET + snp_preview=1만 SAMEORIGIN, 나머지 DENY 유지. 3개 정책 테스트 추가 |
| 모든 메뉴가 펼쳐져 정보 과밀 | 현재 업무군 자동 펼침, 다른 업무군 접기 |

## 재실행 명령

```sh
npm ci --prefix frontend
npm run build --prefix frontend
npm test --prefix frontend
node --test integration_tests/smart_order.test.cjs
bash scripts/verify_integration.sh
SPRINT7_DB_SOCKET_DIR=/tmp/작업전용소켓 bash scripts/verify_integration.sh config.test_mysql_settings
```

마지막 명령은 **새로 만든 작업 전용 MariaDB**가 준비된 경우에만 사용한다. 실행 스크립트의 DB 설정 allowlist와 `--network none --read-only --tmpfs /tmp`를 유지했다. 업무 브라우저 실행 방법은 `verification/ui-three-modes-20261105/README.md` 참조. 브라우저용 앱은 같은 이미지·읽기 전용 저장소·임시 DB로 실행하고, 계정 전용 seed 이후 화면에서 데이터를 만든다. 실제 DB를 복제하거나 초기화하지 않는다.

## 스크린샷

`screenshots/{reference,green,civic}-{dashboard,inventory,headcount,procurement,ledger,cooking,mealplan,recipe}.png`: 같은 DB/URL 데이터, **24장** 1920×1080 PNG.

`screenshots/comparison.png`: 나란히 비교. `screenshots/{reference,green,civic}-tablet.png`: 768×1024. 총 **28장**. 합성·실데이터·개인정보 없음. 개발 중 빈 대시보드 캡처는 최종 산출물에서 제외했다.

## 남은 확인 및 한계

- 실제 영양사 디자인 선택 및 장시간 사용성 인수는 미실시. 디자인 후보이며 상용 인증 완료를 의미하지 않는다.
- Chromium 외 Safari/Firefox, 실제 태블릿 터치, 전체 WCAG/스크린리더, 부하·대용량 모든 표 조합은 미검증.
- 관리자 화면은 기본 Django 레이아웃을 유지한 별도 최소 테마다.
- 원래 폼/문서의 데이터 표시·예외 문구는 보존했으므로 모든 개별 템플릿을 새 컴포넌트로 재작성한 것은 아니다. 화면별 모든 CRUD/필터 조합을 E2E로 전수 통과했다고 주장하지 않는다.
- 비교 창은 축소 조회 전용. 저장/업로드는 일반 화면에서 수행한다.
- 실제 서비스 실행·배포는 하지 않았다. 새 브랜치만 push하며 sprint-final로 병합하지 않는다.

## 검증용 앱 생성 예시

아래 예시는 전용 내부 네트워크와 메모리 SQLite를 사용한다. 동일 이름의 자원이 이미 있으면 재사용하거나 삭제하지 말고 다른 작업용 이름을 정한다. 외부 포트를 노출하지 않는다.

```sh
docker network create snp-ui-review-local
docker run -d --name snp-ui-review-local --network snp-ui-review-local \
  --read-only --tmpfs /tmp \
  -e PYTHONDONTWRITEBYTECODE=1 -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 \
  -e OMP_NUM_THREADS=1 -e OPENBLAS_NUM_THREADS=1 -e PYTHONPATH=/tmp/deps:/workspace \
  -v /tmp/sprint7-test-wheels:/wheels:ro \
  -v "$PWD:/workspace:ro" -w /workspace --entrypoint sh capstone-web:sprint7 -c '
    set -eu
    python -m pip install --no-index --no-deps --target /tmp/deps /wheels/xlrd-2.0.2-py2.py3-none-any.whl /wheels/xlwt-1.3.0-py2.py3-none-any.whl
    python -B manage.py migrate --noinput --settings=config.test_settings
    python -B verification/comprehensive-20261104/seed_accounts.py
    python -B manage.py runserver 0.0.0.0:8000 --noreload --settings=config.test_settings'
docker inspect snp-ui-review-local --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'
```

서버 준비 완료 후 표시된 **작업용 IP**로 브라우저 시나리오를 실행한다. 실행마다 새 빈 임시 DB가 필요하므로 3모드 업무 시나리오는 전용 앱을 각각 새로 만든다. 이후 UI 고유 시나리오는 마지막 앱의 QA 데이터를 사용한다. 종료 시 자신이 생성한 앱/네트워크만 정리한다. 본 작업에서 생성한 임시 자원은 검증 후 모두 정리했다.
