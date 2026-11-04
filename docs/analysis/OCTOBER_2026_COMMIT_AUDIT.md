# 2026년 10월 작성 커밋 전수 조사 및 추가 통합 판정

조사일: 2026-11-04(KST). 저장소: `Jinnuu/temp_capstone`.

## 결론

원격37개 브랜치의 도달 가능한 고유 커밋105개 전체를 조사했다. **작성일(AuthorDate)을 KST로 환산했을 때 2026-10-01 00:00:00 이상, 2026-11-01 00:00:00 미만인 커밋은5개이며 모두 현재 HEAD의 조상이다.** 추가로 적용할 독립 커밋은0개다. 직전 통합에서 보류한 오래된/퇴행 위험 로직은 재검토 후 그대로 보류했다. **새 코드·테스트·모델·migration 수정, cherry-pick·병합은 하지 않았다. 이 보고서1개만 생성했다.**

## 1. 시작 상태와 조사 범위

- 경로 `/home/woohyeak/sprint7-integration`.
- 브랜치 `integration/sprint-final-kanghoon2-20261104`.
- HEAD `42f1fe5639db230c129d151f392b439b7740226d`, 부모 `1aa6302`와 `4cb648f`. 작업 시작 시 Git 작업 트리는 깨끗했다.
- 기존 강훈2차 통합을 유지했다. `sprint-final`/백업 브랜치 및 원본 checkout은 변경하지 않았다.
- `git fetch origin`을 실행했고, `git ls-remote --heads origin`의37개 실제 원격 head를 각각 로컬 원격 추적 ref와 대조했다. 모두 일치했다. 저장소는 shallow가 아니다.
- 브랜치 tip의 날짜로 후보를 줄이지 않았다. 모든 head SHA를 `git rev-list`에 전달해 전체 이력을 합집합으로 순회했다. 커밋 날짜가 비순차적일 가능성을 고려해 이 단계에서 --since/--until 가지치기를 하지 않았다.
- 각 커밋의 `%aI`(AuthorDate)와 `%cI`(CommitDate)를 모두 읽어 Asia/Seoul로 환산했다. 주 판정은 사용자 요청의 ‘작성된’에 맞춰 AuthorDate다. AuthorDate는10월 밖인데 CommitDate만10월인 추가 커밋도0개다. 이번5개는 두 날짜가 모두 동일하다.
- Git 날짜는 기록된 메타데이터이며 실제 최초 개발일을 독립적으로 증명하지 않는다. 공개 원격이 현재 제공하는 브랜치에서 도달할 수 없는 삭제/비공개 이력은 범위 밖이다.

## 2. 10월 커밋별 판정

| 커밋 | AuthorDate(KST) | CommitDate(KST) | 도달 가능한 현재 원격 브랜치 | 변경/제외 사유 | 이번 추가 적용 |
|---|---|---|---|---|---|
| `eac48a0` | 10-15 22:18:49 | 10-15 22:18:49 | `sprint-final` | 기존 대시보드·간편발주4파일 보존. 42f1fe5의 첫 부모 계통에 이미 포함. 최초 개발일이10월이라는 뜻은 아님. | 없음: 이미 이력 포함 |
| `e21478b` | 10-15 22:32:54 | 10-15 22:32:54 | `sprint-final` | 기존 Sprint7/강훈1차 통합과 회귀 기반. 첫 부모 계통에 포함. 재병합 불필요. | 없음: 이미 이력 포함 |
| `ab5ed57` | 10-15 22:40:41 | 10-15 22:40:41 | `sprint-final` | 요구사항/구현 계획 문서. 이미 포함됐으며 신규 실행 기능 커밋이 아님. | 없음: 이미 이력 포함 |
| `a8d9fae` | 10-15 23:19:26 | 10-15 23:19:26 | `sprint-final` | 확정 식수·명시 규격·검수 합격량·FIFO/원장·권한·문서 workflow. 이미 포함, 기존139개 회귀 대상. | 없음: 이미 이력 포함 |
| `27f0edc` | 10-28 20:42:48 | 10-28 20:42:48 | `feat/kanghoon/comprehensive-improvement2` | 공급업체/품목 수정·기간 문서·월간 양식/UI. 4cb648f의 부모이며 42f1fe5에서 안전하게 선별 반영. 보류 로직은 아래 별도 판정. | 없음: 이미 이력 포함 |

