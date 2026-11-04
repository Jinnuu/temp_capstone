# UI 기술 선택과 구조

## 선택: Django SSR + TypeScript + Vite

인증·세션·CSRF·URL·ORM·업무 계산은 기존 Django가 계속 담당한다. 브라우저는 기존 HTML 폼을 제출한다. TypeScript는 모드 선택, 내비게이션, 표 가로 스크롤과 비교 화면만 제어한다. React용 신규 API나 인증 체계를 만들지 않았다.

| 후보 | 판단과 트레이드오프 |
|---|---|
| React | 복잡한 대화형 편집에 장점. 이번 전체 전환은 기존 폼·템플릿 JS를 중복 구현할 위험과 API 추가 비용이 커서 보류 |
| TypeScript + Vite | 선택. 작은 독립 모듈, 타입 검사, 번들 생성. Django는 결과 정적 파일만 제공 |
| Tailwind / shadcn/ui | 기존 CSS 클래스와 React 컴포넌트로 다시 작성할 비용이 커서 도입하지 않음 |
| TanStack Table | 기존 서버 검색·페이지 처리 및 표 안 폼을 교체하지 않도록 미도입 |
| Alpine / HTMX | 이번 모드 전환은 네트워크 요청 없이 구현 가능. 기존 페이지 JS와 중복 상태 계층을 추가하지 않음 |
| Chart.js | 새 통계 기능을 암시하지 않도록 미도입. 기존 표시 유지 |
| Bootstrap | 기존 5.3.3을 유지하되 CDN 대신 로컬 번들. JS는 기존 알림 닫기에 필요한 Alert만 포함 |

Vite 8.3.5, TypeScript 7.0.2, Bootstrap 5.3.3을 lockfile에 고정한다. 빌드 환경 Node 22.22.2. Vite의 Node 요구조건은 ^20.19 또는 >=22.12다. npm 의존성은 `frontend/`에만 설치한다.

## 파일과 책임

- `templates/base.html`: 공통 헤더·모드·로그아웃·검색·본문. 기존 template block과 `.sp-main` 유지.
- `templates/partials/top_nav.html`: 실제 업무 URL을 기능군으로 구성.
- `frontend/src/ui.css`: 토큰 + 세 레이아웃 + 반응형/인쇄.
- `frontend/src/main.ts`: DOM을 교체하지 않는 전환, 접근성, 미리보기.
- `static/ui/boot.js`: 첫 페인트 전에 저장 모드 적용. 저장소 접근 불가 시 기본 레퍼런스형.
- `frontend/src/brand.ts`: 사용자 확인에 따른 그린 팔레트.
- `static/ui/build/`: 커밋하는 런타임 번들. Django 서비스에 Node/Vite 서버 불필요.
- `templates/admin/base_site.html`, `static/ui/admin.css`: Django 관리자 구조를 유지한 별도 작은 테마. 관리자에는 Bootstrap 전역 CSS를 주입하지 않음.
- `config/ui_preview.py`: 명시적 조회 화면 6개에 `snp_preview=1`인 인증된 GET/200만 SAMEORIGIN. 일반 화면 및 다른 경로는 기존 DENY 유지.
- `/ui/compare/`: 같은 Django 화면을 세 가지 모드로 보여주는 조회 전용 비교. 기존 공통 인증 미들웨어 적용.

`localStorage`의 `snp.ui.mode.v1`에 선택을 저장한다. 값은 allowlist로 제한한다. 전환은 `<html data-snp-mode>`만 바꾸므로 폼·파일·CSRF·업무 DOM을 다시 생성하지 않는다. 브라우저 저장소가 차단되면 현재 탭 전환은 가능하고 저장 불가 안내를 제공한다.

## 빌드

```sh
npm ci --prefix frontend
npm run build --prefix frontend
npm test --prefix frontend
```

정적 번들은 기존 Django staticfiles로 제공한다. `.dockerignore`는 Node 의존성, Git, .env, 참고 문서/ZIP를 Docker build context에서 제외한다. 기존 컨테이너나 Dockerfile은 변경하지 않았다. 실제 배포는 수행하지 않았다.

## 공식 자료

- [Vite Django 등 서버 통합](https://vite.dev/guide/backend-integration.html)
- [Vite TypeScript 지원과 별도 타입 검사](https://vite.dev/guide/features.html)
- [기존 프로젝트에 React 점진 적용](https://react.dev/learn/add-react-to-an-existing-project)
- [HTMX](https://htmx.org/docs/)
