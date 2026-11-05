# 로그인·계정 복구 운영 안내

대상은 UI 실험 브랜치와 `https://ui.jinnuu.site`의 독립 Preview뿐이다. 안정 서비스의 승인 정책이나 계정을 변경하지 않는다.

## 로그인과 승인

로그인은 Django `LoginView`/`ModelBackend`/DB 세션과 기본 CSRF 검증을 사용한다. 폼은 username/password를 기존 로그인 URL에 POST한다. JavaScript API 로그인으로 교체하지 않았다. 안전한 next 경로 전달과 POST 로그아웃을 유지한다.

비활성 계정은 올바른 비밀번호를 입력해도 로그인할 수 없다. 비밀번호를 확인한 경우에만 승인 대기/사용 중지 안내를 표시하며, 틀린 비밀번호에는 일반적인 인증 오류를 표시한다. 비활성 비밀번호 검증에는 setter를 쓰지 않아 기존 해시를 갱신하지 않는다. 활성 계정에는 기존 Django 인증 절차를 사용한다.

가입 신청은 여전히 비활성 일반 영양사 계정으로 저장된다. 새 신청에는 복구용 이메일을 필수로 받는다. 기존 이메일 미등록 계정에는 임의의 이메일을 넣지 않는다. 기존 계정 복구는 권한 있는 관리자가 본인 확인 후 이메일을 등록해야 하며, 승인도 별도 관리자 절차다.

## 화면과 정책

로그인 화면에서 아이디 찾기·비밀번호 재설정·회원가입으로 이동한다. 모든 화면은 기존 세 UI 모드를 공유한다. MODE2는 사용자 확인에 따라 ZIP 레퍼런스에 녹색을 적용한 디자인이며 별도 포스터 원본을 재현한 것이 아니다.

| 기능 | 정책 |
|---|---|
| 아이디 찾기 | 가입 이메일로 소유권 확인 링크 발송. GET은 링크를 세션에 임시 보관하고 깨끗한 URL로 이동. CSRF 보호 확인 버튼 POST 후 아이디 공개 |
| 동일 이메일의 복수 계정 | 아이디 찾기는 연결된 전체 아이디(비활성 포함)를 안내. 이메일 소유자만 확인 가능 |
| 비밀번호 재설정 | Django 기본 PasswordResetView/ConfirmView와 기본 토큰 생성기를 활용. 활성·사용 가능한 비밀번호 계정만 포함 |
| 복수 계정 재설정 | 한 이메일에 활성 계정별 링크를 묶어 발송. 승인 상태/권한을 변경하지 않음 |
| 만료·재사용 | 30분. 아이디 링크는 Redis GETDEL로 원자적 1회 소비. 비밀번호 링크는 비밀번호 변경 후 무효화 |
| 기존 세션 | 비밀번호 변경 후 Django 인증 해시 검증으로 이전 세션은 다음 요청에서 무효. 재설정 후 자동 로그인하지 않음 |
| 계정 존재 여부 | 등록/미등록 이메일 모두 같은 접수 응답. 조회와 SMTP는 작업자에서 수행해 요청 응답의 SMTP 시간 차이를 줄임 |
| 요청 제한 | 두 복구 기능이 이메일당 시간당3회를 공유. 프록시 소스당 시간당100회. 초과429/Retry-After. 소스는 클라이언트 제공 IP 헤더를 신뢰하지 않는 보수적 집계이며 Cloudflare 경로에서는 공유 제한일 수 있음 |
| 발송 불가 | SMTP 미설정은 화면에 표시하고 제출 비활성화. 강제 POST에도503, 발송했다고 안내하지 않음 |
| 장애 | 큐 장애는503으로 실패 처리. 발송 실패는 수신자·토큰·SMTP 예외 본문 없이 오류 기록. 실패 메일을 무조건 재시도하지 않음 |

요청 접수와 메일 수신은 다르다. SMTP 설정 후에도 제공자 인증·수신함 도착까지 별도 확인이 필요하다. 기존 계정의 이메일이 비어 있으면 등록 이메일 기반 복구를 사용할 수 없다.

## Docker 구성

기존 DB/App/Nginx에 Preview 전용 `recovery-cache`와 `recovery-mail`을 추가한다. 둘 다 기존 운영 서비스의 네트워크/DB에 연결하지 않는다.

