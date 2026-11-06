# Phase 1 + 영양사 가이드 Preview 적용 보고서

2026-11-06 KST. 시작 HEAD `3236e07f2bf218993ab1f686d3034260b760efb4`, 브랜치 `feature/ui-redesign-three-modes`. 이번 사용자 요청의 실행 승인으로 Preview 배포·관리자 username 변경·공개 신규 가입 승인 정책을 적용했다. 비밀번호 변경·데이터 삭제·다른 서비스 변경은 하지 않았다. 최종 로컬 커밋은 Git log/완료 응답을 따른다. 원격 push/PR/안정 브랜치 병합은 없다.

## 실제 결과

| 항목 | 결과 |
|---|---|
| 접속 | https://ui.jinnuu.site / 기존8011 Preview |
| 관리자 | **PK1, username admin**, MAIN_ADMIN·staff·superuser·활성·ACTIVE 유지 |
| 비밀번호 | **기존 비밀번호 유지**. 출력/추측/재설정/실제 계정 로그인 안 함 |
| 계정 수 | 9→9, MAIN1명, verify-admin0명 |
| 신규 공개 가입 | 영양사·공급업체 모두 PENDING/비활성. 계정 승인과 업체 소속 확인/관리자 심사 별도 |
| 기존 활성/정지 계정 | 상태·권한·이메일·개인정보·그룹·연결 관계 보존 |
| 교체한 서비스 | snp-ui-preview의 web/recovery-mail/proxy3개만 |
| 보존한 서비스 | Preview DB/cache와8000/8007/8010 원래 컨테이너·이미지·시작시각·마운트·네트워크 동일 |
| 건강 상태 | Preview5개 healthy |
| 스키마 | 새 모델/migration 없음. 기존 DB 초기화/볼륨 재생성/데이터 삭제 없음 |
| 외부 SMTP | 기존 disabled 유지. 외부 메일 수신 가능하다고 표시하지 않음 |

## 1. 사전 조사와 복구 게이트

기존 Phase1 테스트/운영 보고서와 현재 브랜치/HEAD/status/AGENTS를 확인했다. worktree에는 change_password.sh만 미추적 상태였고 이를 읽거나 실행/수정/커밋하지 않았다. Docker 컨테이너 상태와 보존 대상8개의 메타데이터를 기록했다. 실제 DB는 snp_ui_preview/db, 최초9계정/MAIN PK1 verify-admin/대상admin 충돌 없음이었다.

- 기존 실행 이미지는 `snp-ui-preview-web:pre-tutorial-3236e07`, `snp-ui-preview-proxy:pre-tutorial-3236e07` 태그로 보존했다.
- candidate는 `snp-ui-preview-{web,proxy}:tutorial-20261106`로 빌드했다. AI 파일/학습·추론 로직·의존성은 교체하지 않았다.
- 기존 env/secret 값을 덮어쓰지 않는 prepare를 사용해 **새 bootstrap 전용 관리자 secret 파일만 추가**했다. 이것은 기존 사용자의 비밀번호 설정/변경이 아니다. 기존 secret 내용은 배포 전후 동일함을 private 비교했다.
- 최신 SQL 백업은 private `.ui-preview/backups/`에0600으로 보관하고 Git/이미지에서 제외했다. DB37개 테이블의 전체 행 fingerprint를 백업 전/후와 격리 복원본에서 비교했다. 원문 행·비밀번호 해시·세션·secret을 출력하지 않았다.
- 백업 크기79,085bytes. `backup-verification.json`에 크기/파일 SHA256/검증 여부만 기록했다. 파일 SHA256은 DB 사용자 비밀번호 해시가 아니다.
- 작업 전용 tmpfs MariaDB의 restore_check에만 복원했다. 기존 계정/PK/암호/상태·그룹 보존, rename/seed/역방향 rename rollback을 후보 이미지로 검증했다. 실제 DB로 덤프를 되돌리거나 drop/flush하지 않았다.
- 후보 전체 회귀와 브라우저를 통과한 후 실제 데이터가 검증한 최신 백업과 여전히 같은지 재확인했다. 실패하면 실제 배포/이름 변경을 진행하지 않는 gate를 적용했다.

증거: `verification/tutorial-preview-20261106/backup-verification.json`, `restore-rehearsal.json`, `deployment-gates.json`. SQL·사전 env·민감 비교자료는 private audit 디렉터리이며 커밋하지 않는다.

## 2. 적용한 설정·실행 순서

