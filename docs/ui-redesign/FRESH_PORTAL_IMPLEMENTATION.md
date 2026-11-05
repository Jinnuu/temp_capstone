# Green/Civic · 공급업체 포털 · 관리자 계층

2026-11-05, `feature/ui-redesign-three-modes`, 기준 `e29d9bd90a0016a349c121609afae30c5a5883ac`. 기존 기능을 확장했다. 과거 `RBAC_AND_APPROVAL.md`의 SYSTEM_ADMIN/공급업체 접근 설명은 이 문서로 갱신한다. 기존 실행 로그는 당시 증거로 보존한다.

## 실제 영양사 디자인 피드백

사용자가 제공한 `DOREMI.png`를 실제 열어 확인했다. 넓은 사진 배너, 일정/운영 정보의 병렬 배치, 하단 지표·공지 구조를 참고했다. 원본에 있는 로고·광고·상품·연락처·수치는 복제하지 않았다. 원본 파일은 수정하지 않고 Git에서 제외했다.

Green은 따뜻한 아이보리·화이트, 녹색 포인트와 신선 식재료 배너를 사용한다. Civic은 회색·청록, 절제된 사진과 명확한 표를 유지한다. Reference와 기존 저장된 모드 선택/전환 로직은 보존한다. 신규 브라우저의 기본 Reference를 강제로 Green으로 바꾸지는 않았다. Green을 추천 후보로 개선한 것이다.

배너 사진은 imagegen으로 새로 생성한 원본 자산 `static/ui/images/fresh-produce-original.png`다. 실제 납품 상품의 사진이라고 주장하지 않는다. 생성 출처와 조건은 같은 디렉터리의 `ASSET_PROVENANCE.md`에 기록했다. 외부 이미지 CDN·추가 패키지를 쓰지 않는다. 크기를 확보해 이미지 실패 시 배너/데이터 레이아웃이 유지된다. 빌드 CSS/JS URL 버전을 추가해 예전 캐시 때문에 새 UI가 보이지 않는 문제를 줄였다.

영양사 대시보드는 기존 식단/예측/달력을 보존하면서 사진 배너 옆에 **AI 참고값·영양사 입력·최종 확정**을 별도로 표시한다. 미확정 식수를 예측으로 채우지 않는다. 발주 대기는 기존 발주 상태, 입고 예정은 공급업체 납품 일정, 검수 필요는 미검수 품목, 부족 재고는 기존 재고 집계에서 조회한다. 공급업체가 일정에 입력하지 않으면 입고 예정으로 계산하지 않는다. Green/Civic의 중복 요약을 줄이고 기존 Reference 배치를 유지했다.

공지사항은 새 Announcement DB의 활성 게시글만 표시하며 없으면 빈 상태를 표시한다. 기존 Django 최고관리자가 native admin에서 게시할 수 있다. 일반 영양사 화면의 최근 활동은 본인 감사 기록만 조회한다. 전체 타인 계정 이력을 대시보드에 노출하지 않는다. 임의 KPI·공지·실적을 운영 DB에 넣지 않았다.

## 계정 가입과 업무 진입

- 기존 가입 폼·이메일·비밀번호 검증/CSRF/복구를 유지한다. 가입 유형은 DIETITIAN 또는 SUPPLIER만 받는다. 예전 가입 요청이 유형을 생략하면 DIETITIAN으로 호환한다.
- 영양사는 기본 DIETITIAN이다. 공급업체는 legacy `User.role=SUPPLIER`와 업무 SUPPLIER 역할을 갖는다. 업체명·담당자·연락처가 필수다. role/is_staff/is_superuser/groups를 가입 요청에 추가해도 권한은 생기지 않는다.
- Preview auto에서는 두 유형 모두 즉시 로그인한다. 일반 설정의 기본 manual은 바꾸지 않았다. 공급업체 로그인과 업체 주문 접근은 별도다.
- 로그인 기본 진입은 MAIN/SUB 관리자 대시보드, 공급업체 대시보드, 영양사 홈, 입고·검수, 조리, 조회 영역으로 구분한다. 안전한 next URL은 기존 Django 정책을 유지한다.
- 다중 역할 사용자는 공통 헤더의 **업무 영역**에서 허용된 영역을 선택한다. 메뉴 숨김만으로 권한을 구현하지 않는다.

