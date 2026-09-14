# MariaDB 적재 방법 (직접 실행)

`build_batch.py`는 정제까지만 하고 DB에는 손대지 않는다. 아래 명령을 본인 MariaDB
클라이언트(HeidiSQL, DBeaver, `mysql` CLI 등)에서 직접 실행한다.

## 1. 스키마 생성

`schema.sql` 내용을 그대로 실행한다(`cosmetics_events` 테이블 생성).

## 2. 배치 적재

CSV 컬럼 순서는 `build_batch.py`가 만든 그대로다:
`event_time, event_type, product_id, category_id, category_code, brand, price, user_id, user_session, ts, sess, month, dow, hour, order_id`

`batch_id`는 파일에 없는 컬럼이라 `SET`으로 적재 시 채운다.

```sql
USE cosmetics_cart_eda;

-- local_infile이 꺼져 있으면 먼저 `SET GLOBAL local_infile = 1;` (서버) 또는
-- 클라이언트 접속 옵션에서 --local-infile=1

LOAD DATA LOCAL INFILE 'C:/Users/wodyd/Desktop/Projects/sesac-web/cosmetics_cart_eda/full_build/data/batch1_clean.csv'
INTO TABLE cosmetics_events
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(event_time, event_type, product_id, category_id, category_code, brand, price,
 user_id, user_session, ts, sess, month, dow, hour, @order_id)
SET order_id = NULLIF(@order_id, ''), batch_id = 1;

LOAD DATA LOCAL INFILE 'C:/Users/wodyd/Desktop/Projects/sesac-web/cosmetics_cart_eda/full_build/data/batch2_clean.csv'
INTO TABLE cosmetics_events
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(event_time, event_type, product_id, category_id, category_code, brand, price,
 user_id, user_session, ts, sess, month, dow, hour, @order_id)
SET order_id = NULLIF(@order_id, ''), batch_id = 2;
```

## 3. 적재 후 확인 (직접 SQL 짜보기용 — 여기 있는 값은 참고용, 실제로는 본인이 실행해서 확인)

```sql
-- 배치별 행수
SELECT batch_id, COUNT(*) FROM cosmetics_events GROUP BY batch_id;

-- event_type 분포
SELECT event_type, COUNT(*) FROM cosmetics_events GROUP BY event_type;

-- 가격대별 담기 전환율(조회→담기) — REPORT.md/대시보드에 쓴 것과 같은 정의를 SQL로
SELECT
  CASE
    WHEN price < 1 THEN '0-1' WHEN price < 2 THEN '1-2' WHEN price < 3 THEN '2-3'
    WHEN price < 5 THEN '3-5' WHEN price < 8 THEN '5-8' WHEN price < 12 THEN '8-12'
    WHEN price < 20 THEN '12-20' WHEN price < 50 THEN '20-50' ELSE '50+'
  END AS price_band,
  SUM(event_type='cart') / NULLIF(SUM(event_type='view'), 0) * 100 AS view_to_cart_pct
FROM cosmetics_events
WHERE price > 0
GROUP BY price_band;
```
이 세 번째 쿼리 결과가 기존 2% 표본 기반 대시보드의 20.4%~4.7% 추세와 방향이 비슷하게
나오는지 대조해보면, 전체 데이터로도 표본 분석이 맞았는지 검증이 된다.

## 참고

- 배치 경계(2019-12-31 → 2020-01-01) 근처에서 활동한 소수 사용자는 세션이 배치 1/2로
  갈려서 `sess` 값이 실제보다 하나 더 나뉠 수 있다. 두 배치를 합쳐서 보는 분석(월별 집계 등)
  에는 영향이 없고, 세션 단위 지표(세션 수, 세션 전환율)에서 아주 미세한 과대 계산 가능성이
  있다는 정도로만 참고.
- `full_build/data/*.csv`는 git에 안 올라간다(`.gitignore`). 로컬에만 남는다.
