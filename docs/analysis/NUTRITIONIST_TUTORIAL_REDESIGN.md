> 2026-11-07 후속: [초보자용 재설계 및 최신 검증](NUTRITIONIST_BEGINNER_TUTORIAL.md)을 참조하세요. 아래는 이전 배포 당시 기록입니다. 신규 가이드는 로컬·격리 환경만 검증했고 Preview에 배포하지 않았습니다.

# 영양사 업무 가이드 개편

2026-11-06 KST. 시작HEAD3236e07, feature/ui-redesign-three-modes. 이 문서의 계획은 구현/검증 결과로 후속 갱신한다. 기존 change_password.sh는 보존하고 실행하지 않는다.

## 기존 기능 진입점 조사

| 기존 기능 | 기존 진입점 | 다른 기존 메뉴 | 개편 진입점/보존 방식 |
|---|---|---|---|
| 수동 예상/최종 식수 저장 및 비교표 | procurement:workflow, workflow_views.hub, workflow/hub.html | 문서 홈·대시보드도 같은 hub 링크. 독립 입력 화면 없음 | **workflow_headcounts** /workflow/headcounts/로 분리. 예전 workflow POST는 같은 서비스로 처리 |
| 저장한 발주예정서30개 조회·재검토 표시 | 같은 hub 하단 | 상세 /workflow/plans/<id>/는 있으나 독립 목록 없음 | **workflow_plans** /workflow/plans/로 분리. 상세/확정 경로 유지 |
| 발주예정서 미리보기/생성 | /workflow/preview/ | 업무 메뉴 | 기존 URL/View/서비스 유지, 가이드3단계 링크 |
| 식단/레시피 작성·업로드 | meals 기존 URL | 식단·레시피 메뉴 | 기존 기능 유지,1단계 링크 |
| AI 예측·결과·보고 | forecasting 기존 URL | 식수·소요량 메뉴 | 기존 기능 유지,2단계 링크 |
| 검수 | /workflow/inspections/ | 발주·검수 메뉴 | 기존 기능 유지,4단계 링크 |
| 입출고·수불 | /workflow/transactions/, /workflow/ledger/ | 재고·수불 메뉴 | 기존 기능 유지,5단계 링크 |
| 조리 지시 메모/Excel·인쇄 | /meals/cooking/ | 문서 메뉴 | 기존 기능 유지,5단계 링크 |
| 정산/업체 문서 | /workflow/settlement/ 등 | 문서·정산 메뉴 | 기존 기능 유지,6단계 링크 |
| 분류·업체·규격 기준정보 | 각workflow 기존URL | 권한별 기준정보/공급업체 메뉴 | 서버 권한에 맞는 링크만 안내 |

URL /procurement/workflow/ 자체는 유지한다. GET은 영양사 업무 가이드이고 기존 식수 POST는 호환 처리한다. 가이드 GET은 업무 완료 상태를 계산하거나 저장하지 않는다. 식수·발주 목록을 삭제한 것이 아니라 명시적 업무 진입점을 추가한 것이다.

## 설계 기준

6단계는 식단→AI/최종식수→소요량/발주→납품/검수→재고/조리→정산이다. 각 단계에 이유·업무·입력·결과·다음 단계와 기존 업무 화면 링크를 제공한다. 예측/수동/최종/실측, 수주/입고, 조리 메모/실제 사용을 구분한다. 취소·반복 분납·검수 정정·회계 마감 등 미구현은 후속 범위로 명시한다.

진행률은 **읽음 표시**만 뜻하며 업무 완료/발주 전송과 무관하다. 브라우저 저장은 사용자PK별 namespace로 분리하고 값을 검증한다. 비밀번호/업무값/개인정보를 저장하지 않는다. 미로그인/일반 공급업체의 내부 가이드 접근은 서버에서 제한하며 각 단계의 실제 링크도 서버 권한으로 필터링한다. JavaScript가 없어도 native details와 업무 링크로 내용을 읽을 수 있어야 한다.

## 구현 완료 결과