`SNP_PUBLIC_SIGNUP_REQUIRES_APPROVAL=1`만 실제 compose.env에 추가했다. 기존 ACCOUNT_APPROVAL_MODE=auto와 모든 다른 env/SMTP 값은 보존했다. effective public approval helper가 이 opt-in을 우선하므로 공개 가입은 두 유형 모두 PENDING이다. 기존 active 계정을 일괄 변경하거나 승인 이력을 소급하지 않았다. 관리자 목록/권한 화면에도 raw 환경 모드와 별도로 공개 승인 필요를 표시한다.

```sh
# 이미 수행한 명령의 비밀값 없는 요약
python3 deploy/ui-preview/prepare.py
docker compose -p snp-ui-preview --env-file .ui-preview/compose.env \
 -f compose.ui-preview.yml -f .ui-preview/audit/tutorial-preview-20261106/candidate-compose.yml config --quiet
# candidate web/proxy 빌드와 격리 전체 검사 후 기본 태그를 검증된 candidate로 갱신
docker image tag snp-ui-preview-web:tutorial-20261106 snp-ui-preview-web:three-modes
docker image tag snp-ui-preview-proxy:tutorial-20261106 snp-ui-preview-proxy:three-modes
docker compose -p snp-ui-preview --env-file .ui-preview/compose.env \
 -f compose.ui-preview.yml up -d --no-deps --wait web recovery-mail proxy
# 건강 확인·startup 전후 데이터 동일 확인 후, 기존 명령 사용
docker compose -p snp-ui-preview --env-file .ui-preview/compose.env \
 -f compose.ui-preview.yml exec -T web python -B manage.py rename_preview_admin
docker compose -p snp-ui-preview --env-file .ui-preview/compose.env \
 -f compose.ui-preview.yml exec -T web python -B manage.py rename_preview_admin --apply --expected-pk 1
```

실제 이름 변경은 같은 컨테이너의 docker exec로 위 명령을 실행했다. dry-run의 PK/충돌 검사 후 원자적 변경을 수행했다. 새 admin을 생성하지 않았다. 재시작 시에도 검증한 기본three-modes 태그/현재 env를 사용하도록 candidate 태그만 남겨두지 않고 기본 태그도 갱신했다. db/cache는 재생성하지 않았다. compose up/down을 다른 프로젝트에 실행하거나 터널을 조작하지 않았다.

## 3. 실제 데이터 보존 결과

전체37개 기존 테이블을 비교했다. 허용된 User PK1 username을 비교 시 정규화하고 신규 감사1건 이후를 분리하면 모든 기존 행이 동일하다. 이는 단순 count 비교보다 강한 검증이며 원문 필드는 public 증거에 포함하지 않았다.

| 자료 | 전→후 |
|---|---|
| 사용자/MAIN | 9→9 / 1→1 |
| 메뉴/레시피/식단 | 5→5 / 4→4 / 4→4 |
| 발주/품목/검수 | 2→2 / 2→2 / 2→2 |
| 재고 로그/lot/allocation | 6→6 / 3→3 / 3→3 |
| 업체 소속/조리지시서 | 2→2 / 1→1 |
| 새 감사 | account.username_changed1건만 추가. 기존 감사 FK/역사 라벨 보존 |

`data-preservation.json`은 같은 PK의 암호·개인정보·권한·그룹과 모든 기존 참조 보존을 기록한다. 공개 읽기 검증 후에도 같은 비교를 다시 통과했다. `readonly_seed_check.py`는 배포된 seed를 **SQL 쓰기 차단 wrapper** 아래 실제 재실행했다. SELECT12개/데이터 쓰기0/9계정 유지/verify-admin 재생성 없음이었다. 예기치 않은 INSERT가 있었다면 실행 전에 차단하도록 했다.

## 4. 새 실행 검증

| 검사 | 결과/증거 |
|---|---|
| Django check, migration drift/apply/check | 격리 두 DB 통과, 신규 migration0 |
| SQLite 전체 | 325발견:321pass/4skip/실패·오류0 |
| MariaDB 전체 | 325pass/실패·오류·skip0 |
| JS/빌드 | 17pass, TypeScript/Vite build통과 |
| 기존 영양사 업무 | 21검증 지점: relocated 식수 저장·기존 업로드/발주/검수/FIFO/수불/조리/문서 유지 |
| 공급업체·관리자 | 13지점: 승인 전 로그인 차단·계정 승인과 소속 확인 분리·수주/입고·관리자 신청/겸임·격리 유지 |
| 가이드 | 15지점: 단계·읽음·복원/재시작·역할·JS/저장/이미지 실패·3모드/모바일 |
| 실제 Preview 읽기 | 실제 admin/정책/단계·독립 화면 RequestFactory 렌더 및 배포 소스·asset hash 일치. 실제 사용자 로그인/세션 생성 안 함 |
| 공개 HTTPS | **7지점**: 실제 브라우저 로그인 폼,3모드 이동/재조회 유지, 승인 안내, 보호 화면302, Secure CSRF, public JS/CSS byte 일치 |
| 기존 서비스 | 8000/8007/8010/8011 로그인 GET200, Preview5healthy, 보존 대상 메타데이터 동일 |

