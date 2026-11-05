# SNP 현업 고도화 테스트 보고서

2026-11-06 KST, 시작 HEAD `3ad73a8`, UI 리디자인 브랜치의 Phase 0/1 작업 코드 기준. 아래는 이번에 **새로 실행한** 결과다. 실서비스 계정/DB를 변경하는 업무 테스트는 수행하지 않았다.

## 환경과 격리

기존 `snp-ui-preview-web:three-modes` 이미지의 Python3.12/Django6 환경을 실행 기반으로 재사용하고 **현재 소스를 `/workspace:ro`로 마운트**했다. 운영 이미지를 재빌드/교체하지 않았다. 호스트 Python/Conda 의존성도 변경하지 않았다.

- 네트워크: `snp-hardening-tests-20261106` (현재 작업 전용).
- DB: 새 컨테이너 `snp-hardening-db-20261106`, MariaDB10.6, `/var/lib/mysql` tmpfs. 고정 테스트 host alias `auth-db`와 `snp_auth_verification`만 사용.
- SQLite: 일회용 컨테이너 `/tmp`, 실제 Preview MariaDB와 무관.
- Redis: 새 작업 전용 `auth-cache`, suite별 DB14/15·브라우저13 및 독립 namespace. 기존 복구 큐에 접근하지 않음.
- 브라우저: Chromium1223/Playwright, 작업 전용 Gunicorn+Nginx, `127.0.0.1:18021`, tmpfs SQLite. 1920×1080/390×844.
- 실제 Preview는 사전 SELECT의 비민감 요약과 상태/읽기 확인만 수행. 이번에 공개 HTTPS로 로그인/가입/주문/검수/역할 변경하지 않음.

실행 스크립트는 `verification/nutritionist-hardening-20261106/run_tests.sh`다. 개인 테스트 자격증명은 `.ui-preview/audit/nutritionist-hardening-20261106/test-db.env`에만 있고 값은 보고/커밋하지 않는다.

## 새 실행 결과

| 검사 | 이번 결과 | 증거 (verification/nutritionist-hardening-20261106/) |
|---|---|---|
| 최초 결함 재현 | 신규18개: 2통과·15FAIL·1ERROR | `p0-before.log` |
| 해당18개 수정 후 | 18통과 | `p0-after.log` |
| 관리자 안전 도구 구현 전 | 12개 중10ERROR(아직 없는 기능), 나머지2 기존 방어 통과 | `admin-before.log` |
| 중간 대상 검사 | 39통과 | `targeted.log` |
| native admin/빈 메뉴 재현 | 2FAIL 후 보호/탐색 개선 | `admin-ui-before.log` |
| 빈 월 품목 수 재현 | 1FAIL 후 실제0으로 수정 | `empty-month-before.log` (응답 HTML은 임시 CSRF 토큰 보호를 위해 제외) |
| 업체 삭제 업무 거부 감사 재현 | 1FAIL 후 연결된 업체 보존·DENIED 감사 추가 | `delete-audit-before.log` |
| 최종 Django check | SQLite/MariaDB 각 issues0 | `sqlite-final.log`, `mariadb-final.log` |
| migration drift | 두 DB No changes detected | 동일 로그 |
| 전체 migrate/migrate --check | 격리 두 DB 통과 | 동일 로그 |
| **SQLite 전체** | **309발견 / 305통과 / 0FAIL·ERROR / 4skip** | `sqlite-final.log` |
| **MariaDB 전체** | **309통과 / 0FAIL·ERROR·skip** | `mariadb-final.log` |
| JS 회귀 | 10통과 / 실패0 | `javascript.log` |
| TypeScript/Vite | build 성공 | `frontend-build.log` |
| 기존 영양사 업무 E2E 재실행 | 하나의 시나리오21검증 지점 통과 | `business-green/browser-result.json`, `business-browser.log` |
| 공급업체/관리자/영양사 E2E 재실행 | 하나의 시나리오12검증 지점 통과 | `browser-portal.json`, `portal-browser.log` |
| 새 P0 브라우저 | 하나의 시나리오8검증 지점 통과 | `browser-hardening.json`, `hardening-browser.log` |
| Green/Civic 시각/반응형 | 9화면×2모드×2뷰포트=36PNG 재촬영, 추가 개선 화면4PNG | `portal-screenshots/`, `green/civic-dashboard.png`, `green/civic-mobile.png` |
| 확대/키보드 smoke | 2모드 CSS zoom200%, 본문 overflow 없음·Tab으로 조작 요소 접근 | `accessibility-smoke.json`, `*-css-zoom200.png` |

