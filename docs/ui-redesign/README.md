# SNP 실험 UI 브랜치

작업 브랜치: `feature/ui-redesign-three-modes`. 기준 `origin/sprint-final` = `133b950221bd9cc1effaa51539abf7f88bb095c1`.

일반 화면 상단의 MODE 1/2/3을 선택하면 즉시 전환된다. 마지막 선택은 페이지 이동과 브라우저 재실행 후에도 유지된다. `/ui/compare/`에서 실제 같은 업무 화면을 나란히 비교할 수 있다. 저장 작업은 비교 창 밖의 일반 화면에서 한다.

- [실제 ZIP 분석](REFERENCE_ANALYSIS.md)
- [기술 선택과 빌드](ARCHITECTURE.md)
- [디자인 시스템](DESIGN_SYSTEM.md)
- [화면 적용 범위](SCREEN_COVERAGE.md)
- [검증 결과](TEST_REPORT.md)
- [스크린샷](screenshots/)

운영 DB·8000/8007 서비스·AI 모델을 변경하지 않았다. 실험 브랜치를 실행할 때도 반드시 별도 DB와 포트를 사용한다. 테스트 절차와 격리 컨테이너 명령은 검증 보고서와 `verification/ui-three-modes-20261105/`를 참조한다. 운영 배포는 이 작업에 포함되지 않는다.
