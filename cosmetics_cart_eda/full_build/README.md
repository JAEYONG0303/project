# 전체 원본 배치 빌드 (표본이 아닌 2,069만 행 전체)

`../src/00_make_sample.py`가 만든 2% 표본(약 42만 행) 기반 분석은 그대로 두고, 이 폴더는
**원본 전체**를 다루기 위한 별도 빌드다. 목적은 데이터 프로젝트를 기획하고, 실제 DB에
적재하고, SQL을 어떤 방식으로 썼는지 증명하는 것 — 표본 분석과 결론을 다시 내는 게 아니다.

## 왜 배치로 나눴나

원본은 월별 CSV 5개, 압축 해제 시 총 2.3GB, 2,069만 행이다. 세션 분할(30분 초과 공백 기준)
은 `user_id·user_session·시간순 정렬` 후 diff를 계산해야 해서 청크 단위로는 정확히 계산할
수 없다 — 최소한 하나의 배치 전체는 메모리에 올려야 한다. 5개월을 한 번에 올리는 대신
3개월(배치 1: 2019-10~12) + 2개월(배치 2: 2020-01~02)로 나눠서, 배치당 최대 약 1,300만
행 규모로 메모리 부담을 줄였다.

## 처리 과정

```
archive.zip (Downloads, COSMETICS_ZIP 환경변수로 지정)
  → build_batch.py 1  (2019-10~12, 1M행씩 스트리밍 읽기 → concat)
  → build_batch.py 2  (2020-01~02)
      각 배치마다: 완전 중복 제거 → user_session 결측 제거 → 30분 초과 공백 세션 분할
                  → order_id 부여 (src/02_prep_clean.py와 동일 로직)
  → data/batch{1,2}_clean.csv   (DB 적재용, git 제외)
  → reports/batch{1,2}_summary.xlsx  (검토용 요약, 실제 집계값만)
  → schema.sql + LOAD_INSTRUCTIONS.md  (MariaDB 적재는 사용자가 직접)
```

## 한계

- **배치 경계 세션 분할**: 2019-12-31 심야에서 2020-01-01로 넘어가는 세션은 배치 1/2가
  각자 정제하기 때문에 하나의 세션이 둘로 나뉠 수 있다. 영향받는 사용자 수는 검증 전이라
  정확한 건수는 모른다 — DB 적재 후 `LOAD_INSTRUCTIONS.md`의 확인 쿼리로 직접 확인 가능.
- 이 폴더의 산출물(CSV)은 표본 검증 로직(00_make_sample.py의 전체 대비 비교)을 거치지
  않았다. 배치별 `reports/*.xlsx` 개요 시트의 행수·기간만 sanity check 대상이다.
- DB 적재·쿼리 실행은 사용자가 직접 한다. 이 폴더의 스크립트는 CSV·스키마·적재 SQL까지만
  준비한다.

## 재현

```bash
cd cosmetics_cart_eda/full_build
COSMETICS_ZIP="/path/to/archive.zip" python build_batch.py 1
COSMETICS_ZIP="/path/to/archive.zip" python build_batch.py 2
```
그 다음 `LOAD_INSTRUCTIONS.md`를 보고 MariaDB에 적재.