커밋 메시지 원문:

- `eac48a0752252f3775764a2c70e6c3281e2edd6d`: Preserve Sprint 7 uncommitted dashboard and procurement changes
- `e21478b157aae5d50e0878b83139ff551d8122bb`: Merge Kanghoon improvements with preserved Sprint 7 workflows and isolated verification
- `ab5ed5743f440b2144511799ffb069d04a0223d2`: Document requirement baseline and implementation plan before code changes
- `a8d9faecef04da2368543984fe304d157b25dd16`: Add document-traced SNP workflows with confirmed counts and inspected receipts
- `27f0edc8e7361ac5b20b0f607e4bf51774d7acfe`: feat: 공급업체 관리, 문서 양식(조리시방서/월간정산서) 추가 및 전반적 기능·UI 개선

`git merge-base --is-ancestor <각 SHA> HEAD`가5개 모두 exit0이었다. 따라서 동일 커밋을 다시 cherry-pick하거나 patch-id로 중복 적용할 이유가 없다. **조상이라는 사실과 원본 diff 전부를 그대로 채택했다는 주장은 다르다.** 특히27f0edc는16파일 충돌을 해결하는 과정에서 기존 기능을 보존하도록 선별 반영됐으므로 아래 기능/코드도 확인했다.

## 3. 27f0edc의 기능 단위 재검토

이 커밋의 직접 부모는3b01dc8이다. `git show --stat 27f0edc`는32파일/2,782줄 추가/593줄 삭제다. 브랜치 최신 커밋4cb648f(11월2일)를 이 커밋과 혼동하지 않았다.