Django325개는 두 DB의 같은 테스트 반복이다. 기존309+신규16이며, JS는 기존10+진행률7이다. 브라우저 지점/스크린샷 수는 Django 케이스에 합산하지 않는다. SQLite skip은 기존 행 잠금/경합4개로 MariaDB에서 실행됐다.

공개 HTTPS에서는 비밀번호 입력·회원가입 제출·실제 발주/검수/재고/역할 변경을 하지 않았다. 기존 계정 로그인 유지는 비밀번호/secret/상태 보존과 격리 로그인 회귀로 검증했으며 **실제 admin 로그인 성공을 새로 관측했다고 주장하지 않는다**. 기존 실제 계정은 소유자가 기존 비밀번호로 이용해야 한다.

초기 공개 검사에는 두 하네스 오류가 있었다. 접힌 공급업체 설명을 visible text로 찾던 assertion을 실제 보이는 승인 안내와 유형 선택 후 설명으로 수정했다. 또한 Cloudflare 자동 성능 수집 POST(/cdn-cgi/rum)를 업무 쓰기로 잘못 집계했다. 경로만 기록해 원인을 확인한 후 테스트 브라우저에서 해당 telemetry만 차단했다. 다른 POST는 계속 실패 처리한다. 마지막 applicationMutationRequests는0이다. 실패/진단 기록도 보존했으며 서비스나 Cloudflare 설정을 바꾸지 않았다.

증거는 `verification/tutorial-preview-20261106/`의 final 로그·browser JSON·service-protection/data-preservation/readonly-seed JSON 및 screenshots다. 전체 침투·부하·WCAG·실제 현업 인수는 완료한 것이 아니다.

## 5. 롤백 계획

복원본에서 같은PK의 rename→seed→역방향 rename을 테스트했다. 운영 SQL 덤프 restore는 실행하지 않았다. 배포가 실패했다면 다음 순서를 사용한다.

1. 실제 대상 PK/현재 아이디·충돌을 재확인. 이미 rename된 경우 검증된 candidate 명령으로 admin→verify-admin을 같은 PK1에서 역변경한다. 충돌이 생겼으면 삭제/병합하지 않고 중단한다.
2. 보존한 pre-tutorial 이미지로 web/proxy 기본 태그를 되돌리고 Preview web/mail/proxy만 복구한다. DB/cache/volumes는 유지한다.
3. env 원본은 private에 보존돼 있다. 다만 구버전이 public opt-in을 모르면 가입 승인을 유지하기 위해 구버전의 ACCOUNT_APPROVAL_MODE=manual 대안을 사용해야 한다. 기존 active 계정은 그대로이며 정책 차이는 기록한다. auto를 무심코 되살리지 않는다.
4. 사용자가 새로 만든 데이터나 기존 로그를 지우는 DB 초기화/덤프 덮어쓰기 방식은 사용하지 않는다. 복구 원인과 추가 승인 필요 사항을 보고한다.

이번 실제 배포는 healthy/보존 검사에 성공해 운영 롤백을 실행하지 않았다. 백업·이전 이미지·private env 원본은 보존한다. 작업 소유 임시 테스트 자원만 소유권 검사 후 정리한다.

## 6. 관리자 안내와 남은 범위

- 관리자 아이디: **admin**
- 비밀번호: **기존 비밀번호 유지**
- 로그인: https://ui.jinnuu.site/accounts/login/
- 비밀번호를 모르면 소유권 확인 후 별도 승인된 대화형 `manage.py changepassword admin` 절차를 사용한다. 이번에는 실행하지 않았다. 실제 SMTP는 disabled이므로 이메일 재설정 발송 성공을 약속하지 않는다.

튜토리얼은 업무 실행기가 아니고 읽음100%는 발주 완료가 아니다. Phase2 취소·분납·정정·반품·불변 발행본·실측 입력/AI연계는 [별도 설계](NUTRITIONIST_PHASE2_PLAN.md)이며 이번 DB에 적용하지 않았다. 제품은 검증된 정상 업무/가이드 사용이 가능한 Preview이고 전 현업 예외 처리·상용 운영 완료가 아니다.
