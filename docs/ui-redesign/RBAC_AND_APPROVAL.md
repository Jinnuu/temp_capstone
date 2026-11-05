# UI Preview 계정 승인·관리자·역할 관리

대상: `feature/ui-redesign-three-modes`, 기준 `85e83f9`. 실제 반영 대상은 `snp-ui-preview`와 `https://ui.jinnuu.site`뿐이다. `sprint-final`, 8000/8007/8010, 운영 DB·볼륨·AI 모델에는 적용하지 않았다.

## 승인 정책과 기존 계정

`ACCOUNT_APPROVAL_MODE=manual|auto`. 일반 설정 기본값은 **manual**, Preview Compose 기본값은 **auto**다. 잘못된 값은 시작 단계에서 거부한다. 정책은 환경변수가 결정하며 관리자 화면에서는 조회만 한다. 시작 시 `sync_access_policy`가 이전 값과 달라졌을 때 SYSTEM 작업자로 감사 이벤트를 기록한다.

신규 가입은 기존 Django 회원가입 폼/이메일/비밀번호 검증을 그대로 사용한다. auto는 ACTIVE, manual은 PENDING으로 저장한다. 기본 그룹은 `SNP_ROLE_DIETITIAN`이며, 요청으로 보낸 role/is_staff/is_superuser/groups는 회원가입 필드가 아니므로 적용되지 않는다. 자동 승인은 **Preview 가입 사용자에게 실제 영양사 업무 권한을 주는 정책**이므로 운영 환경에 그대로 사용하면 안 된다.

기존 모델에는 `is_active`만 있어 비활성 사유를 복원할 수 없었다. 데이터 마이그레이션은 기존 활성 계정을 ACTIVE, 모든 기존 비활성 계정을 LEGACY_INACTIVE(확인 필요)로 보존한다. 비밀번호·이메일·기존 role·staff/superuser 플래그를 변경하지 않는다. PENDING/ACTIVE/SUSPENDED/DISABLED/WITHDRAWN을 새로 구분하며 탈퇴 계정 복구는 금지한다.

사용자가 승인 대기로 확인한 두 계정만 다음 명령으로 처리했다. 기존 비활성 + 영양사 + staff/superuser 아님 + 로그인 이력 없음 + Django 관리자 변경 이력 없음 조건을 추가 확인한다. 전체 비활성 사용자를 자동 활성화하지 않는다.

```bash
docker compose -p snp-ui-preview --env-file .ui-preview/compose.env -f compose.ui-preview.yml exec -T web \
  python -B manage.py approve_preview_signups --actor verify-admin \
  --confirmed-signup wlsdngur12 swwlsdngur12
```

PENDING 분류와 승인 각각을 기록하며 두 번째 실행은 승인 0건이다. 다른 기존 비활성 계정 1개는 LEGACY_INACTIVE로 남겼다. 임의 이메일 입력, 비밀번호 재설정, 소유권 변경은 하지 않았다.

## 역할과 권한

Django의 기존 Groups 다대다 관계를 재사용한다. 고정 그룹 이름은 `SNP_ROLE_` 접두사를 사용한다. 사용자에게 여러 그룹을 부여하며 권한은 합집합이다. 다른 기존 그룹은 보존한다. 일반 그룹의 Django Permission을 편집해서 애플리케이션 권한을 늘릴 수는 없다. 정의는 `accounts/rbac.py`에 있고 실제 URL 전체 분류는 `verification/rbac-20261105/endpoint-permissions.json`에 있다.

