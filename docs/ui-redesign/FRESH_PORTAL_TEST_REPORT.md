# 영양사 피드백·공급업체 포털·관리자 계층 검증

기준 `e29d9bd`, 작업 브랜치 `feature/ui-redesign-three-modes`. 현재 결과는 과거 218개 기준 보고서에 대한 후속이다. 기존 테스트를 삭제하거나 기대 조건을 약화하지 않았다. 최종 로컬 커밋 SHA는 작업 완료 응답과 Git log를 따른다.

## 실제 실행 결과

| 검사 | 결과 | 증거 (`verification/fresh-portal-20261105/`) |
|---|---|---|
| Django check | SQLite/MariaDB 이슈 0 | `sqlite-final.log`, `mariadb-final.log` |
| migration drift / 전체 migrate / migrate --check | 두 DB 성공, 변경 누락 없음 | 동일 로그 |
| SQLite 전체 | **260개 발견, 256 통과, 0 실패/오류, 4 skip** | `sqlite-final.log` |
| MariaDB 전체 | **260 통과, 0 실패/오류/skip** | `mariadb-final.log` |
| 기존 기준 | 기존 218개 포함 | 전체 로그의 기존 테스트 이름 |
| 신규 포털·관리자·정합성 | 42개 포함. SQLite 행 잠금 1개 skip, MariaDB 전부 통과 | `integration_tests/test_supplier_portal.py` |
| JavaScript 회귀 | 모드 6 + 발주 4 = 10 통과 | `javascript.log` |
| TypeScript/Vite | 빌드 성공 | `frontend-build.log` |
| 기존 영양사 업무 E2E | 1개 시나리오 **21개 검증 지점** 통과 | `business/browser-result.json` |
| 신규 포털/관리자 E2E | 1개 시나리오 **12개 검증 지점** 통과 | `browser-portal.json` |
| 직원 계정 발주처 분리 E2E | **2개 검증 지점** 통과, 위조 ID 저장 안 됨 | `browser-order-identity.json`, `identity-integrity.json` |
| 기존 인증/복구 E2E | **10개 검증 지점** 통과, 격리 SMTP 수신 | `browser-isolated.json` |
| Green/Civic 시각 검증 | 9화면 × 2모드 × 2뷰포트 = **36장** | `screenshots.json`, `screenshots/` |
| 공개 HTTPS | **14개 검증 지점 통과**, 브라우저 오류 0 | `browser-public.json`, `browser-public.log` |
| 백업 복원/업그레이드 | 9계정/기존 migration 50개 복원, 신원·활성·최고관리자 유지 | `backup-verification.json`, `mariadb-final.log` 첫 줄 |
| 실제 Preview 보존 검사 | 기존 신원·권한 플래그/최고관리자/운영 컨테이너 유지 | `deployment-and-protection.json` |

SQLite skip은 기존 관리자 경합 1개·기존 재고 경합 2개·신규 수주 경합 1개다. MariaDB에서 실제 행 잠금을 검증했다. 두 DB의 260개는 같은 테스트 반복이며 520개의 고유 케이스가 아니다. E2E 지점과 스크린샷 수는 테스트 케이스 수로 합산하지 않는다. 실제 영양사의 최종 인수, 부하·전체 침투·접근성 인증을 수행했다고 주장하지 않는다.

## 환경과 격리

Docker의 기존 Preview Python 3.12.13 / Django 6.0.3 및 MariaDB 10.6, Redis 7을 재사용했다. 새로운 Python/프론트엔드 의존성을 설치하지 않았고 호스트 Conda/시스템 Python을 변경하지 않았다. 테스트는 읽기 전용 `/workspace` 마운트와 컨테이너 `/tmp` SQLite 또는 **별도 네트워크의 tmpfs MariaDB**를 사용했다. settings는 `config.test_settings`, `config.auth_mysql_test_settings`다. 실제 Preview DB를 테스트 DB로 연결하지 않았다.

