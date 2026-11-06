# SNP Phase 2 구현 — 첫 검증 단위 (2-A)

작성: 2026-11-06 KST. 기준 HEAD `2d3ac0b478bedd20170f05e870add4caa07e1dd0`, 작업 브랜치 `feature/ui-redesign-three-modes`.

**Phase 2 전체 완료가 아니다.** 이번에 실제 구현·검증한 단위는 회차별 반복 납품, 구매자 검수, 합격량 입고, 잔량 및 월말 검토 집계 연결이다. 2-B/2-C는 아래와 별도 잔여 보고서에 명시한다. 실제 Preview 배포/마이그레이션은 수행하지 않았다.

## 범위와 상태

| 요구사항 | 상태 | 실제 결과 |
|---|---|---|
| 반복 납품 및 회차별 검수 | 완료 (신규 경로 범위) | 한 발주 여러 회차, 복수 품목, 예정일·담당자·수량·단위·실납일·검사자·합격·불합격·기한·사유 보존 |
| 합격량만 재고 반영 | 완료 | 별도 입고 로그/lot, 동일 검수 재시도는 기존 결과 반환, 변경된 재전송은 차단 |
| 누적 실납/합격/불합격/잔량 | 완료 | 합격 기준 잔량, 미검수 예정량 별도 예약, 불합격분 추가 납품 가능 |
| 공급업체 데이터 격리 | 완료 (신규 경로 범위) | 검증된 membership의 canonical supplier owner로 제한, 타 업체 404, 공급업체 검사 확정 금지 |
| 검수 목록·공급업체 상세·월말 검토 집계 | 완료 | 신규 합격량 표시, 기존 단건 검수와 중복 합산 없음 |
| 납품 일정 변경/회차 취소/출고 회차 상태 | 미구현 | 등록 회차는 수정 불가. 원본 보존. 예정·검수 대기는 표시하지만 차수별 출고 상태 전이 미구현 |
| 발주 취소·정정·재발주 | 설계 완료 | 기존 Phase 2 계획 유지. 실행 코드 미추가 |
| 검수 정정/사후 재고 보정 | 설계 완료 | 기존 원본 덮어쓰기 차단 유지. 승인·보정 서비스 미추가 |
| 반품·교환·재배송 | 부분 완료 | 불합격량을 미납으로 남기고 새 회차로 재납품·독립 검수 가능. 반품 요청/연결/회수/교환 승인/입고 후 반품은 미구현 |
| 발행 발주서·조리지시서 버전 | 설계 완료 | 별도 immutable issue/snapshot 모델 미추가. 기존 문서·조리지시서 기능은 유지 |
| 업무 상태·이력 UI | 부분 완료 | 회차·수량·사유·완료·검수대기 화면 제공. 전역 알림/변경요청 작업함 미추가 |
| 역할별 통합 검증 | 부분 완료 | 신규 supplier/buyer E2E 및 기존 전체 자동화 회귀 실행. 실제 현업 인수는 미실시 |

## 모델·migration 및 보존

추가 migration: `procurement/migrations/0013_repeated_deliveries.py`.

- `DeliveryBatch`: 발주, 순번, unique 요청 UUID, 예정일, 담당자, 등록자/시각, 비고.
- `DeliveryBatchLine`: 회차·기존 OrderItem 참조, 예정 기준량, 재고 단위 및 규격 snapshot. 회차별 품목 unique, 양수 제약.
- `DeliveryReceipt`: 회차 품목 OneToOne, 실납·합격, 실제 납품일, 규격·비고·유통기한, 검사자/시각, unique 입고 로그. 0 ≤ 합격 ≤ 실납 DB 제약.
- 기존 `GoodsInspection.order_item` OneToOne, PK, 원본 수량, 기존 입고 로그 및 lot를 변경하지 않는다. 기존 검수를 신규 검수로 복제하지 않는다. 읽기 adapter가 기존/신규 합격량을 읽는다.
- 기존 완료/단건 검수 품목은 자동 재개하지 않는다. 새 회차가 있는 품목은 기존 단건 검사 URL에서 새 화면으로 안내하고 서비스에서도 혼용을 거부한다.
- 정방향 migration은 세 테이블과 제약 추가만 수행. 기존 업무 테이블 데이터 UPDATE/DELETE 없음. 신기능 미사용 시 왕복 migration 보존 검증 통과.
- 이력이 생성된 뒤 역migration으로 세 테이블을 삭제하려 하면 **IrreversibleError**로 먼저 차단한다. 이는 사용 후 무조건 downgrade가 안전하다는 뜻이 아니다. 배포 전 백업·격리 복원과 구버전의 신규 입고 이력 읽기 호환 검토가 필요하다.

실제 Preview는 읽기 전용 트랜잭션으로 테이블/건수만 확인했다. 사용자9, 발주2, 품목2, 기존검수2, 재고로그6이며 시작/종료 동일. 신규 납품 테이블 없음. 이 건수 비교가 전체 데이터 내용 hash 검증을 대신하지는 않는다.