| 업무 | SYSTEM_ADMIN | DIETITIAN | INVENTORY_MANAGER | COOK | VIEWER |
|---|---|---|---|---|---|
| 운영현황 요약 | 조회 | 조회 | 조회 | 조회 | 조회 |
| 식단·메뉴·레시피 | 읽기/쓰기 | 읽기/쓰기 | 읽기 | 읽기 | 읽기 |
| 예측 실행·최종 식수 확정 | 읽기/쓰기 | 읽기/쓰기 | 읽기 | — | 읽기 |
| 발주계획·발주 | 읽기/쓰기 | 읽기/쓰기 | 읽기/쓰기¹ | — | 읽기 |
| 검수·합격량 입고 | 읽기/쓰기 | 읽기/쓰기 | 읽기/쓰기 | — | 읽기 |
| 식재료·재고·수불 | 읽기/쓰기 | 읽기/쓰기 | 읽기/쓰기 | — | 읽기 |
| 조리지시서·기간별 조리지시서 | 읽기/쓰기 | 읽기/쓰기 | 읽기 | 읽기/쓰기² | 읽기 |
| 정산·업무 문서 | 조회 | 조회 | 조회 | 조리 문서만 | 조회 |
| 규격·분류·거래처 기준정보 수정 | 허용 | — | 허용 | — | — |
| 공급업체 로그인 계정 관리 | 허용 | — | — | — | — |
| 사용자·역할·감사 로그·정책 조회 | 허용 | — | — | — | — |

¹ 기존 발주예정서 확정의 작성자 또는 시스템 관리자 조건도 유지한다. 타인이 만든 계획을 재고 담당자가 임의 확정하도록 넓히지 않는다. ² 기존 지시사항·재고 사용 메모 입력 기능이다. 별도 조리 진행 상태 기능을 새로 만들거나 완료했다고 주장하지 않는다. 규격/분류 페이지는 기존에 조회와 편집이 결합되어 있어 편집 권한이 있는 역할만 접근한다. 순수 규격 조회 화면을 추가한 것은 아니다.

### Django 최고관리자와의 관계

Django superuser는 항상 SYSTEM_ADMIN 권한을 갖는다. 애플리케이션 SYSTEM_ADMIN 그룹을 부여하는 것만으로 is_staff/is_superuser나 Django 관리 사이트 권한을 주지 않는다. `/admin/`은 기존 staff 조건과 애플리케이션 관리자 조건을 모두 충족해야 한다. 사용자·그룹의 원시 Django admin 추가/수정/삭제는 차단하고 감사 서비스가 있는 새 화면을 사용한다. 이를 통해 그룹 편집이나 is_active 직접 변경으로 보호 규칙을 우회할 수 없게 했다.

기존 사용자 초기 변환: superuser/legacy ADMIN → SYSTEM_ADMIN, 영양사 → DIETITIAN, 기존 staff 영양사 → DIETITIAN + INVENTORY_MANAGER, 공급업체 → 내부 역할 없음. 기존 직접 ORM 생성 코드/테스트의 호환성을 위해 `rbac_managed=False`인 신뢰된 레거시 생성 사용자는 기존 구분을 적용한다. 공개 가입과 마이그레이션된 실제 계정은 모두 managed다. 신규 관리 명령을 개발할 때는 역할 초기화를 명시해야 한다.

## 서버 검증과 관리자 보호

`BusinessAccessMiddleware.process_view`가 실제 resolver 이름과 메서드로 권한을 판정한다. 공개 인증 URL은 명시적 허용 목록이다. 이름을 알 수 없는 내부 화면은 거부한다. POST/PUT/PATCH/DELETE는 쓰기 권한을 요구하며, 등록·수정 폼 일부는 GET도 쓰기 권한이 필요하다. 메뉴 숨김 및 조회 전용 폼 비활성화는 보조 표시이며 직접 요청도 서버에서 거부한다. 기존 CSRF와 세션 검증을 유지한다.

`ApprovalBackend`는 활성 여부와 명시적 상태를 함께 검사한다. 역할은 요청마다 DB에서 계산하여 권한 회수가 즉시 반영된다. 기존 ModelBackend 이름으로 저장된 로그인 세션은 배포 후 재로그인이 필요하다. 비밀번호 해시나 사용자 데이터를 바꿔 세션을 복구하지 않는다.

`change_access`는 정책 singleton 행을 먼저 잠그고 작업자/대상을 다시 읽는다. 역할·상태 변경은 트랜잭션으로 처리하며 `access_revision` 충돌은 409다. 자신의 역할/상태 변경, 마지막 활성 관리자 제거, 일반 시스템 관리자의 superuser 변경, 탈퇴 복구, 확인 필요 계정의 즉시 활성화, 공급업체에 내부 역할 부여를 거부한다. 동시에 서로를 강등하는 경우 한 요청만 성공한다. SQLite의 행 잠금 검증은 지원되지 않아 MariaDB에서 검증했다.

