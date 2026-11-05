# 인증·계정 복구 구현 및 중단 작업 재개 검증

대상: `feature/ui-redesign-three-modes`, UI Preview8011 / `https://ui.jinnuu.site`. 원격 push 금지. 기준 커밋231184e의 기존 기능과 미커밋 구현을 보존해 재개했다.

## 확인된 로그인 실패 원인

사용자가 제시한 두 계정 모두 DB의 is_active=False, 사용 가능한 비밀번호 해시 존재, 이메일 미등록이었다. 승인 대기 계정은 기존 ModelBackend 정책상 로그인할 수 없다. 비밀번호 자체의 정확성은 제공받거나 확인하지 않았다. 두 계정을 임의로 활성화/수정하지 않았다.

동일 서비스의 기존 활성 테스트 계정은 올바른 비밀번호로302/로그인 성공, 잘못된 비밀번호는200/폼 오류였다. 따라서 승인 정책에 따른 차단을 프론트엔드·세션·HTTPS 전체 장애로 판단하지 않았다. 기존 화면은 비활성도 일반 비밀번호 오류로 표시해 원인을 설명하지 못했다. 올바른 비밀번호를 확인한 비활성 계정에는 승인 대기/사용 중지 안내를 제공하도록 보완했다. 인증 백엔드는 ModelBackend, 세션은 DB 세션, native POST/CSRF/안전한 next 처리 유지.

추가로 기존 가입 폼에 이메일 필드가 없었고, 작업 시작 시7개 계정 전부 이메일이 비어 있었다. 새 가입에 이메일을 필수로 추가하되 기존 계정 이메일/해시/권한/승인 상태는 변경하지 않았다. 검증 도중 별도 공개 회원가입1건이 추가되었으며, 원래7개 계정의 정렬된 기록 지문을 별도로 비교해 모두 일치함을 확인했다. 새 가입 계정도 비활성 상태로 보존했다. 기존 계정으로 로그인하려면 별도 관리자 승인이, 이메일 복구를 이용하려면 본인 확인 후 이메일 등록이 필요하다.

## 재개 시점 확인

중단 전 `docker compose up -d`는 이미 완료됐다. web/proxy/db/recovery-cache/recovery-mail5개 모두 healthy였다. 중단 상태를 복구하기 위한 빌드나 up 재실행은 하지 않았다. 아래 필수 입력 오류를 새로 확인한 뒤 해당 표시 수정만 별도로 반영했다. 실행 중 이미지와 현재 인증 소스6개 파일 해시도 일치했다.

기존193개 회귀 테스트와 격리 메일/브라우저 증거를 재사용하고, 미실행이었던 공개 HTTPS 브라우저 검증·배포 점검·보호 확인을 추가 수행했다. 최종 화면 검토에서 빈 로그인 폼의 필수 입력 오류가 렌더링되지 않는 문제를 재현해 템플릿3줄을 보완하고, 이 수정만 Preview에 재반영했다. DB/메일 회귀193개는 기존 통과 증거를 재사용했으며 이후 표시 변경은 공개 브라우저9개 확인 지점으로 검증했다.

## 테스트 결과

증거 루트: `verification/auth-recovery-20261105/`.

| 검사 | 실제 결과 | 증거 |
|---|---|---|
| 최초 실제 활성 계정 로그인 진단 | 올바른 비밀번호302, 잘못된 비밀번호200. CSRF403이 원인이 아님 | login-baseline.json/log |
| Django check / migration drift / migrate --check | SQLite·격리 MariaDB 모두PASS. 신규 migration 없음 | sqlite-final.log, mariadb-final.log |
| SQLite 전체 | **193개 중191 통과, 동시성2 skip, 실패0** | sqlite-final.log |
| 격리 MariaDB 전체 | **193 통과, 실패0** | mariadb-final.log |
| 신규 인증·복구 테스트 | **17개**, 위193개에 포함 | integration_tests/test_account_recovery.py |
| 기존 발주 JS | **4 통과** | javascript.log |
| 모드 부팅 JS | **6 통과** | frontend-unit.log |
| 격리 실제 SMTP 수신+브라우저 | **1개 시나리오, 10 확인 지점 통과** | browser-isolated.json/log |
| 공개 HTTPS 브라우저 | **1개 시나리오, 9 확인 지점 통과** | browser-public.json/log |
| 복구 URL 로그 보호 | 테스트 메일2개/링크3개를 앱·프록시·작업자·테스트 SMTP 로그에서 검사, raw 토큰0 | token-log-scan.json |
| 실행 중 서비스 Django/migration 검사 | PASS | deployed-django-check.log |
| 계정 보존 | 원래7개 계정의 ID/해시/이메일/권한/승인 상태 지문 동일. 별도 신규 가입1건은 추가 상태로 보존. last_login·세션은 로그인 검증에 따라 정상 변경 | deployment-and-protection.json |
| 운영 서비스 보호 | 기존18개(Preview DB 포함) ID·이미지·시작시각·PID·마운트·네트워크 동일, 8000/8007/8010/8011 로그인HTTP200 | deployment-and-protection.json |