## 공급업체 소속 확인

기존 주문 FK는 `PurchaseOrder.supplier → User`, 거래처 프로필은 `Supplier.user → User(OneToOne)`다. 이를 바꾸거나 주문을 새 계정으로 옮기지 않았다. `SupplierMembership`은 로그인 계정을 거래처에 연결한다. 같은 거래처의 여러 로그인 계정이 기존 발주용 User를 공유해 조회할 수 있다.

신규 가입은 PENDING membership만 만든다. 상호가 같다고 자동 승인하거나 기존 업체 계정을 빼앗지 않는다. 관리자는 `/procurement/supplier-memberships/`에서 외부로 확인한 근거를 기록한 뒤 기존 거래처를 선택한다. 신규 업체 생성은 별도 체크와 확인 근거가 필요하며 같은 상호가 있으면 거부한다. 법적 사업자 식별/소유권을 상호 문자열에서 추정하지 않는다. 사업자·담당자 실재 확인은 사람의 업무다.

현재 계정에 연결된 업체 변경도 관리자 승인·revision 검사를 거친다. 자신의 소속은 스스로 승인하지 못한다. SUB_ADMIN은 관리자 계정의 소속을 변경할 수 없고 MAIN_ADMIN이 담당한다. 기존 `Supplier.user`에 명시적으로 연결된 공급업체는 기존 관리자 연결을 근거로 migration에서 보존한다. 연결이 없는 기존 계정은 확인 대기다. 비밀번호·이메일·이름·staff/superuser·활성 상태는 migration에서 바꾸지 않는다.

새 포털 로그인은 `registered_via_portal`로 구분한다. 직원 계정은 기존 거래처의 발주용 User를 대신하지 않으며, 식재료/규격/연락처의 발주처 선택·엑셀 업체 조회·발주 생성에서 독립 공급처로 사용하지 못한다. 신규 회사는 관리자가 명시적으로 새 거래처를 생성·승인한 뒤에만 발주처로 사용할 수 있다. 기존 레거시 발주처 선택은 유지했다. 실제 주문의 FK가 되는 업체 계정은 다른 회사로 재소속시키지 않고 별도 직원 계정을 사용한다. 직원의 소속 변경은 정상 승인 절차로 가능하다.

목록·검색·정렬·상세·JSON·Excel·수주 POST는 모두 검증된 membership의 `Supplier.user_id`로 필터한다. 다른 업체의 실제 ID와 없는 ID는 동일한 404다. 검증 전 주문 데이터는 403이며 대기 화면만 볼 수 있다. 소속 변경 후에는 이전 업체 주문을 조회할 수 없다. 연결된 거래처 프로필 삭제는 데이터 보호 오류 대신 안내하고 보존한다.

## 발주·수주·납품·검수 상태

기존 `PurchaseOrder.status`와 재고 처리는 그대로 두고 `SupplierFulfillment`에 별도 수주 상태를 저장한다.

```text
NEW → ACKNOWLEDGED → ACCEPTED → PREPARING → DISPATCHED
  └──────────→ ACCEPTED
NEW / ACKNOWLEDGED → REJECTED (사유 필수)
```

수락 전 접수 확인을 생략하고 수락·거절할 수 있다. 수락 이후 출고 전에는 같은 상태로 예정일/수량을 수정할 수 있다. DISPATCHED/REJECTED는 최종 상태다. 반려가 내부 발주를 자동 취소하거나 재고를 바꾸지는 않는다. 발주 취소/재발주는 영양사와 협의해야 하며 새 취소 업무를 임의로 만들지 않았다.

