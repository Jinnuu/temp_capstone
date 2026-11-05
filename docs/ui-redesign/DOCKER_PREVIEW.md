# 독립 Docker UI 시범 서비스

브랜치 `feature/ui-redesign-three-modes` 전용. 안정 서비스의 Compose 파일은 사용하지 않는다.

## 접속

- 공개 HTTPS: **https://ui.jinnuu.site/**
- 같은 서버: **http://127.0.0.1:8011/**
- Tailscale 연결된 기기: **http://100.65.149.96:8011/**
- 서버 IP 경로: **http://14.138.108.72:8011/** (외부 방화벽/라우팅은 별도 확인 필요)
- 세 화면 비교: 위 주소의 `/ui/compare/`.
- 계정: 영양사 `verify-nutritionist`, 관리자 `verify-admin`, 공급업체 `verify-supplier`.
- 비밀번호: 로컬 `.ui-preview/credentials.txt`에서 확인. 무작위 생성하며 Git·이미지·보고서에 포함하지 않는다.

```sh
cat .ui-preview/credentials.txt
```

포트는8011을 사용한다. 공개 HTTPS는 기존 Cloudflare Tunnel의 `ui.jinnuu.site → http://127.0.0.1:8011` 경로를 사용한다. 터널 자체는 변경하지 않았다. 해당 도메인은 Django Host/CSRF 허용 목록과 Nginx의 고정 HTTPS 원본 정책으로 처리하고, 공개 쿠키에는 Secure를 적용한다. 기존 localhost/Tailscale HTTP 로그인도 유지한다. 후속 장애 원인·수정·실제 브라우저 증거는 [Cloudflare 수정 보고서](CLOUDFLARE_FIX_REPORT.md) 참조.

## 구성

| 서비스 | 이미지 | 용도/접근 |
|---|---|---|
| snp-ui-preview-proxy-1 | snp-ui-preview-proxy:three-modes | Nginx, 호스트8011→8080; 빌드된 정적 파일 직접 제공 |
| snp-ui-preview-web-1 | snp-ui-preview-web:three-modes | Gunicorn 26.2.0 sync2 workers; 내부8000, non-root/read-only |
| snp-ui-preview-db-1 | mariadb:10.6 | 전용 DB snp_ui_preview, 외부 DB 포트 없음 |

- Compose 프로젝트: `snp-ui-preview`.
- 전용 internal 네트워크: `snp-ui-preview_preview` (DB/앱/프록시), 호스트 포트 제공용 `snp-ui-preview_ingress` (프록시만). 기존 네트워크 external 연결 없음.
- 전용 영구 볼륨: `snp-ui-preview_preview_db`. 기존 볼륨 사용 없음.
- Vite 빌드 결과는 앱 이미지에 포함하고 Nginx 이미지에도 collectstatic 결과를 복사한다. 개발 서버·Vite 서버를 공개하지 않는다.
- 검증된 로컬 `capstone-web:sprint7`에서 기존 패키지/OS 런타임을 가져온다. build 단계의 과거 `/app`·홈을 제외한 뒤 FROM scratch에 정리된 런타임을 복사하므로 최종 이미지에 과거 앱/환경 파일 레이어는 상속하지 않는다. Gunicorn 및 Excel 패키지만 추가한다. AI 패키지 일괄 재설치·모델 교체 없음. 이 기반 이미지가 없는 다른 호스트로 이동할 때는 검증한 기반 이미지도 안전하게 전달해야 한다.
- 컨테이너에 저장소를 실시간 바인드하지 않는다. 이후 로컬 코드 편집이 시범 서비스에 바로 반영되지 않는다.
- `config.preview_settings`는 운영 환경 파일/DB의 fallback을 사용하지 않으며 DB 서비스 `db`, DB 이름/사용자 `snp_ui_preview`로 고정한다. Django 비밀키와 DB 비밀번호는 개별 Compose secret 파일로 주입한다.
- 세션/CSRF 쿠키는 시범 서비스 전용 이름이므로 같은 호스트의 기존 서비스 쿠키와 충돌하지 않는다.
- CPU 라이브러리 스레드 제한, 메모리 상한, 로그인 요청 제한, healthcheck, restart unless-stopped 적용.

## 준비와 실행

반드시 저장소 루트에서 실행한다. 기존 `docker-compose.yml`을 사용하지 않도록 **매번 `-f compose.ui-preview.yml`을 명시**한다.

