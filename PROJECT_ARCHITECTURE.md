# 🗺️ Project Architecture & Navigation Map (PROJECT_ARCHITECTURE.md)

이 문서는 S&P 급식/식재료 관리 시스템의 전체 소프트웨어 구조, DB 엔티티 관계(ERD 뼈대), 앱별 파일 연관성 및 URL/View 매핑 현황을 정리한 핵심 탐색 지침서입니다.

---

## 1. 📁 전체 프로젝트 디렉토리 구조 (Directory Tree)

```text
c:\temp_capstone-sprint5
├── accounts/                     # 사용자 계정 및 권한 관리 앱
│   ├── admin.py
│   ├── models.py                # User (AbstractUser 확장: Role - ADMIN, NUTRITIONIST, SUPPLIER)
│   ├── urls.py                  # 로그인/로그아웃 및 계정 관련 라우팅
│   └── views.py                 # 인증 처리 뷰
├── config/                       # Django 프로젝트 설정 및 메인 엔트리
│   ├── settings.py              # 데이터베이스, 앱 등록, 정적파일 설정
│   ├── urls.py                  # 전체 앱 URL 루트 통합
│   ├── views.py                 # 대시보드/메인 홈 뷰 (home)
│   └── wsgi.py / asgi.py
├── forecasting/                  # 식수 예측 및 식재료 산출 앱
│   ├── forms.py / services/     # 예측 처리 및 식재료 필요량 연산 서비스
│   ├── models.py                # MealForecast, AttendancePrediction
│   ├── urls.py                  # /forecasting/ 예측 캘린더 및 식수 예측 라우팅
│   └── views.py                 # 예측 실행 및 결과 출력 뷰
├── inventory/                    # 식자재 마스터 및 재고 수불 관리 앱
│   ├── admin.py / forms.py
│   ├── management/commands/     # 엑셀/CSV 데이터 시딩 및 카테고리별 업체 자동 매핑 커맨드
│   ├── models.py                # Ingredient (식자재 마스터), InventoryLog (재고 수불 이력)
│   ├── urls.py                  # /inventory/ 재고 및 식자재 CRUD 라우팅
│   └── views.py                 # 식자재 등록, 엑셀 등록, 수불 등록 뷰
├── meals/                        # 식단표, 메뉴, 레시피 관리 앱
│   ├── models.py                # Menu, Recipe, DietPlan, DietMenu
│   ├── urls.py                  # /meals/ 일간/주간/월간 식단 등록, 레시피 라우팅
│   └── views.py                 # 식단표 캘린더, AJAX 메뉴 추가/삭제 API 뷰
├── procurement/                  # 발주, 거래처 관리 및 실무 문서양식 앱
│   ├── models.py                # Supplier (거래처 관리), PurchaseOrder (발주서 메인), OrderItem (발주 품목)
│   ├── urls.py                  # /procurement/ 발주생성, 스마트발주, 거래처관리(suppliers/) 라우팅
│   ├── views.py                 # 발주 목록/생성, 스마트 발주, 거래처 CRUD 뷰
│   └── views_new_docs.py        # 구매요청서, 검수일지, 정산서 문서 출력 뷰
├── static/                       # 글로벌 정적 자원 (CSS / JS / Images)
│   ├── css/                     # system.css, sp_final.css (메인 UI 및 배지 스타일)
│   └── js/                      # 프론트엔드 동적 스크립트
├── templates/                    # HTML 레이아웃 및 앱별 템플릿
│   ├── base.html                # 공통 레이아웃
│   ├── home.html                # 메인 대시보드
│   ├── partials/top_nav.html    # 상단 네비게이션 드롭다운 메뉴
│   ├── accounts/                # login.html, signup.html
│   ├── docs/                    # 실무 인쇄 문서 템플릿 모음 (월간정산, 검수일지 등)
│   ├── forecasting/             # 예측 캘린더 및 산출 템플릿
│   ├── inventory/               # 식자재 목록, 등록 템플릿
│   ├── meals/                   # daily, weekly, monthly 식단표 템플릿
│   └── procurement/             # order_list, order_from_mealplan, supplier_list.html
├── manage.py                     # Django 관리 실행파일
└── PROJECT_ARCHITECTURE.md      # 본 시스템 지점 지도 파일
```

---

## 2. 🗄️ 데이터베이스 모델 및 관계 (ERD 뼈대)