납품 예정량은 **재료 기준 단위**로 입력한다. 발주 포장 단위·명시 규격·기준량·금액은 읽기 전용이며 기존 OrderItem 속성과 업체별 Excel 출력을 재사용한다. 예정량은 0 이상/기준량 이하·소수 여섯째 자리까지, 전체 0은 거부한다. 납품일은 오늘 이후다. 과거 검수 완료 발주에는 새로운 공급업체 이력을 만들어내지 않고 읽기 전용으로 표시한다. 기존 `배송완료` 상태도 완료로 취급한다.

공급업체는 검수 합격량/재고/단가/품목/소속을 POST로 조작할 수 없다. 수주 상태 저장은 재고 관련 모델을 쓰지 않는다. 내부 검수 화면에 수락/예정일/기준 단위 예정량/출고 상태/비고를 표시하고 **기존 inspect_item**이 실제 합격량만 입고한다. 검수가 하나라도 시작되면 공급업체 수정은 중지한다. 기존 중복 검수 방지·재고 lot/FIFO·수불·정산을 재사용했다.

정책 singleton을 먼저 잠근 후 계정·membership·발주를 확인하여 권한/소속 변경과 경합하지 않도록 한다. revision이 다른 중복/오래된 요청은 거부하고 같은 요청을 두 번 반영하지 않는다. MariaDB 동시 요청에서 성공 1건/충돌 1건을 확인했다. 이 범위는 한 발주의 한 수주·출고 이력이다. 분할/반복 출고·반품·재배송 정정은 추가 설계 대상이다.

## 관리자 계층과 권한

| 권한 | MAIN_ADMIN | SUB_ADMIN | 일반 역할 |
|---|---|---|---|
| 전체 사용자·관리자 조회 | 허용 | 일반 계정만 | 거부 |
| 일반 사용자 상태·일반 역할 변경 | 허용 | 허용 | 거부 |
| 업체 소속 확인 | 허용 | 일반 계정만, 자기 승인 금지 | 거부 |
| SUB_ADMIN 임명/해제·신청 심사 | 허용 | 거부 | 신청만 가능 |
| MAIN_ADMIN/다른 관리자 변경 | 보호 규칙 내 허용 | 거부 | 거부 |
| 감사 로그 | 전체 | 일반 계정의 제한된 이력 | 본인 활동 일부 |
| 정책 조회 | 허용 | 조회만 | 거부 |
| 정책/보안 설정 HTTP 변경 | 제공하지 않음 | 거부 | 거부 |
| native Django admin | MAIN + 기존 staff 조건 | 거부 | 거부 |
| 영양사·재고·발주·검수·조리 업무 | 허용 | 허용 | 기존 역할대로 |
| 자기 업체 포털 | 내부 발주 관리 화면 사용 | 공급업체 겸임 + 확인된 소속 | SUPPLIER + 확인된 소속 |

기존 SYSTEM_ADMIN은 MAIN_ADMIN 하위 호환 별칭으로 해석한다. migration은 기존 SYSTEM_ADMIN 멤버와 superuser 등 기존 최고관리 권한을 보존해 MAIN_ADMIN으로 정규화한다. **이미 일반 역할로 강등된 managed legacy ADMIN을 다시 승격하지 않는다.** staff만 보고 새 MAIN 그룹을 부여하지 않는다. 기존 trusted ORM 생성 경로의 레거시 권한 호환은 유지하며 공개 가입은 항상 managed로 저장한다. Django superuser는 MAIN 권한을 유지한다. 앱 역할 부여만으로 staff/superuser가 되지 않는다.

정책 행 잠금·작업자 재조회·revision·감사 기록을 기존 서비스에서 확장했다. 자신의 관리자 상태/권한 변경, 마지막 활성 MAIN 제거, SUB의 관리자 대상 조회/직접 API/역할 alias를 통한 승격을 차단한다. SUB 감사 화면에는 보안 정책/관리자 역할 변경 이력을 노출하지 않는다.

