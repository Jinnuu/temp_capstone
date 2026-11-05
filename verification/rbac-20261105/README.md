# 승인·RBAC 검증 증거

2026-11-05, UI 리디자인 브랜치. 기존 인증 증거를 덮어쓰지 않고 이 디렉터리에 새 실행 결과를 저장했다. 계정/DB 백업과 실패 진단은 Git 제외 `.ui-preview/`에만 보관한다.

## 실행 명령

전제: 이 작업에서 만든 `snp-rbac-tests-20261105` 네트워크, `auth-db` 별칭의 일회용 tmpfs MariaDB, `auth-cache` 별칭의 일회용 Redis. MariaDB root 자격증명은 작업별 무작위 값을 담은 Git 제외 `.ui-preview/rbac-test-db.env`에서만 읽었다. 운영 DB/볼륨/네트워크를 사용하지 않았다. 아래 검사가 끝난 뒤 해당 임시 자원은 정리했다. 재실행 시 같은 목적의 **새로운 격리 자원**을 준비해야 하며 운영 호스트명으로 대체하면 안 된다.

```bash
# SQLite; 반환 코드가 0이어야 다음 단계로 진행했다.
docker run --rm --user "$(id -u):$(id -g)" \
  --network snp-rbac-tests-20261105 --read-only --tmpfs /tmp \
  -e DJANGO_SETTINGS_MODULE=config.test_settings \
  -e ACCOUNT_RECOVERY_REDIS_URL=redis://auth-cache:6379/15 \
  -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 \
  -e OMP_NUM_THREADS=1 -e OPENBLAS_NUM_THREADS=1 \
  -v "$PWD:/workspace:ro" -w /workspace --entrypoint sh \
  snp-ui-preview-web:three-modes -ec '
    python -B manage.py check
    python -B manage.py makemigrations --check --dry-run
    python -B manage.py migrate --noinput
    python -B manage.py migrate --check
    python -B manage.py test --verbosity=2
  '
```

MariaDB에서는 같은 명령에 `--env-file .ui-preview/rbac-test-db.env`를 추가하고 settings를 `config.auth_mysql_test_settings`, Redis DB를 `/14`로 바꿨다. 설정은 DB 이름 `snp_auth_verification`, 호스트 `auth-db`로 고정되어 있다. Django가 생성/삭제한 `test_snp_auth_verification`은 이 일회용 DB 안에만 존재했다. 계정/재고 행 잠금 테스트를 포함해 218개 모두 통과했다.

```bash
node --test frontend/tests/*.test.mjs
node --test integration_tests/smart_order.test.cjs
SNP_BROWSER_BASE=http://127.0.0.1:18011 SNP_TEST_MODE=civic \
  SNP_UI_EVIDENCE_DIR=verification/rbac-20261105/business \
  node verification/rbac-20261105/business-flow.cjs
node verification/rbac-20261105/browser-rbac.cjs
node verification/rbac-20261105/browser-recovery.cjs
node verification/rbac-20261105/browser-public.cjs
python3 verification/rbac-20261105/check_preservation.py
python3 verification/rbac-20261105/check_deployed_source.py
```

브라우저 스크립트는 로컬 Playwright/Chromium 경로가 필요하다. 사업 흐름은 기존 검증 스크립트를 복사해 새 증거 경로를 사용하고, 의도적으로 변경한 승인 정책의 옛 Django admin 직접 활성화 단계를 제거했다. 승인/정지/다중 역할은 별도 새 RBAC 시나리오에서 검증한다. 기준정보를 관리자 역할로 준비한 뒤 식단부터 정산까지 DIETITIAN으로 실행하도록 바꿨고 기존 수량·금액·재고 assertion은 유지했다.

`seed_isolated.py`, `seed_recovery_isolated.py`는 DB 엔진/파일명을 검사한 후 합성 사용자만 만든다. 격리 SQLite는 컨테이너 `/tmp` 파일이므로 복구 작업자도 같은 앱 컨테이너에서 실행했다. SMTP 캡처는 기존 `verification/auth-recovery-20261105/mail_capture.py`를 읽기 전용으로 재사용했다. 수신한 메일 본문/링크를 로그나 Git에 저장하지 않았다. 공개 서비스에서는 새 계정 생성이나 비밀번호 변경 없이 기존 시범 계정과 조회만 사용했다.

## 증거 해석

