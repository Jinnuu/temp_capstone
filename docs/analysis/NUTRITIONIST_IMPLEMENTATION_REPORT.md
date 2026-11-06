# SNP 현업 고도화 구현 보고서 — Phase 0/1

> 최신 적용 상태(2026-11-06): 사용자 승인으로 Phase1+튜토리얼을 Preview에 배포했다. 실제 최고관리자는 **동일 PK1의 admin**, 기존 비밀번호/9계정/업무 데이터는 보존했고 공개 신규 가입은 승인 필요다. 아래의 미배포·승인 대기·verify-admin 표기는 해당 시점의 이력이다. 최신 실행/보존 결과는 [Preview 배포 보고서](NUTRITIONIST_PREVIEW_DEPLOYMENT.md), 화면은 [튜토리얼 개편](NUTRITIONIST_TUTORIAL_REDESIGN.md), 후속은 [Phase2 설계](NUTRITIONIST_PHASE2_PLAN.md)를 따른다.

2026-11-06 KST. 작업 브랜치 `feature/ui-redesign-three-modes`, 시작 HEAD `3ad73a8bb2caadfe6e9fc0e628f814fbcc9e3617`. 안정 `sprint-final`은 `133b950221bd9cc1effaa51539abf7f88bb095c1` 보존. 최종 로컬 커밋은 이 보고서를 포함하는 Git log와 작업 완료 응답을 따른다.

## 실제 수행 범위와 보존

분석만 수행한 이전 감사의 후속으로 제품 코드를 수정했다. Phase 0와 안전한 Phase 1, 제한된 UI 개선 및 통합 검증을 완료했다. 전체 제품 고도화 완료가 아니다. 신규 스키마/migration은 **없다**. 실제 Preview DB에는 SELECT만 했고 계정 변경, 승인 모드 전환, 비밀번호 변경, migration, 배포/재시작을 실행하지 않았다. 모델 파일·추론 방식·기존 3개 UI 모드를 보존했다.

시작 worktree에는 감사 문서 3개와 사용자 소유로 취급한 `change_password.sh`가 미추적 상태였다. 해당 스크립트는 실행·수정·커밋하지 않았다. 참고 문서와 original `~/sprint7`을 변경하지 않았다. 기존 운영 서비스 및 Preview의 컨테이너/볼륨/네트워크는 변경하지 않았다.

실제 Preview 읽기 전용 사전 검사는 MariaDB `snp_ui_preview`, host `db`, 가입 모드 auto, 사용자 9명, 활성 MAIN 1명(PK=1, username=`verify-admin`, staff/superuser/ACTIVE), username `admin` 충돌 없음이었다. 이는 비밀번호 로그인 성공을 의미하지 않는다. 비밀 환경값·비밀번호 해시·세션/토큰을 보고하지 않았다.

## 작업 단위별 결과