기존 기준은 260개 고유 Django 테스트이고 이번 신규는 **47개**다. 309개를 두 DB에서 반복한 것이며 618개 고유 테스트가 아니다. 브라우저21/12/8은 단계·검증 지점 수이고 Django 케이스 수에 합산하지 않는다. 확대 smoke는 브라우저 native zoom 설정과 다르며 전체 화면·대비·스크린리더·WCAG 인수 검사가 아니다.

SQLite skip4개는 기존 DB 행 잠금/경합 테스트다. 같은 검사는 MariaDB에서 실행됐다. 새 요구를 통과시키려고 기존 테스트를 삭제하거나 기대값을 낮추지 않았다.

## 주요 회귀 범위

- MAIN→공급업체 겸 SUB/일반 업체 허용, SUB→일반 업체 허용, SUB→공급업체 겸 MAIN/SUB/자기 관리자 계정 차단. 프로필 신규 연결·수정·삭제 및 기존 계정 폼 모두 검사. 거부 감사 지속 및 정상 감사 확인.
- 공급업체 겸 SUB의 내부·포털 경계, 타 업체 IDOR/JSON/Excel/POST, 소속 대기/승인, MAIN 신청 승인/거절·마지막 관리자/경합, 기존 인증·일회성 복구 회귀 유지.
- 관리자 rename 도구의 기본 dry-run·정확한 PK 요구·충돌·반복 실행·역방향 rollback, 같은 PK/암호/이메일/상태/그룹·권한 보존. 기존 발주/공지/관리자 신청·감사 FK/역사 라벨 보존. **실제 Preview 계정이 아니라 synthetic DB에서 수행**.
- bootstrap의 별도 비밀·빈/같은 초기 비밀 원자 실패·기존 MAIN 재사용·기존 비밀번호 유지·이름 충돌 차단. 실제 비밀번호 회전은 수행하지 않음.
- 실측 None/0/양수/잘못된 legacy 음수, 미예측/최신 예측, AI/수동/최종/실측 네 값, HTML/JSON/Excel 의미 일치. 실측 입력 UI·입력 책임자는 후속.
- 완료 식단 단일/다중 업로드 rollback, 레시피 업로드 rollback/레거시 폼 보존, AJAX 변경 발주 재검토, 참조 식단 삭제 방지·native admin 보호.
- 동명 업체 ID 집계, 임의10% 제거·최종 지급액 미확정, 부분 합격 금액·0/음수/NaN 경계, 빈 월 품목 수0.
- 기존 실제 모델 로드/추론, 금요일·주말·중복 재료/안전재고·명시적 규격·합격량 입고·중복 검수·FIFO/수불·조리지시서16개/예시6시트·Excel/PDF·재고 미차감 흐름 회귀 유지.

## 실제 실행 명령

작업 소유 테스트 리소스를 먼저 생성해야 한다. 현재 작업 종료 시 정리하므로 실행 스크립트만으로 DB/네트워크가 다시 생기는 것은 아니다. 기존 DB/소켓/운영 네트워크로 대체하면 안 된다.

```sh
bash verification/nutritionist-hardening-20261106/run_tests.sh
bash verification/nutritionist-hardening-20261106/run_tests.sh config.auth_mysql_test_settings
npm --prefix frontend run build
node --test frontend/tests/*.test.mjs integration_tests/smart_order.test.cjs
SNP_BROWSER_BASE=http://127.0.0.1:18021 SNP_TEST_MODE=green \
 SNP_UI_EVIDENCE_DIR=verification/nutritionist-hardening-20261106/business-green \
 node verification/fresh-portal-20261105/business-flow.cjs
node verification/nutritionist-hardening-20261106/browser-portal.cjs
node verification/nutritionist-hardening-20261106/browser-hardening.cjs
node verification/nutritionist-hardening-20261106/browser-accessibility.cjs
```