브라우저는 Playwright/Chromium 1223, 1920×1080과 390×844이다. 테스트 앱은 loopback 18011, SMTP 캡처는 loopback 18012를 사용했다. 반복 복구 검사는 테스트 전용 Redis namespace를 분리했다. 실제 Preview 복구 namespace/SMTP 설정은 바꾸지 않았다.

DB 변경 전에 private SQL 백업과 기존 이미지 `pre-fresh-e29d9bd` 태그를 보존했다. `.ui-preview/backups/pre-fresh-portal-20261105.sql`을 별도 tmpfs DB `restore_check`에 복원하고 migration 적용 후 신원/비밀번호/이메일/활성/staff/superuser 및 기존 최고관리자 범위를 비교했다. 원본 덤프와 신원 스냅샷은 비공개·Git 제외다. 실제 운영 DB/볼륨을 읽거나 초기화하는 명령은 실행하지 않았다.

## 핵심 시나리오와 보안

- 영양사/공급업체 가입, 잘못된 가입 유형 및 관리자 필드 위조, 업체/담당자/연락처 필수 검증. Preview 자동 로그인과 manual 승인 보존.
- 미확인 업체의 주문 데이터는 403. 실제 관리자 소속 확인 후에만 기존 거래처 주문에 접근. 동일 상호 자동 생성/자기 소속 승인 차단, 신규 업체 명시 승인, 직원 계정 다중 연결, 직원 재소속 revision/경합 처리.
- A업체의 목록·검색·정렬·JSON·상세·Excel·수주 POST를 B업체 실제 ID로 요청해도 접근 불가. Excel에 같은 업체의 다른 발주도 섞이지 않음. 기존 업체별 구매발주서 산출/문자열 수식 방어 재사용.
- 접수→수락→예정일/예정량→출고 준비→출고 완료, 이유 없는 거절/과거일/음수/NaN/초과/과도한 소수/다른 주문 품목/재고·합격량 필드 주입/오래된 revision 거부.
- 공급업체 예정량 8kg, 실제 납품 8kg, 합격 7kg을 별도로 확인. 출고 전·후 재고를 공급업체가 직접 증가시키지 않으며 **영양사 검수로 7kg 입고 1건**. 중복 검수도 1건 유지. 검수 시작 후 공급업체 변경 차단.
- 과거 `완료`/`배송완료` 발주는 없는 수주 이력을 ‘신규’로 꾸미지 않고 읽기 전용. 실제 이력 없음과 기존 검수 완료를 분리해 표시.
- 관리자 신청은 일반 로그인/역할을 유지. MAIN 승인 시 SUB만 추가, 거절은 일반 계정 유지. SUB의 MAIN/다른 SUB/자기 계정/정책/native admin 조작, SYSTEM_ADMIN 별칭 승격, 직접 API를 차단.
- 공급업체의 SUB 겸임 승인/회수 후에도 업체 포털 범위를 유지. 내부 운영 관리 권한은 별도 영역이다. 공급업체 겸임 SUB의 검수 합격량·재고 쓰기는 예외적으로 차단한다.
- 기존 SYSTEM_ADMIN 하위 호환, 이미 강등된 legacy ADMIN 재승격 방지, 마지막 MAIN/본인 변경 보호, 동시 상호 강등에도 활성 MAIN 유지.
- 직원 로그인 계정이 식재료·규격의 독립 발주처로 노출되지 않음. 위조한 직원 supplier ID로 실제 폼 POST 저장 불가. 레거시 발주처는 보존. 발주 생성/엑셀 업체 조회에도 동일 정책 적용.
- 기존 식단·레시피 업로드, AI 기존 모델 추론, 예측/수동360/확정351 분리, 포장규격, 업체별 발주, 검수, FIFO·재고·수불, 조리지시서 Excel/PDF·재고 미차감, 정산 흐름을 DIETITIAN으로 다시 실행.
- 기존 아이디 소유권 확인·복수 계정 복구·일회성 링크·약한 비밀번호 거부·새 비밀번호 로그인·CSRF·메일 미설정/요청 제한 회귀를 유지.