| 앱 (App) | 모델 (Model) | 주요 필드 (Fields) | 연관 모델 및 관계 (Relationships) | 역할 및 설명 |
| :--- | :--- | :--- | :--- | :--- |
| **accounts** | `User` | `username`, `role` (ADMIN/NUTRITIONIST/SUPPLIER), `name`, `phone_number` | - | 사용자 계정 및 납품 업체 계정 기본 모델 |
| **procurement** | `Supplier` | `category`, `name`, `business_items`, `phone_number`, `fax`, `mobile`, `remarks` | `user` 1:1 `User` (Optional) | **[신규] 발주 업체(거래처) 정보 관리 모델** |
| **inventory** | `Ingredient` | `name`, `spec`, `unit`, `unit_price`, `safe_stock_level`, `category` | `supplier` N:1 `User` | 식자재 마스터 정보 및 담당 공급업체 매핑 |
| **inventory** | `InventoryLog` | `log_type` (입고/출고/폐기/조정), `quantity`, `transaction_date`, `expiration_date` | `ingredient` N:1 `Ingredient` | 실시간 재고 입출고 및 변동 이력 로그 |
| **meals** | `Menu` | `name`, `category` (한식, 국, 반찬 등) | - | 식단표에 등록되는 메뉴 기본 정보 |
| **meals** | `Recipe` | `required_amount` (1인분 소요량) | `menu` N:1 `Menu`, `ingredient` N:1 `Ingredient` | 메뉴별 필요 식자재 및 1인 소요량 매핑 |
| **meals** | `DietPlan` | `target_date`, `meal_type` (조식/중식/석식), `headcount`, `is_served` | - | 특정 날짜 및 끼니별 식단 기본 단위 |
| **meals** | `DietMenu` | - | `diet_plan` N:1 `DietPlan`, `menu` N:1 `Menu` | 한 끼니(DietPlan)에 포함된 메뉴(Menu) 구성 목록 |
| **procurement** | `PurchaseOrder` | `status` (대기/승인/완료), `total_amount`, `created_at` | `supplier` N:1 `User` | 발주서 헤더 정보 |
| **procurement** | `OrderItem` | `required_qty`, `missing_qty`, `order_unit_price`, `estimated_price`, `target_date`, `meal_type` | `purchase_order` N:1 `PurchaseOrder`, `ingredient` N:1 `Ingredient` | 발주서 내 세부 식자재 항목 및 과거 단가 스냅샷 |
| **forecasting** | `AttendancePrediction`| `prediction_date`, `meal_type`, `predicted_count`, `model_name` | - | AI 기반 일자/끼니별 예상 식수 데이터 |

---

## 3. 🔗 핵심 URL & View 매핑 네비게이션 지도

### 3.1 발주 (Procurement) 모듈 (`procurement/urls.py`)
| URL Pattern | View Function | Template | 주요 기능 |
| :--- | :--- | :--- | :--- |
| `/procurement/` | `order_list` | `procurement/order_list.html` | 발주 목록 및 업체별 그룹핑 조회 |
| `/procurement/create-smart/` | `order_from_mealplan` | `procurement/order_from_mealplan.html` | 식단/예측/현재고 기반 부족량 자동 산출 및 발주 생성 |
| `/procurement/create/` | `order_create` | `procurement/order_create.html` | 간편/수동 발주 생성 |
| `/procurement/suppliers/` | `supplier_list` | `procurement/supplier_list.html` | **[신규] 거래처(발주업체) 현황 목록 및 관리** |
| `/procurement/suppliers/create/` | `supplier_create` | Modal / Form | **[신규] 신규 거래처 추가** |
| `/procurement/suppliers/<pk>/update/`| `supplier_update` | Modal / Form | **[신규] 거래처 정보 수정** |
| `/procurement/suppliers/<pk>/delete/`| `supplier_delete` | POST Action | **[신규] 거래처 정보 삭제** |
| `/procurement/docs/monthly-settlement/`| `monthly_settlement_view`| `docs/doc_monthly_settlement.html`| 월간 정산 보고서 A4 출력 뷰 |

### 3.2 식단 (Meals) 모듈 (`meals/urls.py`)
| URL Pattern | View Function | Template | 주요 기능 |
| :--- | :--- | :--- | :--- |
| `/meals/` | `mealplan_list` | `meals/mealplan_list.html` | 월간 식단표 캘린더 & 모달 식단 수정 |
| `/meals/create/` | `mealplan_create` | `meals/mealplan_create.html` | 일간 식단 등록/수정 (배지 칩 입력) |
| `/meals/weekly-create/` | `weekly_mealplan_create` | `meals/weekly_mealplan_create.html` | 주간 단위 식단 등록 및 AJAX 편집 |
| `/meals/monthly-create/` | `monthly_mealplan_create` | `meals/monthly_mealplan_create.html` | 월간 슬롯 생성을 통한 일괄 식단 등록 |

---

## 4. 🎨 UI/UX 주요 전역 CSS 맵핑 (`static/css/`)
- **`system.css`**: 시스템 기본 프레임워크 및 Bootstrap 커스텀 레이아웃
- **`sp_final.css`**: 식단 캘린더, 주간 편집기(`.sp-week-menu-list span`), 월간 모달 배지(`.sp-menu-token`), 종합 UI 폰트 및 패딩 스타일 정의
- **`sp_aligned_pages.css`**: 정렬이 적용된 등록 폼 및 카드 레이아웃 서브 페이지 전용 스타일

---
> 💡 **수정 가이드**: 향후 새로운 기능이나 디자인 수정 요청이 발생할 경우, 위의 테이블에서 관련 App, View, Template, CSS 위치를 확인하여 직접 수정 작업을 진행하면 됩니다.
