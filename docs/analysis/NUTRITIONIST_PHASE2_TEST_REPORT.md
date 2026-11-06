# SNP Phase 2-A 테스트 보고서

검증일: 2026-11-06 KST. 범위는 `NUTRITIONIST_PHASE2_IMPLEMENTATION.md` 참조. 이전325개 결과만 재사용하지 않고 수정 후 전체를 직접 실행했다.

## 환경과 격리

- Python3.12.13, Django6.0.3. 기존 dependency 이미지 `snp-ui-preview-web:tutorial-20261106`를 소스 read-only mount로 사용. 이미지 재빌드/실제 Preview 재배포 없음.
- 신규 task label `snp.task=phase2-20261106`, 네트워크 `snp-phase2-tests-20261106`.
- 전용 MariaDB10.6, Redis7 tmpfs. 앱은 새 DB `snp_auth_verification` / 테스트는 Django의 별도 `test_snp_auth_verification`. `auth-db` alias는 이 task 네트워크에서만 접근.
- credential은 Git 제외된 task 전용 env에만 저장. 기존 DB 접속 설정을 테스트에 복사하지 않음.
- 브라우저 앱은 task 전용 루프백18041, Django test server. 공개용 실행/배포가 아니다. 실제 Preview 로그인·업무 쓰기 미실시.
- Chromium headless, 합성 영양사/업체A/업체B, Playwright. 예시100kg 주문만 seed하고 회차 등록과 반복 검수는 화면에서 수행.

## 실제 결과

| 검증 | 케이스/결과 | 실행 증거 |
|---|---|---|
| Django check | 두 DB 모두 문제0 | sqlite-final.log / mariadb-final.log |
| makemigrations --check --dry-run | 두 DB 모두 No changes detected | 동일 |
| migrate / migrate --check | 두 DB 성공 | 동일 |
| SQLite 전체 | 361발견, **354통과/실패0/오류0/7skip** | `verification/phase2-20261106/sqlite-final.log` |
| MariaDB 전체 | **361통과/실패0/오류0** | `mariadb-final.log` |
| JS | **17통과/실패0** | `javascript.log` |
| 신규 기능 targeted | 31통과 | `sqlite-targeted.log` |
| Chromium | **10검증 지점 통과**, pageErrors/500없음 | `browser-results.json`, `browser-final.log` |
| 브라우저 실행 후 DB 대사 | 실납105/합격100/불합격5/재고100/미납0, 입고3건 | `browser-data-consistency.json` |
| 기존 서비스 보호 | 8컨테이너 ID/image/start/mount/port 동일 | `services-before.json`, `services-protection.json` |
| 실제 Preview schema/건수 | 신규 테이블 없음, 전후 건수 동일 | `preview-schema-readonly.json`, `preview-schema-after.json` |

325기존 + 36신규 = 361 고유 Django 케이스. 조리지시서 등 기존 테스트를 다시 더하지 않는다. SQLite/MariaDB는 동일 케이스의 별도 실행이다. SQLite skip7은 기존4 + 새 select_for_update 경합3이며, MariaDB에서는 모두 실행했다. JS 및 브라우저 지점 수를 Django 케이스에 더하지 않는다.

## 신규36개 검증 범위

`integration_tests/test_deliveries.py`:

- `RepeatedDeliveries`:31개. 60kg(55합격/5불합격)→40합격→5재납품 합격, 예약 잔량, 실납/합격0, 음수/NaN/무한대/정밀도/상한, 날짜·기한·사유, 단위 변경, 중복/충돌 재전송, 완료/재검토 제한, 단건 검수 혼용 차단, legacy 원본 및 입고 보존, 월말 합격 비례금액95000원, 목록/화면/POST/redirect, 공급업체+SUB 검사 차단, 미확인 membership·타 업체 IDOR, VIEWER쓰기 및 CSRF 차단.
- `DeliveryConcurrency`:MariaDB3개. 경쟁60kg회차 등록은1건만, 같은UUID 동시 등록은동일1건, 동시 검수는합격55kg 단1회 입고.
- `DeliveryMigrationPreservation`:2개. 기존 사용자/발주/품목/검수/입고를 가진 상태에서0012↔0013왕복 후 동일, 신기능 기록이 있으면 역migration 차단·원본 유지.

