# Green/Civic · 공급업체 포털 · 관리자 계층 설계

기준 e29d9bd, UI 브랜치에서만 확장한다. DOREMI.png를 실제 확인했다. 흰색 헤더·넓은 사진 배너·일정 영역·하단 지표/공지 구성을 참고하되, 브랜드/광고/연락처/고정 수치는 복제하지 않는다. 원본은 수정·커밋하지 않는다. Green을 우선, Civic은 사진을 절제, Reference 구조는 보존한다. 새 사진은 원본 생성 자산이며 출처를 기록한다.

기존 발주는 PurchaseOrder.supplier(User), 거래처는 Supplier.user(OneToOne)다. 이를 재작성하지 않고 SupplierMembership을 추가한다. 가입은 소속 확인 요청만 만들며 주문 접근권한을 주지 않는다. 관리자 확인 후 Supplier에 연결하고 해당 Supplier.user의 주문만 모든 목록/상세/다운로드/API에서 조회한다. 동일 업체의 여러 계정은 membership으로 연결하며 기존 발주 FK를 변경하지 않는다. 신규 업체 생성은 관리자 검증 후 명시적으로 수행하고 중복 상호를 거부한다. 상호 문자열만으로 소속을 추정하지 않는다.

공급업체 수주 상태는 기존 발주/검수/재고 상태와 분리한다. NEW→ACKNOWLEDGED→ACCEPTED→PREPARING→DISPATCHED, 수락 전 REJECTED 가능. 접수 전 즉시 수락/거절도 가능하다. 수락 이후 기존 발주 품목/수량/금액은 고정이며, 출고 전 예정일/예정량은 수정 가능하다. DISPATCHED와 REJECTED는 최종 상태다. 예정량은 재료 기준 단위를 명시하며 실제 합격 입고량과 구별한다. 수주·출고 요청은 재고를 건드리지 않는다. 실제 합격 검수는 기존 inspect_item만 사용한다.

SYSTEM_ADMIN은 MAIN_ADMIN의 하위 호환 별칭으로 취급한다. 기존 최고관리자/legacy ADMIN과 그룹 권한은 MAIN_ADMIN으로 정규화하여 강등하지 않는다. staff 단독 계정은 승격하지 않는다. SUB_ADMIN은 일반 계정/역할/업체 연결과 업무를 관리하지만 관리자 계정/역할, 정책, 최고관리자, 전체 보안 감사는 변경하지 못한다. 사용자 확인에 따라 공급업체도 MAIN_ADMIN의 관리자 신청 승인으로 SUB_ADMIN을 겸임할 수 있다. 단순 가입/직접 role 전송으로는 내부 권한을 얻지 않는다.

기존 최고관리자를 유지하며 새 admin 계정을 만들지 않는다(사용자 확인). 비밀번호를 변경하지 않는다. 일반 계정의 관리자 신청은 로그인 상태를 바꾸지 않고, MAIN_ADMIN만 승인해 SUB_ADMIN을 추가한다. 기존 다중 역할은 보존한다. 자기 관리자 권한 변경 및 마지막 활성 MAIN_ADMIN 제거를 트랜잭션/정책 행 잠금과 revision으로 보호한다.

변경 전 Preview DB를 private SQL로 백업하고 별도 tmpfs MariaDB에 복원해 계정/migration 수를 확인했다. 새 migration도 복원 DB에서 먼저 검증한다. 운영 서비스, stable 브랜치, DB/볼륨/네트워크는 변경하지 않는다. 테스트 후 Preview 웹/메일/프록시만 교체하고 로컬 커밋한다.