| 항목 | 실제 변경 | 검증/잔여 범위 |
|---|---|---|
| AUD-01 | 기존 업체 계정 수정·프로필 생성/수정/삭제가 공통 대상 보호를 통과. 권한 변경과 같은 policy mutex 및 사용자 행 잠금, 거부 감사는 rollback 밖 기록 | SUB→공급업체 겸 MAIN/SUB/자기 계정 차단, MAIN→SUB·SUB→일반 업체 허용, 일반 공급업체 차단. 관련 Django·실제 CSRF POST 브라우저 통과 |
| AUD-02 | 새 관리자 초기 secret을 demo secret과 분리. 비어 있거나 같은 secret이면 원자적 실패. 기존 MAIN이 이름을 바꿔도 seed가 `verify-admin`을 재생성하지 않음 | 격리 테스트 통과. **실제 기존 관리자 비밀번호가 분리됐다는 뜻은 아님**. 기존 비밀번호와 private 파일을 변경하지 않음 |
| AUD-03 | 공개 가입에 승인 요구를 강제할 수 있는 명시적 opt-in 추가. 가입 성공 메시지를 저장된 활성 상태에 맞춤 | manual/auto 기존 회귀와 opt-in 테스트 통과. 실제 Preview auto 정책 전환은 미실행/승인 대기 |
| AUD-04 | 공통 보고 read model로 AI/수동/최종/실측 분리. 실제 값은 연결된 MealForecast.actual_count만 사용. 결측은 null/미입력, 실측0은0, 분모0/결측 오차 산출 불가 | HTML·JSON·Excel 테스트/브라우저 통과. 실측 입력 UI·책임/수정 이력은 만들지 않음 |
| AUD-05 | 업로드 시 기존 식단 잠금·사용 완료 차단·전체 파일 트랜잭션 보존. 수동/AJAX/업로드/레시피 변경 시 발주 재검토 표식. 완료 메뉴·레시피 일반 편집/업로드 및 native admin 편집 보호. 발주 snapshot/조리 메모 참조 식단 삭제 방지 | 단일/다중 업로드 rollback·서버 폼·AJAX·보호 테스트 통과. 이미 발행됐지만 아직 사용 전인 조리지시서 snapshot은 Phase 2 |
| AUD-06 | 공통 money 서비스로 기록 금액/합격량 비례 금액 계산. 임의10% 가산 제거, 지급액 미확정. 월간 업체 집계 ID 키·화면 ID 표시 | 0·부분 합격·금액 유효성·동명 업체·HTML/Excel 기존 회귀 통과. 과세/면세/할인/운송비/회계 마감은 정책 미확정 |
| 추가 결함 | 빈 월간 정산의 품목 수가 예시12로 표시되던 default 제거 | 수정 전 실패 재현, 수정 후 전체 회귀 포함 |
| A-1 | 기본 dry-run인 관리자 username 전환 관리 명령. apply는 명시 옵션+예상PK 필요. 충돌·카운트·속성·그룹 보존 검증, 감사·반대 방향 rollback 지원 | synthetic DB의 이름/PK/해시/권한/FK/과거 감사 라벨 보존 테스트 통과. **실제 이름 변경 안 함** |
| D-1 일부 | 공급업체 빈 내부 메뉴 그룹 제거, Green/Civic 식수 요약14px, 모바일 배너 사진72px·제목 줄바꿈 개선 | 36개 재촬영 및 신규 화면/DOM 검사. CSS zoom200% 대체 smoke/키보드 접근2모드 통과. WCAG/현업 인수 아님 |

## 수정 파일과 이유

| 파일 | 변경 이유 |
|---|---|
| `accounts/access_service.py` | 공통 업체 대상 보호·직렬화·감사 및 opt-in 가입 승인 |
| `accounts/views.py` | 실제 활성/승인 상태에 맞는 가입 안내 |
| `accounts/preview_bootstrap.py` | 기존 관리자/암호 보존, 분리된 secret·idempotent bootstrap |
| `accounts/management/commands/rename_preview_admin.py` | 승인 후에만 사용하도록 설계한 dry-run/apply/rollback 도구 |
| `config/business_access.py` | 업체 관리 경로의 권한 거부 감사 |
| `config/settings.py`, `config/preview_settings.py`, `compose.ui-preview.yml` | 승인 정책 opt-in·관리자 secret 연결 준비. 실제 env/Compose 서비스에는 미적용 |
| `deploy/ui-preview/prepare.py`, `seed_preview.py` | 새 초기 비밀 분리, 평문 credentials 안내 파일 신규 생성 제거, 기존 계정 보존 |
| `forecasting/services/reporting.py`, `forecasting/views.py`, `templates/docs/weekly_forecast_report.html` | 네 식수 값·결측/오차·최신 예측 선택 기준을 HTML/JSON/Excel에서 공유 |
| `meals/change_policy.py`, `views.py`, `views_extra.py`, `recipe_file_views.py`, `admin.py` | 완료 식단/레시피·참조 삭제 보호, 발주 영향 표시, 업로드 원자성 |
| `procurement/workflow_views.py`, `supplier_views.py` | 레거시 업체 경로 보호, 레시피 변경 검토, 공통 금액 계산 |
| `procurement/money.py`, `views.py`, `team_document_views.py` | 기록/합격량 금액 재사용, 미등록 세금 가산 금지, 업체 ID 집계 |
| `templates/procurement/order_detail.html`, `templates/docs/doc_monthly_settlement.html` | 미확정 지급액·업체 식별·빈 합계0 표시 |
| `templates/partials/top_nav.html`, `frontend/src/ui.css`, `static/ui/build/snp-ui.css` | 역할별 빈 메뉴 제거·읽기/모바일 개선 및 빌드 결과 |
| `integration_tests/test_nutritionist_hardening.py`, `test_preview_admin_safety.py` | 49개 신규 회귀/계약 테스트 |
| `verification/nutritionist-hardening-20261106/` | 실제 실행 로그·재현·격리 브라우저/산출물/보호 증거 |
| 본 보고서 및 NUTRITIONIST 5개 관련 문서 | 최초 감사와 현 구현/잔여 과제/운영 수준 구분 |