발주/재고 기준 단위 kg와 명시적 `5kg/통` 20통 표시는 구분했다. 이번 테스트는 기존 전체 규격 환산 회귀도 포함하지만, 새 회차 입력 자체는 kg만 받아 자유문자 규격에서 중량을 추정하지 않는다.

## 실행 명령

새 task 네트워크/전용 MariaDB·Redis 및 비밀 env 준비 후:

```sh
bash verification/phase2-20261106/run_tests.sh config.test_settings
bash verification/phase2-20261106/run_tests.sh config.auth_mysql_test_settings
node --test frontend/tests/*.test.mjs integration_tests/smart_order.test.cjs
# task-only MariaDB에 seed_browser.py를 1회 실행한 루프백18041 앱에서:
node verification/phase2-20261106/browser-deliveries.cjs
```

스크립트는 현재 task 이름에 고정되어 있으므로 정리 이후 재실행 시 새 격리 자원을 준비해야 한다. 실제 Preview를 대상으로 seed/run_tests 하지 않는다. 브라우저 시나리오는 초기 합성 데이터용이며 사용한 DB에서 무작정 반복하면 완료 주문 때문에 실패할 수 있다. 격리 새 DB만 사용한다.

## 초기 실패와 수정

- 첫 SQLite 실행:353중321pass/28ERROR/4skip. 신규 픽스처에 필수 `OrderItem.order_unit_price` 누락. 모델 NOT NULL 완화 없이 테스트 데이터에 명시 단가 추가. 이후 targeted31 및 전체361 성공.
- 최초 브라우저 앱: 중첩 스크립트 실행 시 `config` 모듈 경로 누락. task 컨테이너에 `PYTHONPATH=/workspace`를 주어 해결. 실제 서비스 설정 변경 없음.
- 최초 Playwright: 실제 링크는 `#번호`인데 '상세' 텍스트로 찾던 harness가 timeout. 실제 href 기반으로 수정. UI 버튼/요구사항 변경 없음. 최종10지점 성공.
- 보호 비교: Docker mounts 배열 순서가 달라 첫 단순 배열비교 실패. Destination 기준 정렬 후 모든 속성이 동일함을 확인. 서비스 변경은 없었음.

실패 로그도 evidence 디렉터리에 보존. 성공을 만들기 위해 업무 수량 기대값을 낮추거나 테스트를 무시하지 않았다.

## 브라우저와 화면 증거

공급업체 로그인/납품등록·재조회3회, 영양사 로그인/검수·재조회3회, 최종합계·완료/포장량, 3모드 저장/재조회·모바일, 타 업체404/구매자 경로403, 주간 수불 진입의10지점. 각 회차별 실제 입력·저장·재조회가 포함된다.

`verification/phase2-20261106/screenshots/`:
- `{green,civic,reference}-buyer-desktop.png`
- `{green,civic,reference}-supplier-desktop.png`
- `{green,civic,reference}-buyer-mobile.png`

데스크톱1920×1080, 모바일390×844. 실제 계정·운영 주문은 사용하지 않음. Green 화면을 직접 확인했고 나머지는 동일 시나리오 스크린샷/브라우저 assertion 근거다. 200%확대·전체 접근성·모바일 공급업체 입력 수용 테스트는 미실시.

## 한계

실제 현업 인수, 부하/장시간 경합, 전체 침투 테스트, 실제 부분 납품 이력의 운영 DB 변환, SMTP 발송은 검증하지 않았다. 발주 취소/정정/입고 후 반품/문서 발행 버전은 미구현이므로 해당 성공 주장 없음. 이번 신규 회차별 Excel/PDF 출력은 추가하지 않았고 기존 출력 회귀만 실행했다. AI 모델/입력/API는 수정하지 않았으며 이번에 새로운 AI 실험을 하지 않았다.