SQLite/MariaDB 반복 실행은 고유 케이스386개로 합산하지 않는다. 신규17개도193개에 다시 더하지 않는다. E2E의10/9는 시나리오 안의 확인 지점 수다. 실제 외부 SMTP 수신은 **미검증/미설정**이다.

### 신규17개 검사 범위

1. 정상 로그인/POST 로그아웃/외부 next 거부.
2. 잘못된 비밀번호로 승인 상태를 노출하지 않음.
3. 올바른 비활성 비밀번호 안내 및 legacy 비밀번호 해시 보존.
4. 가입 이메일 필수, 승인 대기/일반 권한 보존.
5. 등록·미등록 이메일 응답 동일, 둘 다 비동기 경로.
6. 아이디 확인 메일은 ID를 먼저 노출하지 않으며 확인 POST 후만 공개.
7. 같은 이메일의 복수 아이디, 재설정은 활성 계정만 단일 메일에 계정별 링크 제공.
8. 아이디 토큰 만료/변조/실제 Redis GETDEL 동시1회 소비.
9. 비밀번호 링크 발송, 새 비밀번호 로그인, 기존 인증 세션 무효화.
10. 비밀번호 토큰 만료/변조/약한 비밀번호 거부.
11. 비활성/사용 불가능한 비밀번호/미등록 이메일 재설정 발송 제외.
12. 이메일 변경 시 기존 링크 무효화.
13. 이메일 요청 제한을 두 기능이 공유.
14. 미설정/큐 장애를503으로 처리.
15. 메일 실패 로그에 이메일/전송 예외 민감 내용 미노출.
16. 복구 요청과 확인의 CSRF 검증.
17. 세 모드 공통 컨트롤·개인정보 헤더·로그 경로 필터.

격리 SMTP 서버는 새 네트워크/임시 SQLite·MariaDB/합성 계정만 사용했다. 실제 이메일 전송 자격이나 운영 사용자 계정은 사용하지 않았다. 테스트 계정 생성 스크립트는 정확한 임시 SQLite 경로와 빈 사용자 테이블을 확인한다. 브라우저에서 이메일 수신→소유권 확인→아이디2개 공개→재사용 거부, 비밀번호 링크→약한 값 거부→변경→새 비밀번호 로그인을 수행했다.

### 발견·해결한 검증 문제

- 초기 토큰 변조 테스트가 URL 마지막 slash 뒤에 문자열을 붙여404를 검사했다. 실제 토큰을 변조하는 테스트로 수정했다.
- non-root 이미지 사용자로 private 참고 문서를 읽지 못해 cooking 테스트를 불러오지 못했다. 테스트 실행 UID를 호스트 소유자와 맞췄다. 참고 문서 권한/내용이나 기존 테스트 요구사항은 바꾸지 않았다.
- legacy 해시 시험에는 해당 보조 해셔를 테스트 설정에 등록했다. 실제 계정 해시를 바꾸지 않았다.
- 브라우저에서 폼 전체의 no-referrer 정책이 Origin:null을 유발해 CSRF403이 발생했다. 링크를 세션에 임시 보관한 뒤 raw 토큰 없는 URL로 이동하고, 폼에는 same-origin을 사용하도록 수정했다. CSRF 검증을 완화/제거하지 않았다.
- 기존 가입 승인 테스트2개의 입력에 새 필수 이메일을 추가했다. 권한 상승 차단/승인 관련 assertion은 유지했다.

## 구현과 현재 실제 발송 상태

- 로그인·복구·등록 화면은 세 모드에서 연결됐다. 공개 HTTPS에서 로그인/로그아웃·세션 유지·Secure 쿠키를 확인했다.
- 실제 발송 모드: **disabled**. 발송 가능false, 큐 길이0. 실제 복구 요청을 발송 성공으로 표시하지 않는다.
- 복구 화면은 미설정을 명시하고 버튼을 비활성화한다. 유효 CSRF로 강제 제출해도503/메일 미발송 안내.
- 테스트 SMTP 캡처 수신만PASS이며 실제 외부 수신함 수신으로 표현하지 않는다.
- 설정·운영 방법: [AUTH_RECOVERY.md](AUTH_RECOVERY.md). SMTP 제공자 호스트/포트/사용자/발신 주소/비밀번호, 발신자 인증과 실제 수신 검증이 필요하다.