## 화면 증거

각 행에 `green`/`civic`, `desktop`/`mobile` 조합 4개 PNG가 있다. 전체 경로는 `screenshots.json`에 기록했다.

| 화면 | 파일 이름 접미사 |
|---|---|
| 로그인 | `*-login.png` |
| 가입 유형 선택 | `*-signup.png` |
| 영양사 대시보드 | `*-dietitian.png` |
| 식단 관리 | `*-mealplan.png` |
| 발주 | `*-orders.png` |
| 검수 | `*-inspections.png` |
| 재고 | `*-inventory.png` |
| 공급업체 대시보드 | `*-supplier.png` |
| 관리자 대시보드 | `*-admin.png` |

예: `verification/fresh-portal-20261105/screenshots/green-desktop-dietitian.png`, `civic-mobile-supplier.png`. 모든 화면에서 본문 가로 overflow가 없음을 확인했고, 실제 배너 로딩 및 실패 시 레이아웃 유지도 확인했다. 배너·식수 요약 배치를 실제 화면 확인 후 한 차례 정돈하여 업무 정보를 더 빨리 볼 수 있도록 했다. Reference 선택/기존 사용자의 모드 저장도 유지한다. 원본 DOREMI는 참조만 했으며 상표·연락처를 출력 자산으로 복사하지 않았다.

## 수정 과정에서 확인한 사항

1. 기존 사용자/발주 모델을 직접 덮어쓰면 직원 가입 계정이 기존 업체 FK와 혼동될 수 있어 membership 계층으로 분리했다. 최종 점검에서 직원 계정이 구매자 선택지에 섞일 위험을 발견해 등록 경로 표식·canonical 업체 필터·회귀 테스트를 추가했다.
2. 과거 완료 발주가 새 포털에서 ‘신규’로 보이거나 수정 폼이 나타날 수 있는 표시 문제를 재현 테스트 후 수정했다. 과거 수주 기록을 만들지 않았다.
3. SUB의 native admin 메뉴/경로와 관리자 대상 조회를 서버·화면 양쪽에서 제한했다. 공급업체 겸임자의 직접 재고/검수 쓰기는 별도로 차단했다.
4. 신규 테스트의 전체 HTML 검색이 로그인 헤더의 자기 아이디까지 검사하던 준비 오류, 화면 검증의 선택 날짜 누락, 두 CSRF 필드의 잘못된 브라우저 selector를 수정했다. 업무 결과를 오류에 맞춰 낮추지 않았다.
5. 공개 공급업체에 소속이 없다고 가정했던 하네스를 실제 기존 명시 연결에 맞춰 수정했다. 서비스가 이미 확인된 회사 주문을 올바르게 보여준 것이며, 확인 대기로 강제 변경하지 않았다. 실제 DB의 허용 주문 ID와 공개 API 결과를 읽기 전용으로 비교했다.

중간 진단/실패 출력과 private 범위 자료는 `.ui-preview/audit/fresh-portal-20261105/`에서 보존한다. 최종 로그만 보고 초기 실패가 없었다고 해석하면 안 된다.

## 실제 Preview·데이터 보호

배포는 `snp-ui-preview`의 web/recovery-mail/proxy만 `up -d --no-deps --wait`로 수행했다. DB/cache 컨테이너와 원래 8000/8007/8010의 ID·이미지·시작 시각·PID·마운트·네트워크를 비교했다. `sprint-final`은 `133b950221bd9cc1effaa51539abf7f88bb095c1`로 보존했고 merge/push/PR을 하지 않았다. 다른 Docker 프로젝트를 중단하지 않았다.

기존 9개 계정의 비밀번호·이메일·legacy role·staff/superuser·활성을 보존하고 기존 최고관리자 범위를 비교했다. 새 admin 계정 생성은 사용자가 필요 없다고 확인해 하지 않았다. 원래 실제 사용자의 비밀번호를 요청/추측/변경하지 않았다. 공개 검증은 기존 시범 계정의 로그인/읽기만 사용하고, 실제 신규 가입이나 관리자 임명/업체 연결·검수·재고 변경은 격리 환경에서만 수행했다.