| 10월 원본 변경 | 현재 코드 근거 | 판정/추가 적용하지 않은 이유 |
|---|---|---|
| Supplier 연락처 관리 및 화면 | `procurement/models.py:Supplier`, `supplier_views.py`, `templates/procurement/supplier_list.html` | 이미 반영. 기존 User/FK를 보존하고 계정 명시 연결·관리자 변경·이력 보존으로 보강됨 |
| 식재료 수정 URL/View/화면 | `inventory/views.py:ingredient_update`, urls.py, ingredient_form/list.html | 이미 반영. PK·재고 유지, 연결 단위 변경/음수 차단·발주 재검토 포함 |
| 월간 정산 양식 | `procurement/team_document_views.py:monthly_settlement_view`, `templates/docs/doc_monthly_settlement.html` | 이미 반영. 날짜 우선순위·단위별 수량·0원·빈 달 검증 포함. 기존 합격량 정산과 별개 발주 참고 문서 |
| 조리지시서 기간 양식 | `team_document_views.py:doc_cooking_instruction`, `meals/cooking.py:cooking_sheet`, `templates/docs/doc_cooking_instruction.html` | 이미 반영. 기존 확정 식수·저장 비고·수정/Excel 연결 사용 |
| 수불 기간 조회·품목 필터 | `inventory/views_new_docs.py:doc_inventory_status`, `templates/docs/doc_inventory_status.html` | 이미 반영. 월 쿼리 호환, 기초잔량 보존. activity_only=1은 선택 필터 |
| 문서/식단 가독성·메뉴 | `templates/docs/`, `templates/meals/mealplan_create.html`, `templates/partials/top_nav.html`, `static/css/sp_final.css` | 호환되는 변경은 이미 반영. 기존 분류 묶음·업체별 스냅샷·문서 진입점 유지 |
| 자유문자 규격·기본 통/봉 추정, mL≈g | 원본 `procurement/utils.py` vs 현재 동명 파일 및 `procurement/workflow.py:convert/build_preview` | 계속 제외. 명시적 SupplySpecification만 환산하며 단위/안전재고/발주 올림 기존 규칙을 유지해야 함 |
| 미확정/0명에500명 대입 및 수량 크기로g/kg 추정 | 원본 `procurement/views_new_docs.py` vs 현재 cooking_sheet/convert | 계속 제외. 확정 식수 구분·0명·명시 단위와 충돌. 날짜가10월이어도 안전하지 않음 |
| 발주 없을 때 식단에서 구입요구서/검수 품목을 추정하는 fallback | 원본 `procurement/views_new_docs.py`의 fallback vs 현재 기존 문서/업무 preview | 그대로 재적용하지 않음.500명 기본값/추정 단위/확정되지 않은 식단에 의존하는 경로와 결합됨. 기존 발주예정서 preview가 별도로 존재하지만 모든 문서의 fallback과 동등하다고 주장하지 않음 |
| 조회 시 샘플 업체 자동 생성·이름으로 기존 계정 추정 연결 | 원본 supplier_list/create vs 현재 supplier_views.py | 계속 제외. 조회에 DB 쓰기 금지, 잘못된 역할/계정 연결 위험. 관리자가 명시 연결하도록 이미 대체 |
| 빈 달 샘플 행·금액 표시 및 세율10% 일괄 적용 | 원본 monthly_settlement_view/템플릿 vs 현재 team_document_views.py/템플릿 | 계속 제외. 데이터 없는 숫자 표시와 세금 임의 확정 위험. 실제0·빈 결과와 세금 확인 필요 표시로 대체 |
| 주간 다음 월요일 편집/검색을 제거하는 화면 교체 | 기존 `templates/meals/weekly_mealplan_create.html` 및 기존 회귀 테스트 | 계속 제외. 기존 기능 퇴행이 실행 시험에서 확인됐으며 보존하기로 결정한 변경 |
| 카테고리 정정·업무 seed 관리 명령 | `inventory/management/commands/fix_ingredient_categories.py`, `procurement/management/commands/seed_workflow_test.py` | 파일은 기존 통합에 포함됨. 명령은 이번에도 실행하지 않음. 실제 데이터 수정이 필요하면 별도 대사/승인 범위 |

현재 구현과 기존 통합 결정은 `docs/analysis/KANGHOON2_MERGE_REPORT.md` 및 회귀 코드로 대조했다. 이 표에서 아직 보류 중인 부분은 ‘동등 기능 전체 반영 완료’로 처리하지 않는다. 안전성·정책 확인 없이 이번 기간 조건만을 이유로 되살리지 않는다.

## 4. 날짜 범위 밖의 기존 변경 보존

| 커밋 | AuthorDate(KST) | 처리 |
|---|---|---|
| 3b01dc8 | 2026-09-08 18:13:38 | 10월 추가 후보 아님. 이미 반영된 기존 기능은 유지 |
| 4cb648f | 2026-11-02 15:49:21 | 이번 신규 후보 아님. 앞선 통합에서 반영/보류한 결정을 유지하며 되돌리지 않음 |
| 1aa6302 | 2026-11-04 17:43:57 | 이번 신규 후보 아님. mid-presentation이라는 제목만으로10월 커밋으로 취급하지 않음 |
| 42f1fe5 | 2026-11-04 22:02:41 | 유지할 현재 통합 커밋. 이번에 새 병합하지 않음 |

## 5. 원격 전수 조사 표

아래 tip 날짜는 참고 정보일 뿐 후보 판정은 각 브랜치의 **모든 도달 가능한 이력**을 사용했다. 각 브랜치 이력의 커밋 수는 서로 중복되므로 합산하지 않는다. 합집합은105개다.

