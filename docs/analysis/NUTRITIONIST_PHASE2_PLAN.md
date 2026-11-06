# SNP Phase 2 구현 설계안

2026-11-06 KST. UI 브랜치. **설계 문서이며 아래 신규 모델/API/상태는 아직 구현·migration·운영 적용하지 않았다.** Phase 1+튜토리얼의 기존 업무 경로를 기준으로 additive 변경을 준비한다. 영양/알레르기·회계·다기관 기준을 임의로 확정하지 않는다.

## 1. 현재 구현과 원칙

- PurchaseOrder는 legacy status 대기/승인/완료, needs_review, ProcurementPlan snapshot·fingerprint를 가진다. 취소/대체 발주·입고 후 정정은 완결되지 않았다.
- SupplierFulfillment/DeliveryLine은 발주별 하나의 수주 상태/예정량을 기록한다. 계정 승인과 업체 소속 확인은 별도이며 canonical 발주처 FK를 보존한다.
- GoodsInspection은 OrderItem과 OneToOne, InventoryLog도 일대일이다. 한 차수 합격량 입고/중복 방지는 되지만 반복 검수·정정 이력은 없다.
- inspect_item은 **사유가 있는 발주 초과 납품**도 허용한다. 공급업체 예정량의 상한과 구매자가 확인한 실제 합격량은 다른 규칙이다. 보고 서비스에서 새 상한을 강제하지 않는 회귀 테스트를 유지한다.
- 조리지시서 메모 revision은 현재 레시피로 재계산하며 불변 발행본이 아니다. 식수·레시피 변경 시 과거 발행 수치 보존이 부족하다.
- AttendancePrediction에는 생성 시각·모델·입력 feature가 있으나 현재 메뉴는 CSV fallback 경로다. MealForecast.actual_count 필드는 있지만 실측 입력/수정 책임 UI는 없다.

공통 요구는 Decimal/명시 단위, 원자적 트랜잭션, parent 행 잠금, expected revision, unique request key, 원본·정정 관계, 서버의 업체별 queryset이다. GET에 발주·입고·문서 발행 같은 부작용을 넣지 않는다. 새 상태를 표시한다고 실제 업무가 끝났다고 판단하지 않는다.

## 2. 발주 취소·정정·재발주

| 항목 | 제안 |
|---|---|
| 모델 | OrderChangeRequest(order FK, requested_by, reason, kind, revision, status, reviewed_by/at); OrderRevision 또는 불변 snapshot; replacement_order/source_order 참조; 기존 status와 별도의 lifecycle 필드 검토 |
| API/화면 | 기존 계획/주문 상세에 변경 영향·재검토 원인·요청 이력. POST 변경 요청→권한 있는 검토→적용/거절, replacement 링크. 기존 create/confirm 엔드포인트는 유지 |
| 상태 | 초안/확정 미입고/수주 응답/부분 입고/완료를 구분. 수주 거절은 자동 구매 취소가 아님. 취소 상태만 바꾸고 재고를 역차감하지 않음 |
| 호환 | 대기/승인/완료 및 기존 배송완료 해석을 adapter에 보존. 과거 supplier 응답을 만들어내지 않음. 원본 주문/단가/업체/검수 참조를 삭제하지 않음 |
| migration/rollback | nullable 관계·추가 이력 테이블 우선. legacy 기원과 확정 가능 정보만 표기. 신기능 사용 후 구버전 무조건 downgrade/drop 금지; feature 제한·읽기 adapter·사본 복구 계획 |
| 권한/책임 | 초안은 기존 작성자/관리자 제약 유지. 영양사 또는 허용 운영자가 변경 요청. 확정/수주 이후 취소 승인자·독립 승인 필요 여부는 현업 확인. 업체는 수락/거절/변경 회신만, 구매자 주문 삭제 불가 |
| 테스트 | 식단 변경→재검토→새 계획, 거절→대체 업체, 미입고 취소, 중복 요청/동시 확정, 이미 검수된 주문 취소 거부/정정 안내, 원본과 대체 주문 합계/재고 중복 없음 |

현업 질문: 취소 마감, 업체 통지와 승낙 필요 여부, 긴급 전화 수정의 사후 승인, 공급업체 겸 SUB의 자기 거래 승인 제한, 미납 종결 책임자.

## 3. 반복 분할 납품

