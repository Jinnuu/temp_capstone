# Docker UI Preview 실제 실행 검증

검증일 2026-11-05 KST. 브랜치 `feature/ui-redesign-three-modes`. 안정 `sprint-final`은 `133b950221bd9cc1effaa51539abf7f88bb095c1` 그대로다.

## 결과

**8011에서 시범 서비스를 실행한 상태로 유지한다.** 기존 서비스에는 배포하지 않았다. [접속·계정·Compose 실행 안내](DOCKER_PREVIEW.md).

| 항목 | 실제 결과 | 증거 (`verification/ui-preview-20261105/`) |
|---|---|---|
| 기존 자원 조사 | 컨테이너17, 이미지55, 네트워크22, 볼륨55 조사. 8011 비어 있음 | inventory-before-summary.json |
| 기존 8000/8007 로그인 페이지 | 실행 전·후 모두 HTTP200 | protection-final.json |
| 새 DB/App/Nginx | 3개 모두 healthy, Nginx8011만 게시 | protection-final.json |
| 프론트엔드 포함 | CSS/JS collectstatic 후 이미지에 포함, CDN/Vite 서버 불필요 | image-content.json, build-final.log |
| Django check | 오류0 | django-check-final.log |
| migration drift / 적용 검사 | No changes detected, migrate --check 통과 | django-check-final.log |
| Django 배포 보안 점검 | **HTTP/TLS 관련 경고4건**. 경고를 숨기지 않음 | django-check-final.log |
| SQLite 전체 회귀 | 176개 중174 통과, 동시성2 skip, 실패0 | sqlite-regression.log |
| 실제 MariaDB 업무 E2E | 초기7 지점 통과 후 누락 CSV로 예측 실패 → 수정 후 남은15 지점 통과. 고유 업무 확인 지점 총22 | flow/initial-progress.json, initial-attempt.json, browser-result.json |
| 세 모드 UI E2E | 모드 변경·입력 유지·파일 유지·이동·브라우저 재실행·비교·태블릿·인쇄 등16 확인 지점 통과 | ui/ui-result.json, ui/run.log |
| 재시작 | 이 Compose의 DB/App/Nginx만 재시작 후 모두 healthy | restart.log, restart-health.json |
| 데이터 영속성 | 업무 테이블23개 행 수와 내용 해시가 재시작 전후 일치 | db-*-restart.json, restart-data-result.json |
| 세션·선택 유지 | 기존 영양사 세션과 그린 모드로 재시작 후 수불현황 재조회 성공 | restart-before.json, restart-after.json |
| 기존 자원 보호 | 기존17개 컨테이너 ID·이미지·PID·시작시각·마운트·네트워크 동일. 새 서비스에 기존 볼륨/네트워크 연결 없음 | protection-final.json |
| 정리된 최종 이미지 AI 재검증 | 별도 날짜2026-11-13의3끼니를 실제 화면에서 예측·저장 | ai-final-image.json, ai-final-image.log |
| 모델 보존 | 3개 pickle 해시 원본과 일치, 재학습/교체 없음 | image-content.json, protection-final.json |

SQLite와 별개로 **실제 시범 MariaDB에서 업무 브라우저 시나리오를 실행**했다. 이번 작업에서 MariaDB용 Django 전체176개를 다시 실행한 것으로 표현하지 않는다. 그 전체 테스트의 이전 결과는 `verification/ui-three-modes-20261105/mariadb-final.log`에 있으며 이번 신규 실행 증거와 구분한다. 22/16은 E2E 시나리오 안의 확인 지점 수이며 독립 테스트 개수가 아니다.

## 검증한 실제 업무

- 공급업체2개, kg 식자재2개를 화면으로 생성·조회·수정.
- 5kg/캔500원, 3kg/판600원 명시적 규격 설정. 기본 품목 단가와 포장 단가 구분.
- 100g 레시피 작성·재저장, 레시피/식단 Excel 업로드, 일간 저장, 주간 다음 월요일 추가·제거.
- 기존 AI 모델 실행·3끼니 결과 저장, 수동360명/최종351명 분리.
- 품목별35.1kg 소요량 → 참치 최소8캔을9캔으로 조정, 두부12판. 공급업체별 발주/Excel 확인.
- 검수 전 재고증가 없음. 납품45kg 중 합격40kg만 입고, 동일 검수 재제출은 중복 입고되지 않음.
- 추가입고2kg, 사용35.1kg, 폐기1kg → 참치기말5.9kg, 두부0.9kg. FIFO/수불 확인.
- 조리지시사항 저장·수정·재조회, Excel/PDF, 조리지시서로 재고가 자동 차감되지 않음.
- 월 정산/구매발주 문서, 미사용 메뉴 삭제, XSS 문자 이스케이프, CSRF 없는 요청403, 공급업체 내부업무403, 관리자 가입 승인.
- 동일 DB의8개 화면에서 세 모드 텍스트가 같고, 입력 노드/파일 선택이 유지됨. 비교 화면은 읽기 전용.

초기 E2E 중단 후 기존 합성 레코드를 초기화하지 않았다. `SNP_PREVIEW_RESUME=after-meals`로 이미 통과한 등록/식단 단계를 건너뛰고 실패 지점부터 이어 실행했다. 이전 실패는 `flow/initial-attempt.*`로 남겼다. 같은 DB에 처음부터 전체 생성 시나리오를 재실행하면 중복 fixture 때문에 실패할 수 있으므로 새 검증에는 별도 빈 테스트 환경을 사용한다.