## 관리자 화면

| URL | 기능 |
|---|---|
| `/accounts/manage/` | 아이디·이름·이메일 검색, 상태 필터, 상태·역할·최근 로그인, 최대 200명 |
| `/accounts/manage/users/<id>/` | 읽기 전용 신원 정보, 상태·다중 역할 저장, 현재 유효 권한, 최근 감사 이력 |
| `/accounts/manage/permissions/` | 고정 역할 매트릭스, 환경 승인 정책 조회 |
| `/accounts/manage/audit/` | 성공/거부 필터, 작업자·대상·시각·전후 상태, 최신 200개 |
| `/accounts/manage/api/users/<id>/` | 관리자 전용 GET/POST, 필드 허용 목록·revision·CSRF 검사 |

사용자 관리 링크는 공통 헤더에 표시한다. 세 모드 모두 기존 공통 UI를 사용한다. 이 기능은 계정 목록/접근 제어 관리이며, 신원 확인 없는 이메일 변경·계정 복구 대행·세부 권한 자유 편집을 제공하지 않는다.

## 감사 기록

가입 대기/자동 승인, 확인된 가입 대기 분류, 승인·복구·정지·비활성화·탈퇴, 역할 부여·회수, 환경 정책 변경, 관리자 접근 거부, 보호 규칙에 따른 변경 거부를 기록한다. 이벤트에는 작업자/대상 및 레이블, 전후 상태·활성 여부·역할·revision, 시각, 결과, 고정 사유 코드가 있다. 성공 이벤트는 데이터 변경과 함께 커밋한다. 거부 로그는 실패 트랜잭션 밖에서 기록한다. 비밀번호·이메일·인증 토큰·SMTP 자격증명은 저장하지 않는다. 로그 수정/삭제 UI는 없다.

## 마이그레이션·배포·복구

새 마이그레이션은 `accounts/0002_accesspolicy_user_access_revision_user_account_state_and_more.py`, `0003_initialize_access_roles.py`다. Django auth 그룹을 재사용하여 사용자·역할 연결용 별도 테이블을 중복 생성하지 않았다.

Preview DB의 consistent SQL 백업을 **마이그레이션 전에** `.ui-preview/backups/pre-rbac-20261105.sql`에 저장했다(0600, 상위 디렉터리 0700, Git 제외). 별도 tmpfs MariaDB `restore_check`에 복원해 계정 8개·마이그레이션 기록 48개를 확인하고 새 마이그레이션 적용 후 기존 신원/권한 필드 동일성과 비활성 보존을 확인했다. 공개 증거에는 해시·크기·결과만 포함한다. 변경 전 웹/프록시 이미지도 `pre-rbac-85e83f9` 태그로 보존했다.

```bash
docker compose -p snp-ui-preview --env-file .ui-preview/compose.env -f compose.ui-preview.yml build web proxy
docker compose -p snp-ui-preview --env-file .ui-preview/compose.env -f compose.ui-preview.yml up -d --no-deps --wait --wait-timeout 180 web
docker compose -p snp-ui-preview --env-file .ui-preview/compose.env -f compose.ui-preview.yml up -d --no-deps --wait --wait-timeout 180 recovery-mail proxy
```

DB/cache 컨테이너를 재생성하지 않는다. 시작 스크립트의 기존 migrate/중복 방지 seed 뒤에 정책 감사 동기화만 추가했다. 롤백 시 우선 Preview 쓰기를 중단하고 이후 신규 가입/업무 데이터를 보존한 뒤, 보관 이미지와 백업을 별도 DB에서 검증해야 한다. 백업 복원은 후속 데이터를 되돌릴 수 있으므로 자동 복원 명령은 실행하지 않았다. 기존 운영 DB/볼륨 삭제·초기화나 전체 Compose down은 하지 않는다.

실제 SMTP는 여전히 미설정이다. 기존 SMTP 환경변수/secret 및 비동기 복구 구조를 보존했다. 공개 화면은 메일 미설정을 알리고 요청을 503으로 거부한다. 실제 외부 수신은 검증하지 않았다.