사용자 지정 문서/RBAC/Fresh 포털 문서와 현재 모델·URL·기존 실행 로그를 재검토했다. 완결되지 않은 기존 서술은 최초 감사로 남기고 후속 상태를 앞부분/부록에 명시했다.

## 데이터 및 migration 영향

모델 필드·제약·migration 파일 변경 없음. 두 DB에서 `makemigrations --check --dry-run`은 No changes, migrate/migrate --check 통과. 새 DB의 모든 기존 migration을 적용해 검사했다. 이번 실행에서 실제 Preview의 migration이나 데이터를 변경하지 않았다. 이전 백업을 현재 상태로 복구 가능하다고 새로 주장하지 않는다. 실제 계정 전환/배포 직전에는 최신 백업의 격리 복원 확인이 필요하다.

새 bootstrap은 **비어 있는 DB의 최초 관리자만** 독립 secret으로 생성한다. 이미 존재하는 관리자/시범 사용자의 암호·이메일·권한은 바꾸지 않는다. 새 secret 파일은 prepare 코드에 정의했지만 이번에 실제 `.ui-preview`에 생성/적용하지 않았다. 향후 승인된 배포 시 운영자가 준비해야 한다. 기존 credentials 파일/공유 이력과 실제 관리자 비밀번호 분리 여부는 소유자가 별도로 확인해야 한다.

금액 데이터는 기존 estimated_price snapshot을 읽는다. 과세·면세·단가 포함세 여부를 새로 추정하지 않으며 기존 주문금액을 일괄 다시 쓰지 않는다. 합격량 비례 집계는 회계 확정이 아닌 검토용 기존 의미를 유지한다. 최종 지급액·세금은 null/미확정이다. 통화 반올림·할인·배송비·반품 마감 정책은 후속 합의가 필요하다.

## 관리자 username 변경 계획 — 아직 승인 필요

현재 사전 검사: PK1의 verify-admin, 사용자9/활성 MAIN1, admin 충돌 없음. 승인 직전 재검사가 필요하다.

1. 소유권/작업자·현재 계정·충돌·계정/MAIN 수를 재확인하고 최신 private 백업을 격리 DB에 복원 검증한다.
2. 기존 seed를 유지한 채 이름만 바꾸면 재시작 시 verify-admin 재생성 위험이 있으므로, 이번 seed 보호 코드가 사용되는 실행 경로를 먼저 확보한다. 실제 서비스 배포는 별도 승인 대상이다.
3. 검토된 명령이 설치된 **Preview 전용** 환경에서 우선 dry run한다. 현재 실행 중인 이전 이미지에 새 명령이 이미 있다고 가정하지 않는다.