## 발견·수정 사항

| 원인 | 조치 |
|---|---|
| Compose inline tmpfs 옵션의 쉼표가 별도 경로로 해석됨 | 옵션 문자열을 따옴표로 묶어 정상 마운트 확인 |
| 이 Docker 버전의 internal-only 네트워크는 host port를 실제 게시하지 않음 | DB/App은 internal 유지, 프록시에 전용 ingress 네트워크만 추가. 기존 네트워크 사용 없음 |
| Gunicorn control socket 기본 경로가 read-only 홈을 사용 | `--no-control-socket` 적용. WSGI 서비스는 정상 실행 |
| 초기 비밀키 길이가 Django 권장50자 미만 | 시범 전용 비밀키를64바이트 무작위로 생성. 기존 DB/서비스 키 변경 없음 |
| 기반 이미지에 과거 `/app/.env`와 데이터가 포함되어 있음 | build 단계에서 과거 앱/홈을 제외하고 FROM scratch에 정리한 전체 런타임을 복사. 기존 패키지/OS는 보존하며 최종 이미지에는 과거 앱 레이어를 상속하지 않음 |
| 선택적 COPY에서 예측용 CSV 누락 | 새 합성 CSV128일 포함. 기존 원본 CSV와 운영 DB는 사용하지 않음 |
| 앱 재생성 시 프록시 DNS 주소 고정 위험 | Docker DNS resolver/동적 upstream 적용 |

## 변경 파일과 이유

- `compose.ui-preview.yml`: 별도 프로젝트/3서비스/2네트워크/전용 DB볼륨/healthcheck/포트/secret.
- `deploy/ui-preview/Dockerfile`: 검증된 기존 Python/AI 환경 기반 이미지, Gunicorn, collectstatic, non-root 실행, Nginx 이미지.
- `deploy/ui-preview/entrypoint.sh`: 전용 DB migration과 비파괴 계정 bootstrap 후 Gunicorn.
- `deploy/ui-preview/seed_preview.py`: DB 이름/호스트/명시적 preview flag 확인 후 없는 합성 계정만 생성.
- `deploy/ui-preview/prepare.py`: 기존 secret/env를 덮어쓰지 않는 로컬 설정 생성.
- `deploy/ui-preview/nginx.conf`: 정적 파일·프록시·업로드 크기·로그인 제한·동적 DNS.
- `deploy/ui-preview/ai_data/*`: 시범용 합성 이력, 생성 규칙 설명.
- `config/preview_settings.py`, `preview_build_settings.py`, `preview_context.py`: 운영 DB fallback 없는 설정, 정적 수집, 합성 시범 안내.
- `templates/base.html`: preview 설정에서만 표시되는 합성 데이터 안내. 일반 브랜치 설정의 업무 동작은 유지.
- `.gitignore`, `.dockerignore`: `.ui-preview` 자격정보 제외. `.gitattributes`: 합성 CSV 줄바꿈과 원본 Docker 로그의 공백 처리 명시.
- `docs/ui-redesign/`: 실행/검증 문서, 실제 시범서비스28장 캡처. 이전 보고서의 Python 이미지 내 Django 버전 표기를 실제 측정6.0.3으로 정정.
- `verification/ui-preview-20261105/`: 실행 결과·재시작/보호 증거 및 재현 도구. 신규 migration 없음.

## 한계·남은 문제

1. **HTTP**: HSTS/HTTPS redirect/Secure session/Secure CSRF 경고4개가 남는다. Tailscale/SSH 접속을 우선 사용한다. 공개 HTTPS 호스트명과 Cloudflare 연결은 이번에 설정하지 않았다. 외부 인터넷에서 서버 공인IP로 접속 가능한지는 다른 네트워크에서 미검증이다.
2. **AI**: 모델3개 추론·저장은 성공했으나 오프라인 SBERT 캐시가 없어 기존 processor의 텍스트 특징 제외 fallback이 관찰됐다. 합성 이력 기반 결과이므로 예측 품질/정확도나 최종 연구 모델 성과로 해석하지 않는다. 모델/추론 코드는 수정하지 않았다.
3. **사용성**: Chromium으로 검증했다. 실제 영양사 인수, 다른 브라우저, 장시간 부하, 실제 터치 기기, 전체 접근성은 미검증이다.
4. **기존 데이터 보호 증거 범위**: 운영 DB에는 접속하지 않았으며 내용 해시를 수집하지 않았다. Docker 구성/시작 상태 보존과 완전 분리된 연결을 확인한 것이다. 기존 DB 데이터 전수 비교를 주장하지 않는다.
5. 합성 테스트에는 문자 안전성 확인용 특수문자 메뉴도 포함된다. QA 데이터이며 실운영 발주/검수에 사용하지 않는다.
6. 전체 호스트 재부팅은 하지 않았다. 실제 수행한 검증은 시범 Compose3서비스 재시작이며 restart unless-stopped 정책을 설정했다.

시범용 메뉴/식단/발주/검수 조작은 가능하다. 운영 서비스 전환 또는 상용 배포 완료로 판정하지 않는다. 원격 반영은 UI 실험 브랜치만 대상으로 하며 PR/안정 브랜치 병합은 수행하지 않는다.
