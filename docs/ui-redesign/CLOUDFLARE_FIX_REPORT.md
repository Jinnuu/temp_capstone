# ui.jinnuu.site 접속 장애 수정

검증일: 2026-11-05 KST. 브랜치: `feature/ui-redesign-three-modes`.

## 실제 원인

1. 로컬 `http://127.0.0.1:8011/accounts/login/`은200이었지만 동일 요청에 `Host: ui.jinnuu.site`를 주면400이었다. 공개 HTTPS 요청도400이며 Nginx/Django 양쪽 로그에 도달했다. **UI Preview의 ALLOWED_HOSTS에 도메인이 빠진 것이 현재 접속 장애의 원인**이다. 터널 연결 실패/502가 아니었다.
2. 호스트 허용 뒤 POST도 정상 동작하도록 확인한 설정 결함: Nginx가 Cloudflare의 외부 HTTPS를 내부 `$scheme`인HTTP로 전달하고 있었고 CSRF 허용 목록에도 해당 HTTPS 주소가 없었다. 기존 SECURE_PROXY_SSL_HEADER 설정에 실제 HTTPS 정보가 전달되도록 수정했다. 초기400 때문에 이 POST 단계는 접근조차 불가능했으므로 초기 장애와 구분한다.

## cloudflared 조사

- systemd 호스트 서비스 `/etc/systemd/system/cloudflared.service`, PID1816. Docker 컨테이너가 아니다.
- `PrivateNetwork=no`, `NetworkNamespacePath` 없음, cgroup `/system.slice/cloudflared.service`.
- `/proc/1816/ns/net` 직접 읽기는 권한 제한으로 불가능했다. 이를 네트워크 장애로 판단하지 않았다. systemd 설정과 실제 요청 로그로 호스트 실행/접근을 확인했다.
- 토큰 방식 원격 관리 터널. 프로세스 인수의 토큰은 출력/저장하지 않았다.
- 최신 journal 구성 version27의 UI 경로는 `ui.jinnuu.site → http://127.0.0.1:8011`이었다. 이미 올바른 경로여서 터널·DNS·systemd 설정을 변경하거나 cloudflared를 재시작하지 않았다.
- 과거 일시적인 QUIC 재연결 로그가 있었으나 재등록되었으며 이번400과 무관하다. 실제 요청이 Django까지 도달했다.

## 최소 변경

- 무시된 로컬 `.ui-preview/compose.env`:
  - 기존 `SNP_PREVIEW_ALLOWED_HOSTS`에 `ui.jinnuu.site`만 추가, 기존 localhost/Tailscale/서버IP 보존.
  - `SNP_PREVIEW_CSRF_ORIGINS=https://ui.jinnuu.site` 추가. 와일드카드 허용 없음.
- `deploy/ui-preview/nginx.conf`:
  - 정확한 공개 호스트 `ui.jinnuu.site`만 upstream scheme을https로 설정. 다른 로컬 호스트는 실제HTTP scheme 유지.
  - 클라이언트가 보낸 임의의 X-Forwarded-Proto를 그대로 신뢰하지 않는다. 이 도메인의 TLS는 Cloudflare에서 종료된다는 명시적 배치 정책이다.
  - 해당 공개 호스트의 Preview session/CSRF 쿠키에 Secure 적용. 로컬HTTP 쿠키 동작 보존.
- `config/preview_settings.py`: 기존 SECURE_PROXY_SSL_HEADER의 역할을 실제 정책과 맞도록 주석 정정. 업무 로직 변경 없음.
- UI Preview 앱/프록시 이미지만 재빌드·재생성했다. DB 컨테이너는 재시작/재생성하지 않았다. 새 migration 없음.

새 환경에도 적용하려면 기존 환경 파일 값을 보존하며 아래 도메인을 추가한다.

```dotenv
# 기존 허용 호스트 뒤에 추가
SNP_PREVIEW_ALLOWED_HOSTS=localhost,127.0.0.1,ui.jinnuu.site
SNP_PREVIEW_CSRF_ORIGINS=https://ui.jinnuu.site
```