| 실제 원격 브랜치 | 현재 tip | tip 작성일(KST) | 전체 이력 커밋 수 | 이력에 포함된10월 커밋 |
|---|---|---|---:|---|
| `develop` | `97a64dc` | 2026-03-24 | 12 | 없음 |
| `feat/Kanghoon-procurement` | `c16cdb3` | 2026-04-04 | 24 | 없음 |
| `feat/Kanghoon-procurement-system-upgrade-modify` | `950d72c` | 2026-04-13 | 39 | 없음 |
| `feat/Myoung-ingredient-calc` | `887b992` | 2026-03-28 | 21 | 없음 |
| `feat/Myoung/procurementfunc` | `20012c1` | 2026-05-05 | 49 | 없음 |
| `feat/Myoung/recipe-file` | `fddcee2` | 2026-05-20 | 57 | 없음 |
| `feat/deficiency_calc` | `5426da9` | 2026-03-28 | 22 | 없음 |
| `feat/forecasting-ui-ux` | `3032e49` | 2026-04-01 | 24 | 없음 |
| `feat/ingredient-regi-combobox` | `0b8cd7f` | 2026-04-01 | 25 | 없음 |
| `feat/ingredient-regi-file` | `a45b370` | 2026-04-03 | 24 | 없음 |
| `feat/kanghoon/comprehensive-improvement` | `3b01dc8` | 2026-09-08 | 65 | 없음 |
| `feat/kanghoon/comprehensive-improvement2` | `4cb648f` | 2026-11-02 | 67 | 27f0edc |
| `feat/kanghoon/recipe_list` | `059bde2` | 2026-05-03 | 48 | 없음 |
| `feat/meal-and-order-management` | `aeda043` | 2026-05-07 | 49 | 없음 |
| `feat/procurement-system-upgrades` | `37dfb99` | 2026-04-12 | 38 | 없음 |
| `feat/sprint4-new-design` | `5e16ac2` | 2026-04-06 | 35 | 없음 |
| `feat/sprint7-ux-inventory-flow` | `2bd8d0e` | 2026-06-01 | 82 | 없음 |
| `feat/sprint7-xlsxupload` | `f5de5a3` | 2026-05-30 | 69 | 없음 |
| `feat/ui-system-redesign` | `f924836` | 2026-04-05 | 36 | 없음 |
| `feature/sprint7_docs-completion` | `c924612` | 2026-05-28 | 64 | 없음 |
| `fix/inventory-UI` | `6843b16` | 2026-04-11 | 41 | 없음 |
| `kanghun` | `a73d31d` | 2026-03-19 | 9 | 없음 |
| `main` | `a44ff00` | 2026-03-20 | 4 | 없음 |
| `prototype` | `32921eb` | 2026-03-25 | 18 | 없음 |
| `sprint-final` | `1aa6302` | 2026-11-04 | 94 | eac48a0, e21478b, ab5ed57, a8d9fae |
| `sprint2` | `32921eb` | 2026-03-25 | 18 | 없음 |
| `sprint3` | `8219e38` | 2026-03-29 | 23 | 없음 |
| `sprint4` | `899033e` | 2026-04-08 | 40 | 없음 |
| `sprint4-for-merge` | `da4e770` | 2026-04-05 | 37 | 없음 |
| `sprint5` | `ae97f6a` | 2026-04-13 | 45 | 없음 |
| `sprint6` | `ed5aade` | 2026-05-19 | 56 | 없음 |
| `sprint7` | `a8f5adb` | 2026-06-05 | 88 | 없음 |
| `temp/sprint6-docker` | `f9efb3e` | 2026-05-25 | 57 | 없음 |
| `temp/sprint7-docker` | `2517c95` | 2026-05-31 | 69 | 없음 |
| `temp/sprint7-integration` | `bc02965` | 2026-05-18 | 55 | 없음 |
| `temp/sprint7-integration-temp` | `c72e99a` | 2026-06-01 | 81 | 없음 |
| `temp/sprint7-ui-v1` | `650935a` | 2026-05-26 | 66 | 없음 |

