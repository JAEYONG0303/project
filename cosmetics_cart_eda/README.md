# 화장품 몰 행동 로그 EDA — 장바구니 이탈은 어디서 생기는가

Kaggle [eCommerce Events History in Cosmetics Shop](https://www.kaggle.com/datasets/mkechinov/ecommerce-events-history-in-cosmetics-shop) (REES46) 데이터로 한 이커머스 행동 로그를 처음부터 끝까지 분석한 연습입니다.
한 몰, 2019-10 ~ 2020-02, 국가·통화 미상. 전체 2,069만 행 중 **사용자 2% 표본**(약 40만 행)으로 진행했습니다.

## 결론 한 줄

담긴 상품의 약 20%가 같은 세션에서 제거되지만 제거율은 가격대·브랜드와 무관하게 16~22%로 고르다.
가격 저항은 장바구니가 아니라 **조회→담기** 단계에서 생기며(담기율 20.4% → 4.7%), 일단 담긴 뒤의 구매율은 16~19%로 평탄하다.
장바구니는 세션을 넘어 유지되므로 세션 단위 전환율은 이탈을 과소 추정한다.

## 산출물

| 산출물 | 링크 |
|---|---|
| 보고서 전문 (표본 기준, 0~4단계 표, AARRR, 한계, 재실행 프롬프트) | [REPORT.md](REPORT.md) |
| 인터랙티브 대시보드 (HTML) | [dashboard/cosmetics_dashboard.html](dashboard/cosmetics_dashboard.html) · [게시본](https://claude.ai/code/artifact/3cc94119-14e5-4def-ae66-9950f11c213f) |
| Notion 보고서 | https://app.notion.com/p/3d603811541181849124f7f90240b4ed |
| Figma 시안 | https://www.figma.com/design/VsC0tCiC0P4N9PxCiv10F7 |
| Tableau Public | https://public.tableau.com/app/profile/.15597934/viz/EDA_17888837630310/1_1 |
| GitHub | https://github.com/JAEYONG0303/project/tree/main/cosmetics_cart_eda |

## 재현 방법

데이터 파일은 저장소에 없습니다. 캐글에서 `archive.zip`(월별 CSV 5개, 약 450MB)을 받아 `raw/` 에 두거나 `COSMETICS_ZIP` 환경변수로 위치를 지정합니다.

```bash
pip install pandas numpy
cd src
python 00_make_sample.py      # zip에서 사용자 2% 표본 추출 + 전체 대비 검증표
python 01_structure.py        # 1단계 구조 점검
python 02_prep_clean.py       # 정제: 중복 제거, 30분 세션 분할, 주문 ID
python 03_demand.py           # 2단계 수요 탐색
python 04_conversion.py       # 3단계 구매 전환
python 05_aarrr.py            # 4단계 매출 분해 트리, 리텐션 코호트
python 06_export_tableau.py   # Tableau용 CSV 4개
python 07_dashboard_data.py   # 대시보드용 집계 JSON
```

표본 추출은 `md5(user_id) mod 100 < 2` 로 결정적이라 누가 돌려도 같은 사용자가 뽑힙니다. Python 3.11, pandas 2.x에서 확인했습니다.

## 정의와 정제 기준

- 사용자 = `user_id`. 세션 = `user_session`을 30분 초과 공백에서 분할한 것(89,826 → 95,171).
- 주문 = 같은 세션·같은 초의 구매 행 묶음. 상품 = 구매 행 1개(수량 정보 없음).
- 완전 중복 23,223행 제거, `user_session` 결측 42행 제거, 가격 0 이하 979행은 가격대 분석에서 제외.
- 모든 전환율은 분자÷분모를 명시합니다. 자세한 표는 REPORT.md 참고.

## 폴더

```
src/         분석 스크립트 (번호 순서대로 실행)
dashboard/   HTML 대시보드 원본
tableau/     Tableau용 CSV (큰 파일 3개는 git 제외, cohort_retention.csv만 포함)
raw/         archive.zip 두는 곳 (git 제외)
sample/      표본 CSV 생성 위치 (git 제외)
work/        중간 산출물 (git 제외)
```

## 한계

- 한 몰, 5개월, 2% 표본. 절대 수치는 표본값이고 비율만 전체 추정에 씁니다.
- `category_code` 98% 결측, `brand` 42% 결측. 통화·국가·수량·환불 정보 없음.
- 유입 채널과 Referral 정보가 없어 AARRR 중 Acquisition·Referral은 다룰 수 없습니다.
- 2019-10 코호트는 데이터 시작 전 활동자가 섞여 있어(좌측 절단) 리텐션 비교에서 제외합니다.
