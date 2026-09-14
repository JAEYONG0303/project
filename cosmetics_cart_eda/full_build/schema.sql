-- cosmetics_cart_eda 전체 원본(배치 1·2) 적재용 스키마.
-- full_build/data/batch{1,2}_clean.csv 컬럼과 1:1로 맞춘다. 이 파일은 사용자가 직접
-- MariaDB에서 실행한다 — build_batch.py는 DB에 접속하지 않는다.

CREATE DATABASE IF NOT EXISTS cosmetics_cart_eda
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE cosmetics_cart_eda;

CREATE TABLE IF NOT EXISTS cosmetics_events (
  event_time      DATETIME(0)     NOT NULL,
  event_type      VARCHAR(20)     NOT NULL,       -- view / cart / remove_from_cart / purchase
  product_id      BIGINT          NOT NULL,
  category_id     BIGINT          NOT NULL,
  category_code   VARCHAR(255)    NULL,           -- 원본 결측률 98%대, NULL 많음
  brand           VARCHAR(100)    NULL,
  price           DECIMAL(10,2)   NULL,
  user_id         BIGINT          NOT NULL,
  user_session    CHAR(36)        NOT NULL,       -- 원본 세션 UUID (30분 분할 전)
  ts              DATETIME(0)     NOT NULL,       -- event_time 을 UTC로 파싱한 값 (event_time과 사실상 동일)
  sess            VARCHAR(80)     NOT NULL,       -- user_session + 30분 분할 인덱스, 실제 세션 단위
  month           CHAR(7)         NOT NULL,       -- YYYY-MM
  dow             TINYINT         NOT NULL,       -- 0=월요일 ~ 6=일요일
  hour            TINYINT         NOT NULL,       -- 0~23 UTC
  order_id        VARCHAR(120)    NULL,           -- purchase 행에서만 채워짐 (sess + 구매시각)
  batch_id        TINYINT         NOT NULL,       -- 1 또는 2, 적재 시 LOAD DATA 명령마다 채워 넣는다
  PRIMARY KEY (user_id, sess, event_time, product_id),  -- 완전 중복이 이미 제거된 상태라 이 조합이 사실상 유일
  INDEX idx_session (sess),
  INDEX idx_user (user_id),
  INDEX idx_event_type (event_type),
  INDEX idx_month (month),
  INDEX idx_order (order_id)
) ENGINE=InnoDB;