| 항목 | 제안 |
|---|---|
| 모델 | DeliveryBatch(order FK, canonical supplier, sequence, expected_date, state, revision, request_key); DeliveryBatchLine(batch FK, order_item FK, planned_quantity/base_unit); 차수별 구매자 검사 별도 연결 |
| API/화면 | 업체 주문 상세에 차수 목록·약속 수량/일정·출고·잔량. 자기 업체 queryset으로 list/detail/JSON/export/POST 필터. 구매자 검수 화면도 주문→차수→품목으로 선택 |
| 수량 | 발주량·차수 약속량·실납·합격·누적 순입고·미납 종결량을 각각 표시. 필요/포장/재고 기본 단위 분리. 남은 납품 대상은 정의된 순입고/종결 기준으로 계산하고 초과량은 별도 표시 |
| 기존 데이터 | 기존 Fulfillment/DeliveryLine을 legacy 차수로 대응하되 없던 접수/출고 사실을 만들지 않음. canonical owner·직원 membership 연결을 유지 |
| migration/rollback | legacy ID→batch ID 대응표와 count/수량 대사. 기존 합격 IN 로그를 참조해 **재입고하지 않음**. 새 차수 생성 이후 단순 역migration으로 기록을 지우지 않음 |
| 권한 | 업체는 자기 차수의 약속/출고만 관리. 구매자가 실납/합격을 확정. 확인되지 않은 membership·다른 회사 ID·직원 계정 발주처 위조는 거부 |
| 테스트 | 10kg→6+4, 동시 두 차수, 같은 request 중복, 일부0/불합격/초과 납품 사유, 공급업체 A/B IDOR 모든 출력/API, 상태 경합/날짜·단위 오류 |

현업 확인: 예정량 누적 상한/변경 허용 시점, 초과 납품 승인, 차수 배송완료와 구매자 검수완료 구분, 잔량 자동/수동 종결, 휴무·지연 통지.

## 4. 검수 정정

| 항목 | 제안 |
|---|---|
| 모델 | 차수별 InspectionReceipt, InspectionRevision(원본 FK, 전후 수량, 사유, 작업자/승인자/시각, revision/request key). 원본 검수·입고 로그는 불변 이력으로 유지 |
| API/화면 | 기존 GoodsInspection 읽기 adapter와 새 차수 검사 화면 공존. 차이·lot/정산 영향 미리보기→권한 검토→정정 확정. 단순 form resubmit과 정정 요청은 구분 |
| 재고 | 증가/감소 보정에 대응하는 명시적 거래와 할당 기록. 이미 조리 사용된 lot를 음수로 만들지 않음. 실제 보유량보다 큰 역보정은 별도 실사/승인 없이 실행하지 않음 |
| 호환 | OneToOne GoodsInspection을 즉시 삭제/다중 FK로 바꾸지 않음. legacy 단건·새 유효 누적량의 의미를 adapter에서 분리해 기존 문서가 중복 집계하지 않도록 함 |
| migration/rollback | 기존 검사/InventoryLog 링크1건을 legacy receipt로 매핑, 수량/기말 불변 대사. 실제 정정 기록 생성 후 이력 삭제 rollback 대신 기능 정지/보정/사본 복구 절차 |
| 권한 | inspection.write가 있는 구매자 담당자. 공급업체·공급업체 겸 SUB의 합격량/재고 쓰기 금지 유지. 승인자/정정 한도·기간 마감 이후 권한은 현업 확정 |
| 테스트 | 오입력 증가/감소, 일부 사용 후 감소 거부, 유통기한 수정, 동시 정정409, 중복 요청, 원본 조회·정정 이력·수불/정산 대사 |

미정 사항: 온도/품질 증빙, 재검수 서명, 기한/로트 정보 정정 방식, 검사 불합격의 회계 반영·책임.

## 5. 반품·재배송

| 항목 | 제안 |
|---|---|
| 모델 | ReturnRequest/ReturnLine(원래 receipt/lot, 수량·사유, 상태·승인자), ReplacementDelivery 참조. 반품과 현장 폐기는 별도 원인 |
| API/화면 | 구매자 반품 요청→업체 회신/구매자 승인→물리 반출 확인→재배송 차수. 업체는 구매자의 재고/합격량을 직접 확정하지 못함 |
| 재고·금액 | 실제 반출 시에만 순재고 감소. 기존 OUT/lot allocation과 연결하는 방향으로 수불 호환을 우선 검토. 새로운 로그 유형을 추가한다면 모든 집계 경로를 함께 변경해야 함. 환입/공제/교환 정산 기준은 미정 |
| 호환/migration | 기존 condition='반품' 검수는 당시 합격0인 단건 결과이며 실제 사후 반출로 추정하지 않음. 이관 시 새 거래를 생성해 재고를 차감하지 않음 |
| rollback | 반출/재배송 원본 보존·명시적 보정. 실제 소진 재고를 되살리거나 기존 로그를 삭제해 rollback하지 않음 |
| 권한/테스트 | 구매자 재고 담당 확정, 업체 회신만 허용. 이미 소진된 lot·중복 반품·부분 재배송·기한 오류·차수/업체 IDOR·정산 대사 테스트 |

현업 확인: 교환/환불 선택, 물리 반출 시점·확인자, 유통기한 지난 반품, 비용과 세금계산서 정정 책임.

## 6. 발행 조리지시서 이력