사용자 확인에 따라 **공급업체도 MAIN_ADMIN 승인 후 SUB_ADMIN을 겸임**할 수 있다. 포털은 이 경우에도 자기 업체 필터를 유지한다. 별도 내부 운영 영역에서는 SUB_ADMIN에게 부여한 전체 업무 범위를 사용하므로 여러 업체의 내부 자료를 관리할 수 있다. 이 예외는 단순 공급업체가 아닌 명시적으로 승인된 내부 운영 관리자 권한이다. 공급업체를 겸임한 SUB는 직접 재고 거래/검수 합격량 쓰기를 제외하며 서버 미들웨어와 기존 재고·검수 서비스에서도 차단한다. 실제 합격량은 별도 영양사/재고 담당자가 확정해야 한다. SUB 회수 시 내부 관리 접근은 즉시 차단되고 공급업체 소속/로그인은 유지된다.

관리자 신청은 `/accounts/admin-request/`에서 사유만 제출한다. 기존 로그인/일반 역할을 변경하지 않는다. MAIN이 `/accounts/manage/requests/`에서 승인하면 SUB만 추가하고, 거절하면 일반 계정을 유지한다. 중복 대기 신청은 새 행을 만들지 않고, 심사 revision과 완료 상태를 검사한다. 관리자 신청의 role/is_staff/is_superuser 입력은 거부한다. 승인·거절·역할 부여/회수·차단은 감사 기록에 남는다.

**새 admin 계정은 만들지 않았다.** 사용자가 기존 최고관리자 유지를 확인했다. 고정 비밀번호·초기화·강제 비밀번호 변경을 추가하지 않았고 기존 비밀번호를 변경하지 않았다.

## 주요 URL

| URL | 목적 |
|---|---|
| `/accounts/workspaces/` | 다중 역할 업무 영역 선택 |
| `/accounts/manage/dashboard/` | MAIN/SUB 관리자 대시보드 |
| `/accounts/manage/requests/` | MAIN의 관리자 신청 심사 |
| `/accounts/admin-request/` | 일반 계정 관리자 권한 신청 |
| `/procurement/portal/` | 공급업체 대시보드/소속 대기 |
| `/procurement/portal/orders/` | 소속 업체 발주 목록·검색·정렬·JSON |
| `/procurement/portal/orders/<id>/` | 발주 상세/수주 처리/JSON/인쇄 |
| `/procurement/portal/orders/<id>/export/` | 해당 업체의 해당 주문 Excel |
| `/procurement/supplier-memberships/` | 관리자 업체 소속 확인 |

## 데이터·배포·복구

추가 migration: `accounts/0004_adminrolerequest_announcement.py`, `procurement/0010_supplierdeliveryline_supplierfulfillment_and_more.py`, `0011_initialize_portal_roles.py`, `0012_suppliermembership_registered_via_portal.py`. 기존 9개 계정/50개 migration의 DB 스냅샷을 private SQL로 보관하고 별도 tmpfs MariaDB에 복원한 뒤 업그레이드해 신원/활성 상태/기존 최고관리자를 검증했다. 원본 SQL/계정 스냅샷/환경 파일은 Git에 넣지 않는다.

배포는 Preview의 web/recovery-mail/proxy만 `--no-deps`로 갱신한다. DB/cache 컨테이너나 운영 네트워크/볼륨은 재생성하지 않는다. `pre-fresh-e29d9bd` 웹/프록시 이미지 태그를 보존했다. 그룹 정규화 때문에 이전 이미지 태그만 바꾸는 롤백은 보장하지 않는다. 실제 복구가 필요하면 새 사용자/업무 변경을 먼저 보존하고 private 스냅샷을 별도 DB에서 검증한 뒤 Preview 범위의 복구를 결정해야 한다. 자동 복원/삭제 명령은 실행하지 않았다.

SMTP/기존 비밀번호 복구 환경과 AI 모델은 보존한다. 실제 외부 SMTP는 여전히 미설정이다. 테스트와 공개 검증의 범위·제한은 `FRESH_PORTAL_TEST_REPORT.md`를 따른다.