Browser seed 파일은 정확한 일회용 SQLite 엔진·파일을 검사한다. 추가 hardening fixture는 `SNP_HARDENING_BROWSER=1` opt-in도 요구한다. 테스트 날짜/합성 데이터가 고정되어 있으므로 미래 재실행 시 납품 예정일을 현재 업무 규칙에 맞춰 새로 준비해야 한다. 테스트의 시간 검증을 없애는 방식으로 재실행하지 않는다.

## 환경 오류와 해결 기록

첫 MariaDB 시도는 새 빈 DB 서버에 테스트 base database가 없어 실패했다. **새 작업 소유 MariaDB에만** base DB를 생성했다. 초기 두 전체 실행은 컨테이너 UID10001이 사용자 소유 참고 Excel을 읽을 수 없어 조리 모듈 import에 실패했다. 참고 파일/권한/테스트를 완화하지 않고 기존 검증 방식대로 호스트 UID/GID로 실행했다. 로그는 `mariadb-setup-failure.log`, `sqlite-permission-failure.log`, `mariadb-permission-failure.log`에 보존한다.

브라우저 초기 준비에서는 seed 스크립트의 Python import path, Gunicorn control socket의 read-only 홈 문제를 확인했다. 임시 앱에만 PYTHONPATH·`--no-control-socket`을 적용했다. 제품/기존 서비스 설정을 바꾼 것이 아니다. `browser-setup.log`에 진단 기록을 남겼다. 정상 실행 이후 해당 setup 오류를 성공으로 집계하지 않았다.

## 미실행/미검증

- 실제 Preview의 관리자 rename·비밀번호 변경·승인 모드 전환·새 버전 공개 배포/재검증: 승인 대기.
- 신규 반복 분납·반품·취소/재발주·발행 snapshot·스키마 변환: 미구현이므로 테스트 완료 아님.
- 실제 SMTP 수신: 미설정. 기존 격리 메일 회귀는 외부 발송 증거가 아님.
- AI의 실제 현장 정확도·신규 DB 메뉴 입력 호환성·실측 수집: 미검증. 기존 추론 성공과 구분.
- 실제 영양사/업체 인수, 전체 native zoom200%·스크린리더·고령 사용자 테스트, 부하/장애/전체 침투 테스트: 미실시.
- 새 migration은 없으므로 신규 분납/문서 이력 data migration 호환성을 검증했다고 표시하지 않는다.

보호 비교/정리 결과는 같은 증거 폴더의 `protection.json`, `cleanup.json` 및 운영 준비도 문서를 따른다.

## 보호 비교 보충

보호 컨테이너8개의 ID/이미지/시작 시각/네트워크·마운트는 동일하다. 최초 비교는 Docker가 반환한 recovery-mail Mounts 배열 순서만 달라 false였고 원본은 protection-initial.json에 보존했다. 마운트 destination으로 정렬해 모든 값이 같은 것을 확인했다. 계정 요약/승인 정책도 동일하다. 전체 업무 row 내용의 DB 감사는 아니다.

공개 로그인 GET은 curl200, Python urllib403이었다. 클라이언트별 응답 차이의 원인은 이번에 진단하지 않았고 새 공개 브라우저/인증 성공으로 집계하지 않는다. 원래8000/8007/8010 로그인 GET은200이다. 격리 SQLite의4재료는 stock/lot 잔량이 일치하고 음수가 없었다(stock-consistency.json).

## 최종 호환성 검토에서 발견한 회귀 예방

새 money helper가 합격량을 발주량 이하로 제한하면 기존 inspect_item이 사유와 함께 허용하는 초과 납품을 정산 화면에서 거절할 수 있음을 확인했다. 발주3/실납4/합격4와 사유를 격리 DB에 기록하는 재현은 helper에서 실패했다(overdelivery-before.log). 기존 검수 정책을 변경하지 않고 보고 helper의 새 상한만 제거했다. 최종 신규 테스트는 합격량 금액과 실제 월말 정산 View 응답/금액을 두 DB에서 검증한다.

브라우저21/12/8 지점은 정상 납품량 경로의 새 실행 증거이며, 마지막 초과 납품 보정 자체의 근거는 최종 Django ORM/View 회귀다. 실제 공개 서비스에서는 초과 납품/검수/계정 변경을 실행하지 않았다.