## 6. 검증 상태와 보존 범위

코드·테스트·migration을 변경하지 않았으므로 불필요한 Docker/DB 재생성을 하지 않았다. 다음은 **직전42f1fe5 통합 때 실행한 기존 증거를 이번에 재대조한 결과**다. 이번 신규 실행 성공으로 표시하지 않는다.

| 항목 | 기존 결과 | 근거 |
|---|---|---|
| SQLite 전체 |139/139 통과, 실패0·skip0 | `verification/kanghoon2-20261104/sqlite-final.log` |
| 격리 MariaDB 전체 |동일139/139 통과, 실패0·skip0 | `verification/kanghoon2-20261104/mariadb-final.log` |
| Django check | 두 환경 모두0 issues | 위 두 로그 |
| makemigrations --check --dry-run | 두 환경 모두No changes detected | 위 두 로그 |
| migrate / migrate --check | 적용/적용 완료 검사 통과 | 위 두 로그 |
| JavaScript |4/4 통과 | `verification/kanghoon2-20261104/javascript.log` |
| Chromium |3개 시나리오 passed=true, pageErrors=[] | 동 폴더 `cooking/browser.json`, `workflow/browser.json`, `browser-team2.json` |
| 자원 정리 | 앞선 작업의 임시 자원 정리 기록 있음 | 동 폴더 `cleanup.json` |

Django139개는 같은 케이스를 두 DB에서 실행한 것이며278개 독립 케이스가 아니다. 기존117개+신규22개 상태를 유지했다. 이번에는 테스트 케이스를 추가/삭제/수정하지 않았다. 현재 추적 파일은42f1fe5와 차이가 없으며 새 파일은 이 보고서뿐이다. 기존 증거 파일도 변경하지 않았다.

실제 사용자 인수·온라인 전체 AI 경로·동시 부하·세금/청구 확정·과거 lot 대사 등 앞선 보고서의 제한은 그대로 남는다. 새로운 미통합10월 커밋 때문에 필요한 후속 개발은 없다.

## 7. 재현 방법

```bash
git fetch origin
git ls-remote --heads origin
git rev-parse --is-shallow-repository
git rev-list <ls-remote에서 확인한 모든 head SHA>
git show -s --format='%H %aI %cI %s' <각 SHA>
git merge-base --is-ancestor <10월 후보 SHA> 42f1fe5
git show --stat 27f0edc
git show 27f0edc -- procurement/views.py procurement/views_new_docs.py procurement/utils.py
git diff 27f0edc 42f1fe5 -- procurement inventory meals templates
git status --short
```

날짜 판정은 Python datetime.fromisoformat + ZoneInfo('Asia/Seoul')로 전체 SHA를 필터했다. AuthorDate 기준의 정확성을 위해 git log의 CommitDate 기반 날짜 필터에만 의존하지 않았다. 위 diff는 오래된 분기와 현재 통합본 차이이므로 삭제/추가를 모두 신규 작업으로 해석하지 않고 커밋 직접 부모 diff·실제 코드·이전 충돌 보고서를 함께 읽었다.

## 8. 이번 작업 결과

- 조사: 원격37브랜치 / 고유105커밋 / 작성일10월5커밋.
- 이미 현재 이력 포함:5. 이력 밖10월 후보:0. 새로 추가 적용:0.
- 보류했던 위험 로직:기존 결정 유지. 기능 전체를 무조건 완료 처리하지 않음.
- 새 코드/테스트/DB/migration 변경:0. 새 병합/cherry-pick:0.
- 보고서만 신규 생성. 원본 checkout·실행 서비스·DB·볼륨·AI 모델·원격 push/PR/배포 작업 없음.