```sh
git branch --show-current  # feature/ui-redesign-three-modes 확인
# 처음 설치만: 기존 secret/env를 덮어쓰지 않음. 기본은 localhost 전용.
python3 deploy/ui-preview/prepare.py
npm ci --prefix frontend
npm run build --prefix frontend
docker compose -p snp-ui-preview --env-file .ui-preview/compose.env -f compose.ui-preview.yml config --quiet
docker compose -p snp-ui-preview --env-file .ui-preview/compose.env -f compose.ui-preview.yml build
docker compose -p snp-ui-preview --env-file .ui-preview/compose.env -f compose.ui-preview.yml up -d
docker compose -p snp-ui-preview --env-file .ui-preview/compose.env -f compose.ui-preview.yml ps
```

이번 호스트에서는 사용자 요구에 따라 `.ui-preview/compose.env`에 bind `0.0.0.0`, port8011과 localhost/서버IP/TailscaleIP allowlist를 설정했다. 새 호스트에는 `prepare.py --bind ... --port ... --hosts ...`로 지정한다. secret은 호스트 0700 디렉터리에 보관하며 개별 파일은 컨테이너 non-root 읽기를 위해 0644, 계정 안내/env는0600이다. 디렉터리 전체를 외부에 공유하지 않는다.

AI 패키지가 크므로 최초 이미지 빌드는 수 분 이상 걸릴 수 있다. 기존 서비스는 그동안 유지한다. 최초 시작/재시작 시 AI 관련 Django import 때문에 준비에 약1분 이상 걸릴 수 있다. web healthy 후 proxy가 시작된다. DB migration은 **새 전용 DB에만** 적용하며 계정 seed는 없는 사용자만 생성한다. 재시작 때 기존 계정·비밀번호·업무 데이터를 덮어쓰지 않는다.

```sh
# 이 시범 프로젝트만 재시작. 기존 SNP 서비스는 대상이 아님.
docker compose -p snp-ui-preview --env-file .ui-preview/compose.env -f compose.ui-preview.yml restart
# 상태 및 로그
docker compose -p snp-ui-preview --env-file .ui-preview/compose.env -f compose.ui-preview.yml ps
docker compose -p snp-ui-preview --env-file .ui-preview/compose.env -f compose.ui-preview.yml logs --tail 30 web
# 필요할 때 시범 서비스만 중지 (데이터 유지)
docker compose -p snp-ui-preview --env-file .ui-preview/compose.env -f compose.ui-preview.yml stop
```

볼륨 삭제·DB 초기화 명령은 제공/실행하지 않는다. `.ui-preview`의 secret을 잃으면 기존 볼륨의 DB 자격과 일치하지 않으므로 서비스 재생성만으로 해결되지 않는다. secret과 전용 볼륨을 함께 보관한다.

## 합성 데이터와 검증

실제 운영 데이터를 복사하지 않았다. 예측 입력도 `deploy/ui-preview/ai_data/new_data.csv`의 합성128일 이력만 사용한다. SBERT 오프라인 캐시 부재로 텍스트 특징 제외 fallback이 관찰됐으며 예측 정확도 검증으로 해석하면 안 된다. 계정 seed 후 Playwright로 공급업체·품목·규격·메뉴·레시피·식단·예측·확정 식수·발주·검수·입출고를 생성했다. 이 시범 서비스에서 새 등록/수정/발주/검수를 수행할 수 있다. QA 날짜는 2026-11-06, 주간 수불 범위는2026-11-02~08이다. 재고와 계정은 전용 MariaDB 볼륨에 저장된다.

자세한 실제 결과는 [DOCKER_PREVIEW_TEST_REPORT.md](DOCKER_PREVIEW_TEST_REPORT.md), 증거는 `verification/ui-preview-20261105/` 참조. 기존 업무 E2E는 **빈 테스트 DB에서 최초 1회용**이므로 실행 중 시범 데이터에 반복 실행하지 않는다. 반복 검증이 필요하면 별도의 새 Compose 프로젝트/DB로 진행한다.

Gunicorn/Nginx 구성 참고: [Gunicorn deployment](https://gunicorn.org/deploy/), [Compose secrets](https://docs.docker.com/compose/how-tos/use-secrets/), [Compose networking](https://docs.docker.com/compose/how-tos/networking/).
