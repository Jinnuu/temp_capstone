# Fresh UI / supplier portal / admin hierarchy evidence

실행일 2026-11-05 KST. 시작 HEAD e29d9bd. 정책·기능 설명은 `docs/ui-redesign/FRESH_PORTAL_IMPLEMENTATION.md`, 판정·제한은 `FRESH_PORTAL_TEST_REPORT.md`에 있다. 원본 DOREMI 이미지와 SQL 백업/자격증명/실계정 스냅샷은 Git에 넣지 않는다.

## 실제 DB 검증 명령

작업 소유 리소스: `snp-fresh-tests-20261105` 네트워크, `auth-db` 별칭의 tmpfs MariaDB, `auth-cache` 별칭의 일회용 Redis. `.ui-preview/fresh-test-db.env`는 이 테스트 DB만 위한 무작위 자격증명이며 내용은 기록하지 않는다. 기존 운영 DB 주소/소켓/볼륨을 사용하지 않는다.

```bash
docker run --rm --user "$(id -u):$(id -g)" \
  --network snp-fresh-tests-20261105 --read-only --tmpfs /tmp \
  -e DJANGO_SETTINGS_MODULE=config.test_settings \
  -e ACCOUNT_RECOVERY_REDIS_URL=redis://auth-cache:6379/15 \
  -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 \
  -e OMP_NUM_THREADS=1 -e OPENBLAS_NUM_THREADS=1 \
  -v "$PWD:/workspace:ro" -w /workspace --entrypoint sh \
  snp-ui-preview-web:pre-fresh-e29d9bd -ec '
    python -B manage.py check
    python -B manage.py makemigrations --check --dry-run
    python -B manage.py migrate --noinput
    python -B manage.py migrate --check
    python -B manage.py test --verbosity=2
  '
```

MariaDB는 동일 명령에 `--env-file .ui-preview/fresh-test-db.env`를 추가하고 settings를 `config.auth_mysql_test_settings`, Redis DB를 14로 바꿨다. `config.auth_mysql_test_settings`는 `auth-db`/`snp_auth_verification`으로 고정된다. 기존 네트워크를 운영 DB에 연결해 재사용하면 안 된다. 테스트 후 이 자원을 정리했으므로 재실행에는 새 격리 환경이 필요하다.

`verify_restored_migration.py`는 백업을 복원한 일회용 `restore_check`만 업그레이드한다. 기존 계정 9개·migration 50개와 신규 migration의 호환성을 검증했다. 실제 비밀번호/이메일은 private 비교에만 쓰고 출력하지 않는다.

## 브라우저와 프론트엔드

```bash
npm --prefix frontend run build
node --test frontend/tests/*.test.mjs integration_tests/smart_order.test.cjs
SNP_BROWSER_BASE=http://127.0.0.1:18011 SNP_TEST_MODE=green \
  SNP_UI_EVIDENCE_DIR=verification/fresh-portal-20261105/business \
  node verification/fresh-portal-20261105/business-flow.cjs
node verification/fresh-portal-20261105/browser-portal.cjs
node verification/fresh-portal-20261105/screenshots.cjs
node verification/fresh-portal-20261105/browser-order-identity.cjs
node verification/fresh-portal-20261105/browser-recovery.cjs
node verification/fresh-portal-20261105/browser-public.cjs
python3 verification/fresh-portal-20261105/check_preservation.py
python3 verification/fresh-portal-20261105/check_deployed_source.py
```

Playwright와 Chromium은 이전 작업의 로컬 설치 경로를 재사용한다. 격리 app/proxy는 loopback 18011, SMTP 캡처는 18012다. app은 `config.auth_test_settings`, `ACCOUNT_APPROVAL_MODE=auto`, 별도 `ACCOUNT_RECOVERY_NAMESPACE`를 사용한다. SQLite 파일은 앱의 `/tmp`에 있으므로 메일 작업자는 동일 앱 컨테이너에서 실행한다. 메일 캡처는 `verification/auth-recovery-20261105/mail_capture.py`를 읽기 전용 재사용한다. 외부 이메일 발송이 아니다.

`seed_isolated.py`는 SQLite 엔진/정확한 임시 파일명/빈 사용자 테이블을 확인한 후 합성 계정·두 업체·주문만 만든다. 기존 business-flow의 수량·단위·예측·재고·정산 assertion은 보존하고 새 관리자 로그인 진입 URL만 반영했다. 새로운 포털/관리자 신청/역할 흐름은 `browser-portal.cjs`에서 실제 폼으로 검사한다. 마지막 등록 경로/발주처 분리 변경 후 테스트 앱을 새로 만들고 기존 업무·포털·사진·복구 검증을 다시 실행했다. 운영/Preview DB를 테스트 seed 대상으로 사용하지 않았다.

`browser-order-identity.cjs`의 private fixture 파일은 격리 회원의 ID/아이디만 제공한다. 직원 계정을 발주처로 위조 제출해도 실제 폼에서 저장하지 않는지 검사한다. `identity-integrity.json`은 저장되지 않았음을 별도 확인한 결과다.