```sh
# 아래는 승인 후 실행할 절차 예시이며 이번에 실행하지 않음.
docker compose -p snp-ui-preview --env-file .ui-preview/compose.env -f compose.ui-preview.yml \
  exec web python manage.py rename_preview_admin
# 별도 승인 후에만 실행. 예상 PK가 달라지면 중단.
docker compose -p snp-ui-preview --env-file .ui-preview/compose.env -f compose.ui-preview.yml \
  exec web python manage.py rename_preview_admin --apply --expected-pk 1
```

ORM 계획은 `transaction.atomic` → `policy_lock` → User PK1 행 잠금 → source/target 충돌·MAIN 검사 → `user.username='admin'; user.save(update_fields=['username'])` → PK/암호/개인정보/그룹·권한/계정 수 보존 확인 → 감사 기록이다. 비밀번호 값은 비교에만 사용하며 출력하지 않는다. FK는 PK 불변이므로 기존 발주/소속/감사/신청 참조가 유지된다. 새 감사 이벤트는 추가하되 기존 역사 라벨은 당시 이름 그대로 둔다.

롤백은 admin이 같은 PK1이고 verify-admin 충돌이 없을 때, 같은 명령의 `--source admin --target verify-admin --apply --expected-pk 1`로 수행한다. 충돌/다른 계정·권한 변화가 있으면 강제 병합/삭제하지 않고 중단한다. 비밀번호를 되돌리거나 새 공용 비밀번호를 설정하지 않는다. 이 경로는 격리 DB에서 테스트했으며 실제 DB에서는 실행하지 않았다.

승인 후 안내는 아이디admin/기존 비밀번호 유지/로그인 URL/본인 확인 후 안전한 대화형 재설정 절차로 제한한다. **현재 실제 아이디는 아직 verify-admin이다.**

## 공개 가입 정책 전환 계획 — 미실행

현재 auto 동작을 임의 변경하지 않았다. `ACCOUNT_PUBLIC_SIGNUP_REQUIRES_APPROVAL`(일반 설정), `SNP_PUBLIC_SIGNUP_REQUIRES_APPROVAL=1`(Preview env opt-in)은 자동 모드에서도 신규 가입을 PENDING/비활성으로 만든다. 기존 활성 계정·비밀번호·역할은 변경하지 않는다. 공급업체 계정 로그인 승인과 업체 소속 VERIFIED는 별개이고 관리자 신청은 별도 MAIN 승인이다.

안전한 순서: 공개 체험 방식 합의 → 격리 신규 영양사/공급업체 가입·승인/복구 리허설 → 실제 설정 전환·배포 별도 승인 → 전환 후 기존 로그인 보존/신규 대기 검증. 과거 auto 가입자의 신원 재검토는 목록·정책 승인 없이 일괄 정지하지 않는다. 전환 전까지 공개 auto 가입의 내부 쓰기 위험은 남는다.

## Phase 2 설계 경계와 보류

다음은 실행 구현이 아닌 후속 설계안이다. 승인 책임과 기존 데이터 호환성을 합의한 뒤 독립 구현한다.

### 발주 취소·재검토·정정 (AUD-07)

- 초안 변경/확정 미입고/일부 검수/전체 검수를 구분. 취소 사유·작업자·전후 revision·대체 발주 연결을 별도 이력으로 보존한다.
- 업체 거절은 주문 취소를 의미하지 않음. 미입고 취소와 대체 발주는 원본 참조·idempotency로 중복 방지. 미납 종결 시 기존 합격 입고를 자동 차감하지 않는다.
- 검수 이후 취소·정정은 AUD-08의 반품/보정 업무로만 처리할지 현업 승인 필요. 이미 사용된 lot를 음수로 역차감하지 않는다.

### 반복 분납·검수 정정 (AUD-08)