이미 운영 중인 Preview에서는 위 예제로 기존 IP 목록을 덮어쓰지 않는다. `SNP_PREVIEW_HTTPS=1`을 전역으로 켜지 않고 프록시에서 호스트별 Secure를 적용해 기존 Tailscale HTTP 로그인도 유지했다.

```sh
docker compose -p snp-ui-preview --env-file .ui-preview/compose.env -f compose.ui-preview.yml build
docker compose -p snp-ui-preview --env-file .ui-preview/compose.env -f compose.ui-preview.yml up -d web proxy
```

## 실제 공개 HTTPS 브라우저 검증

`verification/ui-cloudflare-20261105/browser.cjs`를 실제 Chromium으로 실행했다. 인증정보는 로컬 secret에서만 읽으며 저장하지 않는다. **1개 시나리오, 확인 지점10개 통과**.

| 검증 | 결과 |
|---|---|
| HTTPS 로그인 폼 제출 → 대시보드 | PASS |
| 공개 session/CSRF 쿠키 Secure | PASS |
| MODE1/2/3 표시·전환, 페이지 이동·reload 후 유지 | PASS |
| 같은 도메인의 JS/CSS 다운로드 | PASS200 |
| 메뉴/식재료 검색 API | PASS200, JSON 결과 확인 |
| 기존 미사용 식단 메뉴에 대한 멱등 POST | PASS200, CSRF·Origin·Referer 포함 |
| CSRF token 없는 POST | 예상403 |
| 유효 token만 있고 Origin/Referer 없는 HTTPS POST | 예상403. Django가 HTTPS로 인식함을 확인 |
| 같은 공개 도메인의 비교 iframe3개 | PASS |
| 기존 localhost/Tailscale HTTP 로그인 | PASS, 로컬 쿠키에는 Secure 강제하지 않음 |

브라우저 JS 예외0, 서버500 오류0, HTTP mixed-content 요청0. 정적 파일과 API는 상대 경로를 정상 사용했으며 프론트엔드 코드 수정은 필요하지 않았다. `nginx -t` 통과.

증거: `verification/ui-cloudflare-20261105/result.json`, `browser.log`, `https-comparison.png`, `protection-and-http.json`.

일부 Python urllib 기본 요청은403을 받았으나 curl 및 실제 Chromium은 성공했다. 이403의 세부 원인은 별도로 확정하지 않았으며 애플리케이션 로그인 실패로 혼동하지 않았다. 우회 설정도 변경하지 않았다.

## 보호 확인

- 앱/프록시2개 외 기존 컨테이너18개(Preview DB 포함)의 ID·이미지·PID·시작시각·마운트·네트워크 동일.
- 운영 DB에 접속하지 않았다. Preview 업무 테이블22개는 이전 Preview 검증 종료 스냅샷과 행 수/해시가 일치했다. 이는 작업 직전 새 스냅샷이 아니라 이전 검증 증거와의 비교이다. 계정 표는 로그인에 따른 last_login/세션 변경을 고려해 비교에서 제외했다.
- 기존 `capstone.jinnuu.site`, `sprint7.jinnuu.site`, `demo.jinnuu.site` 로그인 페이지는 curl200. cloudflared PID1816 및 구성version27 유지.
- `sprint-final`은 기존 `133b950221bd9cc1effaa51539abf7f88bb095c1` 유지. 기존 서비스·운영 DB·볼륨·Cloudflare 다른 도메인 수정 없음.

이번에는 공개 HTTPS 접속 관련 기능을 집중 검증했다. 전체 Django/MariaDB 회귀 테스트를 다시 실행했다고 주장하지 않는다. 기존 합성 AI 데이터/SBERT fallback 한계는 이전 Preview 보고서와 같다.

공식 설정 근거: [Django 프록시 HTTPS 설정](https://docs.djangoproject.com/en/6.1/ref/settings/#secure-proxy-ssl-header), [Cloudflare HTTP 헤더](https://developers.cloudflare.com/fundamentals/reference/http-headers/).