- Redis7: 외부 포트 없음, 비밀번호 secret, 메모리 제한, 영구 파일 저장 없음. 원자적 제한/소유권 증명/메일 큐 공유.
- 메일 작업자: 웹과 같은 전용 이미지, 기본 entrypoint를 바꿔 계정 seed/migration을 실행하지 않음. 자체 Preview ingress를 통해 SMTP로 나갈 수 있으나 포트를 게시하지 않음.
- Redis 재시작 시 대기 메일·아이디 증명·제한 카운터는 사라진다. 이미 발급한 아이디 링크는 실패 처리되므로 재요청해야 한다. 비밀번호 토큰은 Django 표준 상태/만료 검증을 따른다.
- 패키지 추가는 `redis==8.1.0` 하나다. 기존 AI 패키지/모델은 교체하지 않았다. 신규 DB migration 없음.

## SMTP 설정

**현재 실제 발송은 disabled다.** 테스트 SMTP 캡처 수신 성공을 실제 사용자 이메일 수신으로 표현하지 않는다.

기존 `.ui-preview/compose.env` 내용을 유지하면서 제공자에게 확인한 값만 설정한다.

```dotenv
SNP_RECOVERY_DELIVERY_MODE=smtp
SNP_SMTP_HOST=<제공자 SMTP 호스트>
SNP_SMTP_PORT=587
SNP_SMTP_USER=<SMTP 사용자>
SNP_SMTP_TLS=1
SNP_SMTP_SSL=0
SNP_DEFAULT_FROM_EMAIL=<발신 권한이 검증된 주소>
```

SMTP 비밀번호/앱 비밀번호는 `.ui-preview/smtp_password`에 로컬 보안 편집기로 기록한다. 코드·Git·채팅·명령행 인수에 넣지 않는다. `.ui-preview`는0700으로 유지한다. 개별 secret 파일은 컨테이너 사용자 읽기를 위한0644, 환경 파일과 계정 안내는0600이며 상위 디렉터리가 다른 사용자 접근을 제한한다. TLS/SSL 옵션은 동시에 켜지 않는다. 제공자 정책에 따라 포트/SSL을 설정한다.

`prepare.py`는 기존 secret과 설정을 덮어쓰지 않고 복구 Redis secret 및 비어 있는 SMTP secret을 준비한다. 다음 명령은 **이 Preview 프로젝트만** 대상으로 한다.

```sh
python3 deploy/ui-preview/prepare.py
docker compose -p snp-ui-preview --env-file .ui-preview/compose.env -f compose.ui-preview.yml config --quiet
docker compose -p snp-ui-preview --env-file .ui-preview/compose.env -f compose.ui-preview.yml build
docker compose -p snp-ui-preview --env-file .ui-preview/compose.env -f compose.ui-preview.yml up -d recovery-cache web proxy recovery-mail
docker compose -p snp-ui-preview --env-file .ui-preview/compose.env -f compose.ui-preview.yml ps
docker compose -p snp-ui-preview --env-file .ui-preview/compose.env -f compose.ui-preview.yml logs --tail 30 recovery-mail
```

전송 상태가 sent로 처리되는 것은 설정된 SMTP가 메일을 접수했다는 의미다. 실제 수신함 수신과 SPF/DKIM/DMARC·스팸 정책은 별도 운영 검증한다. 설정 후 소유자가 확인할 수 있는 계정 이메일로 승인된 검증을 진행한다. 이번 작업에서는 기존 사용자 이메일·승인을 수정하지 않았다.

## 로그·링크 보호

- Nginx/Gunicorn은 복구 URL을 고정된 REDACTED 경로로 기록하고 쿼리/Referer를 기록하지 않는다. 복구 경로의 Nginx upstream 오류 로그도 raw URL을 남기지 않는다.
- Django 오류 기록에 복구 경로 필터와 민감 POST 처리를 적용한다. 메일 작업자는 메일 본문/수신자/토큰/전송 예외의 민감 텍스트를 기록하지 않는다.
- raw 링크의 진입 응답은 no-referrer로 깨끗한 URL로 이동한다. 실제 폼은 same-origin 정책으로 CSRF Origin/Referer 검증을 유지한다. no-referrer를 폼 전체에 적용하면 브라우저의 Origin:null로 정상 POST가 차단될 수 있어 사용하지 않는다.
- 복구 응답은 no-store. 주소는 고정된 HTTPS 공개 원본에서 생성해 요청 Host를 이용한 링크 변조를 피한다.

외부 Cloudflare/메일 제공자의 독립적인 로그 정책은 이 애플리케이션 로그 검사 범위 밖이다. [실제 검증 보고서](AUTH_RECOVERY_TEST_REPORT.md)를 참고한다.