- 기존 GoodsInspection OneToOne/응답·inventory_log 링크를 즉시 제거하지 않는다. OrderItem FK의 차수별 Receipt/InspectionBatch를 **추가**하고 request_key/revision·실납/합격·기한·원래 기록/정정 사유를 보존하는 방향을 우선 검토한다.
- data migration은 기존 검사1건→legacy 차수1건을 대응시키고 원래 IN 로그를 재사용하며 재고를 다시 입고하지 않는다. 기존 API는 읽기 호환 요약으로 유지하는 방안을 테스트한다.
- 누적 합격/반품/잔량·업체 약속 수량은 별도 의미. 10kg→6+4, 불합격/교환/미납 종결 정책과 책임자 승인 필요. 공급업체는 자기 업체의 납품 계획만 변경하며 합격량/재고 쓰기 금지.
- 승인된 schema·사본 이관 대사 후 additive migration. 새 차수 데이터가 생긴 뒤 구버전으로 단순 downgrade/drop하지 않는다. 롤백은 기능 차단/읽기 호환과 백업 복원 계획을 별도 승인한다. 이번 migration/변환 실행 없음.

### AI 입력·실측 연계 (AUD-09)

현재 모델/전처리와 CSV fallback을 보존했다. DB 메뉴를 모델 기대 문자열·군집/임베딩 처리와 대조한 golden-input 검증 후 연결해야 한다. 입력 출처·결측·모델 식별/생성 시각·재예측 이력/중복 제약은 후속. 실제 식수 입력은 책임자·입력 시각·정정 감사/권한 설계 후 도입한다. 모델 교체/재학습은 제외한다.

### 과거 문서 보존 (AUD-10)

조리 메모 revision을 발행본 보존으로 취급하지 않는다. 불변 발행 snapshot(배합·식수·단위·규격·메모·양식 버전·발행자/시각·원본/재발행 참조)을 추가하고 explicit POST 발행과 GET 재출력을 분리하는 방향이다. 사용 전 초안 재계산은 유지한다. 작성/확정/발행/변경 요청/재발행/사용 완료의 권한과 마이그레이션은 합의 전 구현하지 않는다.

## 운영 품질 분류와 다음 순서

- 즉시 구현한 범위: AUD-01/04/05의 명확한 보호·의미 오류, AUD-06의 임의 세금/ID/빈 합계, AUD-02의 신규 seed 예방, 승인 opt-in 준비, 제한된 AUD-18.
- 설계 후 구현: AUD-07~11, 조리 실적/협업, 복구·대사·역사 문서. 새 스키마 없이 부분적으로 완료했다고 표시하지 않음.
- 현업 요구 확정: 영양·알레르기 기준, 원가/회계 마감·세금/반품, 다기관 데이터 경계. 안전성이 검증되지 않은 영양·알레르기 정보를 제공하지 않음.

다음 작업은 ①승인할 관리자 이름/공개 가입/배포 범위 결정 ②AUD-07/08 상태 전이·차수 모델·이관 정책 확정 ③AUD-10 발행본 정책 ④모델 입력 호환·실측 책임 검증이다. 실제 서비스 변경 없는 Phase 1 결과를 로컬 커밋으로 보존하고 원격 push/안정 브랜치 병합은 하지 않는다.

테스트와 남은 위험은 [테스트 보고서](NUTRITIONIST_TEST_REPORT.md), [운영 준비도](NUTRITIONIST_OPERATION_READINESS.md)를 따른다. 지금 제품은 통제된 정상 시연에 적합하지만 전 현업 운영/상용화 완료가 아니다.

### 최종 검토 보충

연결된 업체 삭제의 업무 거부도 rollback 밖 DENIED 감사로 남기도록 추가했다. 새 금액 서비스가 기존의 사유 있는 초과 납품을 불필요하게 차단할 수 있는 회귀도 재현 후 제거했다. 기존 검수 정책을 약화/변경한 것이 아니라 그대로 읽도록 보정한 것이다. 최종309개/신규49개 기준에는 두 검사가 포함된다.