- `procurement/tutorial.py`: 6단계의 이유/수행업무/입력/결과/다음 단계/주의사항과 권한 필터링된 실제 업무 링크.
- `procurement/workflow_views.py`, `urls.py`: 기존 workflow GET은 가이드, POST는 원래 save_headcount 서비스로 전달. 독립 headcounts GET/POST와 saved_plans GET 추가. 식수 저장 후 저장 화면으로 이동한다.
- `templates/workflow/tutorial.html`, `headcounts.html`, `saved_plans.html`: 안내와 실제 입력/목록 분리. 원래 hub 템플릿은 삭제하지 않았고 새 route의 렌더링에는 사용하지 않는다.
- `accounts/rbac.py`: 가이드 GET은 dashboard.read, 기존 POST는 forecast.write 유지. 독립 식수 화면은 forecast.read/write 분리. 일반 공급업체는 내부 가이드에 접근하지 못한다.
- `frontend/src/guide-progress.mjs`, `guide.ts`, `main.ts`: 이전/다음·키보드 Home/End/화살표·펼침·읽음 표시·현재 단계·진행률·재시작. 정규화한 `{current,completed}`만 저장한다.
- 공통 navigation과 문서/홈 링크에 가이드·독립 식수·저장 목록을 연결했다. 비교 페이지에는 가이드와 최종 식수 화면을 각각 선택할 수 있다.
- Green/Civic/Reference 공통 내용과 기능을 유지한다. CSS는 기존 토큰/사진을 사용하며 사진이 없어도 안내/링크는 동작한다. 모바일 단계 목록은2열, 텍스트 영역은1열로 배치한다.
- 기존 JS/TS/Vite와 Django Template를 재사용했다. 신규 프레임워크/패키지·모델 필드·migration은 없다. compiled CSS/JS와 cache version을 갱신했다.

## 진행률·접근성·역할

`snp.guide.nutritionist.v1.<User PK>` namespace는 사용자/브라우저/출처별이다. 아이디·비밀번호·업무 수치·서버 완료 상태를 저장하지 않는다. username이 바뀌어도 동일 PK의 키는 유지된다. 이동만으로 읽음 완료가 되지 않으며 각 단계의 읽음 버튼을 눌러야100%가 된다. 서버에 진행률 저장 API나 업무 mutation 요청을 만들지 않았다. 잘못된 값/중복/범위 밖 값은 정규화한다.

localStorage 차단 시 현재 페이지에서만 동작한다는 안내를 표시한다. JS가 없으면 native details6개와 업무 링크를 읽을 수 있다. 현재 단계 버튼은 aria-current=step, 진행률은 progress, 상태는 polite live region이며 단계 이동 시 제목에 포커스를 둔다. 공급업체는 기존 포털, COOK/VIEWER는 허용된 읽기 링크만 제공한다. 앱 전체 접근성 인증이나 실제 영양사 인수 완료는 아니다.

## 검증과 증거

`verification/tutorial-preview-20261106/` 기준 새 실행:

| 검사 | 결과 |
|---|---|
| 새 Django 튜토리얼/승인 안내 | 16개 포함 |
| 전체 SQLite | 325개:321pass/4skip, 실패·오류0 |
| 전체 MariaDB | 325pass, 실패·오류·skip0 |
| JS | 기존10+진행률7=17pass |
| TypeScript/Vite | build 통과 |
| 기존 영양사 업무 E2E | 21검증 지점, 실제 신규 식수 진입점에서 저장/재조회·발주/검수/수불/조리 유지 |
| 공급업체·관리자 E2E | 13지점, 신규 계정 승인 전 로그인 차단→MAIN 계정 승인→별도 소속 확인 포함 |
| 가이드 E2E | 15지점, 진행/복원·키보드·역할·저장차단·JS없음·이미지실패·모바일·기능 연결 |
| 공개 HTTPS 읽기 전용 | 7지점,3모드 유지·승인 안내·보호 화면302·Secure CSRF·실제 asset 일치 |

325개는 두 DB의 같은 케이스 반복이다. 브라우저 지점 수를 Django 테스트 개수에 더하지 않는다. 공개 검증에서 실제 계정 로그인·가입 제출·발주/재고 변경은 하지 않았다. `browser-guide.json`, `business/browser-result.json`, `browser-portal.json`, `browser-public-readonly.json`이 각 결과다.

스크린샷은 `screenshots/{green,civic,reference}-guide-{desktop,mobile}.png`, 공개 익명 가입 안내 `public-*-signup.png`다. 같은 폴더의 다른 화면은 격리 합성 데이터를 사용한다. QA/XSS 시험 문구가 있는 업무 화면은 전시용 고객 마스터로 취급하지 않는다.

기존 테스트의 업무 검산/주장은 보존했다. 식수 화면을 확인하던 GET assertion/standalone browser만 새 URL로 이동했고, 기존 workflow POST 호환을 새 테스트로 검증했다. 역사적 verification 원본을 덮어쓰지 않고 이번 업무 브라우저 사본의 경로/계정명을 갱신했다.

## 배포 상태와 제한

튜토리얼과 Phase1은 승인 범위에서 Preview에 적용했다. 실제 admin은 PK1/기존 비밀번호이며 가입 신규 계정은 승인 필요다. 상세 백업·보존·배포·검증은 [Preview 배포 보고서](NUTRITIONIST_PREVIEW_DEPLOYMENT.md)를 따른다. 실제 사용자가 도움 없이 업무를 수행한 인수 검사는 아직 수행하지 않았다. 미구현 예외 업무는 [Phase2 설계](NUTRITIONIST_PHASE2_PLAN.md)에 분리했다.