## 서비스와 트랜잭션

`procurement/deliveries.py`:

- 수량 Decimal, 유한수·0/양수·최대값·소수6자리, 날짜·기한·사유·길이 검증.
- 공급업체: policy mutex → 사용자 → 검증 membership → 해당 업체 발주 row lock. 수락된 발주만 등록. 등록 자체는 재고를 쓰지 않는다.
- 구매자: policy mutex → 사용자 → 발주 → 품목 → 식재료 row lock. 승인된 검사자만 합격 확정. 공급업체 겸 관리자도 신규 검사 서비스에서는 거부.
- 예정 잔량은 `발주 기준량 - 누적 합격량 - 미검수 예정량`. 신규 경로는 승인 정책이 없는 초과량을 자동 처리하지 않는다. 기존 단건 경로의 사유 있는 초과 검수 정책은 변경하지 않는다.
- 동일 요청 UUID/동일 내용은 같은 회차, 다른 내용은 오류. 같은 회차 검수의 동일 내용은 같은 원본 반환, 다른 내용은 정정 절차 안내.
- 합격 시 기존 `InventoryLog(입고)` 및 `register_lot` 재사용. 모두 같은 원자적 transaction. 전체 품목 합격 잔량0일 때만 신규 경로가 완료 처리.
- 기존 `inspect_item`도 발주→품목 lock 순서를 사용하여 신규 경로와 이중 입고를 막는다.
- 기존 supplier fulfillment 편집은 납품 회차 생성 이후 차단. 과거 출고 기록을 수정하여 새 납품 사실을 만들지 않는다.

공통 policy mutex는 안전성을 우선한 기존 패턴이다. 공급업체 등록/역할 변경/검수의 동시 처리량에 영향을 줄 수 있으며 부하 검증은 하지 않았다.

## 화면 연결

| 사용자 | 경로 | 진입점 |
|---|---|---|
| 공급업체 | `/procurement/portal/orders/<pk>/deliveries/` | 기존 업체별 구매발주서 상세의 회차별 납품 링크 |
| 구매자/조회 허용 사용자 | `/procurement/orders/<pk>/deliveries/` | 기존 검수 목록의 회차별 납품·검수 링크, 회차 있는 품목의 기존 검사 URL redirect |

공급업체는 등록/이력, 구매자는 검사 확정/이력, VIEWER는 조회만 제공한다. CSRF, 공통 RBAC 및 서비스 권한 검사를 함께 적용. 미지원 정정·사후 반품 및 단위/포장량 구분을 화면에 명시했다. 기존 튜토리얼/독립 식수/Green·Civic·Reference 유지, 중복 업무 로직 미추가.

## 수정 파일과 이유

| 파일 | 이유 |
|---|---|
| `procurement/models.py`, `migrations/0013_repeated_deliveries.py` | 기존 관계를 보존한 회차·반복 검사 저장소 및 제약 |
| `procurement/deliveries.py` | 수량·상태·권한·멱등·동시 입고 서비스 |
| `procurement/delivery_views.py`, `procurement/urls.py` | 역할별 실제 GET/POST 화면 |
| `accounts/rbac.py` | 구매자 조회/검수 쓰기 capability 구분 |
| `procurement/workflow.py` | 기존 검사와 회차 검수 혼용 차단 및 lock 순서 |
| `procurement/portal_services.py`, `portal_views.py` | 등록 후 레거시 수주 변경 제한, 누적량 연결 |
| `procurement/workflow_views.py` | 새 화면 진입, 반복 검사 합격액 월말 검토 집계 |
| `templates/workflow/deliveries.html` | 공통 3모드 회차·검수 화면 |
| `templates/portal/detail.html`, `templates/workflow/inspections.html`, `settlement.html` | 링크·누적량·집계 의미 반영 |
| `integration_tests/test_deliveries.py` | 신규36개 테스트 (31기능+3경합+2migration) |
| `verification/phase2-20261106/` | 격리 실행 스크립트·로그·9스크린샷·DB 대사·서비스 보호 증거 |
| 본 보고서 및 PHASE2_TEST_REPORT/REMAINING | 완료 범위와 미완료·정책 확인 구분 |

AI 코드·모델/기존 비밀번호/관리자 계정/승인 정책/운영 Compose는 변경하지 않았다. `change_password.sh`는 기존 미추적 상태 그대로 보존하고 커밋하지 않는다.

## 검증 및 운영 판단

SQLite354pass/7skip, MariaDB361pass, JS17pass. Chromium10개 검증 지점 통과. 자세한 명령·초기 실패·한계는 테스트 보고서 참조.

이 단위는 **격리 환경 시연 가능**하다. 현재 공개 Preview에는 반영되지 않았으며, 전체 Phase 2 또는 현업 적용 완료로 판단하지 않는다. 배포, 실제 DB migration, 업무 정책 전환, 초과 납품/검수 정정/사후 반품의 승인 책임은 별도 검토·승인 대상이다.