`browser-public.cjs`는 기존 시범 계정의 HTTPS 로그인/조회만 사용한다. 기존 공급업체의 명시적 연결 여부와 허용 주문 ID는 private 파일로 읽기 전용 비교한다. 미확인으로 강제 바꾸거나 실계정 SUB 임명/실제 주문·재고 변동을 수행하지 않는다. 로그인 요청 간격을 두어 기존 Nginx 제한을 존중한다. SMTP 미설정은 명시적으로 503이어야 한다.

## 결과와 해석

- `sqlite-final.log`: 260개 중 256 통과, 행 잠금 4 skip.
- `mariadb-final.log`: 260개 전부 통과. 신규 등록 경로 migration을 포함한 복원 DB 검사도 첫 줄에 기록한다.
- `business/browser-result.json`: 21개 지점의 하나의 실제 업무 흐름.
- `browser-portal.json`: 12개 지점의 하나의 공급업체·관리자·영양사 시나리오.
- `browser-order-identity.json`: 실제 발주처 폼의 직원 제외/직접 위조 차단 2개 지점.
- `browser-isolated.json`: 계정 복구 10개 지점, 격리 SMTP 수신.
- `screenshots.json`: Green/Civic × 9화면 × 2기기 = 36 PNG.
- `stock-integration.json`: 예정8/실납품8/합격7/입고1건, Supplier 상태가 검수를 대신하지 않음.
- `deployment-and-protection.json`: 실제 Preview 기존 계정/최고관리자/운영 서비스 유지와 잘못된 직원 발주처 참조 검사.
- `deployed-source.json`, `deployed-assets.json`: 실제 배포 코드/템플릿/CSS/JS/사진과 체크아웃 동일성.
- `backup-verification.json`: private 백업의 해시/크기/복원 검증만 기록한다.

실패한 중간 출력, 계정 원문, 메일/토큰 진단은 Git 제외 private 감사 디렉터리에 보관한다. 공개 build/deployment 로그의 행 끝 공백만 정리하며 원본은 private 보존한다. 테스트 단계/뷰포트 캡처 수를 고유 테스트 케이스 수로 합산하지 않는다.

## 변경 파일과 이유

| 파일/영역 | 이유 |
|---|---|
| `accounts/rbac.py`, `access_service.py`, `access_views.py` | MAIN/SUB 계층, 별칭 호환, 관리자 대상 보호·스코프·감사·동적 공급업체 예외 |
| `accounts/models.py`, `admin_requests.py`, `request_views.py`, `urls.py` | 관리자 신청·심사·공지·운영 대시보드 |
| `accounts/views.py`, `workspaces.py`, `context_processors.py` | 가입 유형·거절 불가능 권한 필드·역할별 진입/업무 영역/역할 표시 |
| `accounts/supplier_identity.py` | 포털 직원과 기존 발주용 업체 계정의 분리 |
| `accounts/admin.py` | MAIN 전용 실제 DB 공지 게시·감사 |
| `procurement/models.py`, migrations 0010/0011/0012, accounts 0004 | 공급업체 소속·수주·예정량·신청·공지 모델, 레거시 관리자/업체 연결 보존, 등록 경로 분류 |
| `procurement/portal_services.py`, `portal_views.py`, `urls.py` | 검증·객체별 격리·상태 전이·revision·전용 화면/JSON/Excel |
| `procurement/views.py` | 기존 구매발주서 계산/Excel에 단일 발주 범위 옵션 추가, 기본 동작 유지 |
| `procurement/workflow.py` | 직원에게 잘못 발주 방지, 공급업체 검수/재고 쓰기 방어 |
| `procurement/workflow_forms.py`, `supplier_views.py`, `workflow_views.py`, `inventory/forms.py`, `inventory/release_patch_views.py` | 실제 발주처 선택/업로드 연결에 직원 제외, 연결된 프로필 삭제 안내, 납품 예정 정보 표시 |
| `config/business_access.py`, `config/views.py` | native admin MAIN 제한, 공급업체 홈 분리, 실제 DB KPI/식수/공지/본인 활동 |
| `config/auth_test_settings.py` | 반복 격리 브라우저의 복구 namespace 분리, 기본값은 기존과 동일 |
| `frontend/src/main.ts`, `ui.css`, `static/ui/build/*` | Green/Civic, 가입 정보 표시, 반응형·인쇄·선택 유지 |
| `static/ui/images/*` | 새 원본 생성 식재료 이미지와 출처 |
| `templates/accounts/*`, `templates/portal/*`, `templates/base.html`, `home.html`, `partials/top_nav.html`, `workflow/form.html`, `admin/base_site.html` | 실제 기능 화면·권한 표시·모드/캐시·사진·역할 차이 |
| `integration_tests/test_supplier_portal.py` | 42개 신규 기능/정합성/보안/동시성 테스트 |
| `.gitignore`, `.dockerignore` | 개인정보/브랜드가 포함된 원본 DOREMI를 커밋·빌드 자산에서 제외 |
| `docs/ui-redesign/*`, 이 디렉터리 | 정책/근거/실행 결과/소스/합성 화면·출력 기록 |