실제 Preview에서 직원 계정이 잘못 발주처로 지정된 발주/식재료/규격이 있는지도 읽기 전용으로 검사한다. 오류가 있으면 자동 재지정하지 않고 보고하도록 검사 스크립트가 실패한다. 결과는 `deployment-and-protection.json`에 있다.

## 미구현·수동 확인·한계

- 실제 업체 실재/담당자 소속 확인은 관리자의 수동 절차다. 상호만으로 소유권을 증명하지 않으며 법적 사업자번호 자동 검증/외부 인증을 만들지 않았다.
- 내부 취소/재발주·분할 반복 출고·반품/재배송 정정은 새로 구현하지 않았다. 수주 거절은 기록하지만 기존 발주를 자동 취소하지 않는다. dashboard는 실제 수주 거절과 기존 검수 완료를 표시하며 없는 취소 수치를 꾸미지 않는다.
- 기존 발주용 업체 계정은 다른 회사로 재소속하지 않고 직원 계정을 별도로 사용한다. 소속 변경·신규 회사 승인에는 사용자 확인 근거가 필요하다.
- 목록·감사·신청은 현재 최대 200개 중심이다. 대규모 페이지네이션·감사 장기 보존/내보내기·세부 권한 편집은 후속이다.
- MAIN 앱 역할과 Django superuser는 다르다. 공지 게시 native admin은 기존 staff 조건과 MAIN 권한이 필요하다.
- 실제 외부 SMTP가 미설정이므로 외부 이메일 수신은 미검증. 격리 SMTP 통과를 외부 발송 성공으로 표시하지 않는다.
- Preview는 영양사 자동 가입 정책을 유지한다. 사용자 유형 선택만으로 실제 영양사 신원까지 인증하지 않으므로 운영 전환에는 manual 정책/실제 조직 확인이 필요하다.
- 공개 HTTPS에서는 기존 시범 계정 로그인/조회/권한 범위를 확인했다. 실계정의 SUB 임명이나 수주·검수 변경을 공개 DB에 만들어 검사하지 않았다.
- 실제 영양사가 새 UI를 다시 인수한 결과, 전체 키보드/스크린리더 인증, 부하·침투 검사는 아직 없다.

## 최종 상태와 정리

공개 HTTPS 최종 시나리오는 14개 지점을 통과했다. 기존 공급업체가 이미 명시적으로 연결된 경우 실제 허용 주문 ID와 포털 JSON을 비교하고 다른 업체의 상세/JSON/Excel은 404임을 확인했다. 기존 영양사 검색 API·로그인/로그아웃·Secure 쿠키·관리자 역할 표·감사 화면 및 SMTP 미설정 동작도 유지됐다. 실제 배포 코드와 CSS/JS/식재료 이미지의 해시가 작업 파일과 일치한다.

기존 9계정과 최고관리자는 보존됐고, 실 DB의 잘못된 직원 발주처 참조는 발주/식재료/규격 모두 0건이었다. Preview 5개 서비스는 healthy다. 소유권과 전용 네트워크를 확인한 테스트 컨테이너 5개와 일회용 네트워크는 정리했다(`test-resource-ownership.json`, `cleanup.log`). 비공개 복구 백업과 이전 이미지 태그는 남겼다. `main`/`sprint-final`을 변경하거나 원격 push하지 않았다.

최근 활동 영역은 본인 계정·포털 감사 기록 중심이며 모든 식단/재고 업무의 전체 타임라인은 아니다. 기존 달력은 식단·예측 중심이고 공급업체 납품은 일정 목록/선택일 입고 KPI에서 확인한다. 발주별 현재 수주·검수 결과는 조회할 수 있지만 별도의 모든 변경 이력 타임라인 UI를 새로 만든 것은 아니다.