- `sqlite-final.log`: 218개 발견, 215 통과/3 skip.
- `mariadb-final.log`: 218 통과.
- `browser-rbac.json`: 관리자 업무 11개 검증 지점. `*-account-admin.png`는 합성 계정의 세 모드 화면이다.
- `business/browser-result.json`: 하나의 실제 폼 업무 시나리오 21개 지점. XLSX/PDF/PNG는 전부 해당 합성 데이터 산출물이다.
- `browser-isolated.json`: 계정 복구 10개 지점. 격리 SMTP 수신이며 실제 외부 이메일 전송이 아니다.
- `browser-public.json`: 공개 HTTPS 실제 결과. 로그인 요청 간격을 두어 기존 프록시 요청 제한을 존중한다.
- `backup-verification.json`: 비공개 SQL 백업의 해시/크기와 복원 검증 결과만 공개한다.
- `identity_snapshot.py`: 비공개 출력 전용 검사 도구. 출력에 해시/이메일이 있으므로 터미널 로그/공개 산출물로 실행하지 않는다. 이번 실행은 비공개 파일로만 리디렉션했다.
- `verify_restored_migration.py`: 일회용 MariaDB의 `restore_check`에 복원한 기존 스냅샷의 새 migration 검증. Preview DB를 직접 대상으로 삼지 않는다.
- `endpoint-permissions.json`: resolver 전체 GET/POST 정책. 메서드 비허용 URL도 포함한 **권한 요구 표**이며 모든 표 항목의 실제 CRUD 성공을 주장하는 실행 로그가 아니다.
- `deployed-source.json`: 변경된 서버/템플릿 파일과 실제 Preview 이미지 내용 일치 확인.
- `deployment-and-protection.json`: 기존 신원 필드·승인 대상 제한·컨테이너/브랜치 보존·5개 서비스 건강 상태. 외부 사용자가 검증 중 가입한 신규 계정은 별도 수로 표시한다.

## 파일별 변경 이유

| 파일/영역 | 이유 |
|---|---|
| `accounts/models.py`, migrations 0002/0003 | 승인 사유 구분, revision, 정책 mutex, 감사 모델; 기존 데이터 및 그룹 호환 초기화 |
| `accounts/rbac.py`, `backends.py` | 고정 다중 역할, URL별 권한, 상태를 검사하는 Django 인증 backend |
| `accounts/access_service.py` | 트랜잭션/행 잠금, 승인/정지/역할 변경, 관리자 보호, 감사 이벤트 |
| `accounts/access_views.py`, `urls.py` | 관리자 검색·상세·매트릭스·감사 화면 및 직접 요청 보호 API |
| `accounts/admin.py` | 원시 사용자/그룹 조작으로 정책을 우회하지 못하도록 차단 |
| `accounts/views.py`, `auth_forms.py`, `recovery_views.py` | 환경별 가입 상태, 중지 로그인/비밀번호 복구 차단, 기존 복구 절차 보존 |
| `accounts/context_processors.py`, `templatetags/access_tags.py` | 공통 모드 유지, 권한별 메뉴·조회 전용 폼 표시, 가입 정책 안내 |
| `config/business_access.py`, `settings.py`, `preview_settings.py` | 명시적 공개 URL 및 서버 권한 검사, 기본 manual/Preview guard |
| `procurement/workflow_views.py`, `workflow.py` | 하드코딩 staff 검사 대신 앱 권한 사용, 기존 작성자 확정 조건 유지 |
| `templates/accounts/manage_*.html`, `signup.html`, `base.html`, `partials/top_nav.html` | 관리자 UI, 역할 상태, 실제 정책 문구, 메뉴·폼 접근 표시 |
| `compose.ui-preview.yml`, Preview entrypoint | Preview auto 환경 및 정책 변경 감사 동기화; DB/cache 컨테이너 보존 |
| `integration_tests/test_access_management.py` | 신규 25개 승인/권한/보호/동시성 회귀 |
| `integration_tests/test_requirements.py` | 새 명시적 접근 거부 403의 기대값 검사 |
| `integration_tests/test_migrations.py` | historical accounts ORM과 실제 rollback schema 일치 |
| `docs/ui-redesign/` | 정책·행위·제한·실행 증거 및 이전 문서와의 관계 |
| 이 디렉터리 | 재현 도구, 검증 로그·JSON·합성 화면/다운로드 증거 |

공개 build/deployment 로그는 행 끝 공백만 정리했다. 원본 출력은 비공개 감사 디렉터리에 보존했다. 검사 결과·메시지·순서는 변경하지 않았다.