## 변경 파일과 보존 범위

- accounts/views.py, auth_forms.py, urls.py: 인증 안내, 명시적 URL 연결, 가입 이메일.
- accounts/recovery.py, recovery_views.py, management/commands/run_recovery_mail.py: 비동기 발송·소유권 증명·기본 재설정 View·원자적 제한.
- accounts/apps.py, logging_filters.py: 복구 토큰 경로/오류 로그 보호.
- templates/accounts/: 로그인·가입·아이디/비밀번호 복구·메일 양식. 기존 공통 UI 모드 사용.
- config/settings.py, preview_settings.py, test_settings.py 및 auth_*_test_settings.py: 기본 발송 비활성, Preview SMTP/secret, 격리 테스트 설정.
- compose.ui-preview.yml, deploy/ui-preview/Dockerfile/nginx.conf/prepare.py: Preview 전용 Redis·메일 작업자, secret, 토큰 로그 제거, redis8.1.0.
- requirements.txt: Redis 클라이언트1개 추가. 기존 AI 의존성 일괄 변경 없음.
- integration_tests/test_account_recovery.py: 신규17개. test_service_verification.py: 가입 fixture2개 이메일 보완.

계정 모델/업무 모델/AI 모델/운영 DB/원본 checkout/Cloudflare 다른 도메인은 변경하지 않았다. 신규 migration 없음. 안정 sprint-final은133b950 그대로다. 커밋은 UI 브랜치에서만 만들며 원격 push/PR은 하지 않는다.

## 남은 사항

- 사용자 지정2개 계정은 계속 승인 대기다. 이번 작업이 관리자 승인을 대신하지 않는다.
- 기존7개 계정의 이메일 미등록을 보존했다. 본인 확인과 권한 있는 관리자의 등록 절차가 필요하다.
- SMTP 자격·발신 도메인 인증·실제 외부 이메일 수신 검증은 남아 있다.
- Redis는 일시 상태이므로 재시작 시 아이디 확인 링크/대기 메일/제한 카운터가 사라진다. 운영형 영속 큐·모니터링·배달 재시도는 후속 작업이다.
- 클라이언트 헤더를 무조건 신뢰하지 않아 프록시 소스 제한은 공유될 수 있다. 규모가 커지면 검증된 실제 클라이언트 주소 전달 또는 별도 남용 방지 구성을 검토한다.
- 실제 사용자 인수/모든 외부 메일 제공자/Cloudflare의 독립 로그 보존 정책은 별도 검증 범위다.

## 실행 명령 및 임시 자원 정리

중단 전에 격리 테스트 네트워크의 Redis와 임시 MariaDB를 준비하고 아래 명령으로193개를 각각 실행했다. 현재 해당 임시 컨테이너5개·네트워크는 소유권과 영구 볼륨 미연결을 확인한 뒤 정리했다. 원래 Preview5개 서비스는 유지한다. 명령을 재사용하려면 새 임시 자원을 먼저 구성해야 하며 Preview DB로 대체하지 않는다.

```sh
# 공통: 새 격리 컨테이너, 읽기 전용 저장소, /tmp 테스트 DB
docker run --rm --user "$(id -u):$(id -g)" --network snp-auth-tests-20261105 \
  --read-only --tmpfs /tmp -e DJANGO_SETTINGS_MODULE=config.test_settings \
  -e ACCOUNT_RECOVERY_REDIS_URL=redis://auth-cache:6379/15 \
  -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 \
  -e OMP_NUM_THREADS=1 -e OPENBLAS_NUM_THREADS=1 \
  -v "$PWD:/workspace:ro" -w /workspace --entrypoint sh snp-ui-preview-web:three-modes -ec '
    python -B manage.py check
    python -B manage.py makemigrations --check --dry-run
    python -B manage.py migrate --noinput
    python -B manage.py migrate --check
    python -B manage.py test --verbosity=2'
```

MariaDB 실행은 같은 명령에서 `DJANGO_SETTINGS_MODULE=config.auth_mysql_test_settings`, `--env-file .ui-preview/auth-test-db.env`를 사용했다. 해당 설정은 auth-db/임시 테스트 DB만 지정한다. 실제 SMTP 캡처용 앱은 config.auth_test_settings와 별도 /tmp SQLite, 자체 SMTP 서버를 사용했다.

공개 브라우저 검증 명령:

```sh
node verification/auth-recovery-20261105/browser-public.cjs
node --test integration_tests/smart_order.test.cjs
npm test --prefix frontend
docker compose -p snp-ui-preview --env-file .ui-preview/compose.env -f compose.ui-preview.yml exec -T web sh -ec 'python -B manage.py check; python -B manage.py makemigrations --check --dry-run; python -B manage.py migrate --check'
```