| 항목 | 제안 |
|---|---|
| 모델 | CookingInstructionIssue(plan FK, issue_no/revision, immutable payload, template_version, issued_by/at, source fingerprint, previous_issue FK, reason). 배합·식수·단위·명시 규격·메모·표시값 snapshot |
| API/화면 | 기존 /meals/cooking/<pk>/는 최신 초안. 별도 POST 발행/재발행과 GET 발행본 조회/Excel/인쇄. 작성 중/확정/발행/변경 요청/재발행/사용 완료를 명시적으로 표시 |
| 기존 데이터 | 현재 CookingInstruction 메모/revision과 Recipe는 유지. 발행 기록이 없던 문서를 과거 발행본으로 소급 확정하지 않음. 이관 시점 초안과 실제 과거 증빙을 구분 |
| migration/rollback | 발행 테이블 추가·발행 번호 유일성. 최초 기존 문서 이관은 상태/출처 명시. 과거 발행물 삭제/덮어쓰기 없이 기능 제한/구버전 읽기 adapter 제공 |
| 권한/책임 | 영양사 또는 지정 발행자, COOK는 허용된 지시 메모/조회. 변경 요청/재발행 승인 책임·현장 전달/회수 방식은 확정 필요. GET 인쇄가 자동 발행 처리하지 않음 |
| 테스트 | 발행→레시피/최종 식수 변경→과거 재조회/Excel 수치 동일, 현재 초안 재계산 분리, 동시 발행/중복 요청, 식수0/미확정·규격 누락, 장문·인쇄 페이지, 재고 자동 차감 없음 |

사용 완료 메뉴 편집을 다시 허용하려면 먼저 레시피 revision/새 메뉴 분기와 과거 발행본 보호를 구현해야 한다. 안전한 snapshot 없이 Phase 1의 완료 보호를 해제하지 않는다.

## 7. 실제 식수 입력과 AI 연계

| 항목 | 제안 |
|---|---|
| 모델 | ActualAttendanceRevision(plan FK, observed_count>=0, observed_at, entered_by, corrected_from/revision, reason/승인 정보). MealForecast.actual_count는 호환 읽기 값으로 유지하고 새 명시적 입력 때만 동기화 |
| API/화면 | 실제 인원 입력·저장/수정 이력·근거 시각. AI 예측/수동 예상/최종 확정/실측을 각각 표시. 실측이 없으면 미입력·오차 산출 불가,0명도 별도 값 |
| AI 입력 | 현재 DB 날짜·끼니의 메뉴 문자열을 기존 학습 전처리/군집/임베딩 계약과 golden-input으로 비교한 후 연결. 입력 출처DB/CSV fallback·결측·모델 식별/입력 snapshot·생성 시각 표시 |
| 재예측 | PredictionRequest(date,meal,input_fingerprint,model_version,request_key) 등의 실행 이력/유일성으로 중복 방지. 기존 AttendancePrediction 이력을 삭제하지 않고 최신 선택/active 참조를 명확히 함. 새 예측이 최종 식수를 자동 변경하지 않음 |
| 호환/migration | 과거 actual_count에 입력자/시각이 없으면 legacy provenance로 표시하고 임의 담당자/과거 시각을 만들어내지 않음. manual/final 값을 실측으로 채우지 않음. 예측 중복 레코드 정리도 삭제 대신 호환 참조 검토 |
| rollback | 새 관측/예측 이력 보존, 기능 제한/호환 필드 읽기. 새 학습 모델 교체·재학습은 별도 승인. 기존 모델/파일·의존성 유지 |
| 권한/테스트 | 식수 책임자/영양사 입력·수정 승인, 업체/조회 사용자 쓰기 금지. None/0/양수/음수·소수·과대값·중복/동시 수정, 보고 HTML/JSON/Excel 동일, fallback/모델 로드·입력 shape·재예측 후 최종 식수 보존 검증 |

현업 확인: 실측은 예약/배식/식권/실제 섭취 중 무엇인가, 입력 마감·추가 조리, 오류 수정 책임자. 현재의 signed 예측 오차와 절대오차를 구분하고 실측0의 비율 오차 정의를 합의한다. 정확도는 실제 현장 관측으로 별도 검증한다.

## 8. 구현 순서·승인 게이트

1. 현업 상태/정정/반품·미납 종결·실측 정의 합의와 권한 매트릭스.
2. additive 차수 모델 + 기존 데이터 사본 mapping/dry-run·합계/FK 대사. 실제 migration 전 백업 복원/구버전 읽기·rollback 검증.
3. 정상 6+4 분납→검수→lot→수불 경로, SQLite/MariaDB/IDOR/E2E.
4. 취소/대체·정정/반품 보정, 이미 사용된 재고·마감 월 예외.
5. 불변 문서 발행·재발행과 레시피 변경 영향.
6. 실제 식수 UI·수정 감사와 기존 모델 입력 계약 검증/연계.
7. 영양사·업체 인수와 운영 성능/복구 확인 후 Preview 배포를 별도 승인.

모든 단계는 실패 재현→최소 구현→도메인/전체 회귀→브라우저·사본 이관 검증→문서 순서로 진행한다. 이번 작업에서는 위 스키마/API를 적용하거나 기존 검사/재고를 변환하지 않았다.
