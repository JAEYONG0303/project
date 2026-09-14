"""원본 REES46 전체(2,069만 행)를 배치로 나눠 정제한다 — 기존 src/00_make_sample.py의
2% 표본이 아니라 전 행을 쓴다. 배치 1개를 한 번에 메모리에 올리는 이유는 세션 분할이
user_id·user_session·시간 순 정렬이 필요해서 청크 단위로는 정확히 계산할 수 없기 때문이다
(정제 로직은 src/02_prep_clean.py와 동일).

배치 경계(12월 31일→1월 1일)를 넘어가는 세션은 배치별로 따로 분할된다 — 영향은 작지만
README.md에 한계로 남긴다.

DB 적재는 이 스크립트가 하지 않는다. LOAD_INSTRUCTIONS.md 를 보고 사용자가 직접 한다.

사용: python full_build/build_batch.py 1   (또는 2)
"""
from __future__ import annotations

import argparse
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from paths import ZIP  # noqa: E402  (COSMETICS_ZIP 환경변수로 Downloads 경로 지정해서 씀)

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
REPORTS = ROOT / "reports"
DATA.mkdir(parents=True, exist_ok=True)
REPORTS.mkdir(parents=True, exist_ok=True)

BATCHES = {
    1: ["2019-Oct", "2019-Nov", "2019-Dec"],
    2: ["2020-Jan", "2020-Feb"],
}

DTYPES = {"user_id": "int64", "product_id": "int64", "category_id": "int64"}


def read_batch_raw(months: list[str]) -> pd.DataFrame:
    """zip에서 해당 월들을 1M행씩 스트리밍으로 읽어 concat. 샘플링 없이 전 행."""
    if not ZIP.exists():
        raise SystemExit(f"원본 zip이 없습니다: {ZIP} (COSMETICS_ZIP 환경변수로 archive.zip 경로 지정)")
    parts = []
    t0 = time.time()
    with zipfile.ZipFile(ZIP) as z:
        for m in months:
            with z.open(f"{m}.csv") as f:
                for chunk in pd.read_csv(f, chunksize=1_000_000, dtype=DTYPES):
                    parts.append(chunk)
            print(f"[읽기] {m} 완료 ({time.time()-t0:.0f}s)", flush=True)
    return pd.concat(parts, ignore_index=True)


def clean(raw: pd.DataFrame) -> pd.DataFrame:
    """src/02_prep_clean.py와 동일한 정제 로직(완전 중복 제거, user_session 결측 제거,
    30분 초과 공백 세션 분할, order_id 부여)."""
    n0 = len(raw)
    s = raw.drop_duplicates()
    n1 = len(s)
    s = s.dropna(subset=["user_session"])
    n2 = len(s)
    s["ts"] = pd.to_datetime(s["event_time"].str.replace(" UTC", ""), utc=True)
    s = s.sort_values(["user_id", "user_session", "ts"]).reset_index(drop=True)
    gap = s.groupby(["user_id", "user_session"]).ts.diff().dt.total_seconds()
    newflag = gap.isna() | (gap > 1800)
    s["sess"] = s["user_session"] + "_" + newflag.groupby([s.user_id, s.user_session]).cumsum().astype(str)
    s["month"] = s.ts.dt.strftime("%Y-%m")
    s["dow"] = s.ts.dt.dayofweek
    s["hour"] = s.ts.dt.hour
    s["order_id"] = np.where(s.event_type == "purchase", s.sess + "_" + s.ts.astype(str), None)
    return s, {"raw_rows": n0, "after_dedup": n1, "after_drop_null_session": n2}


def write_summary_xlsx(path: Path, batch_id: int, months: list[str], s: pd.DataFrame, counts: dict) -> None:
    overview = pd.DataFrame([
        {"항목": "대상 월", "값": ", ".join(months)},
        {"항목": "원본 행수 (배치)", "값": counts["raw_rows"]},
        {"항목": "완전 중복 제거 후", "값": counts["after_dedup"]},
        {"항목": "user_session 결측 제거 후", "값": counts["after_drop_null_session"]},
        {"항목": "최종 세션 수", "값": s["sess"].nunique()},
        {"항목": "최종 주문 수", "값": s["order_id"].nunique()},
        {"항목": "기간 시작", "값": str(s["ts"].min())},
        {"항목": "기간 끝", "값": str(s["ts"].max())},
    ])
    event_dist = s["event_type"].value_counts().rename_axis("event_type").reset_index(name="count")
    daily = s.assign(date=s["ts"].dt.date).groupby("date").size().rename("event_count").reset_index()
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        overview.to_excel(writer, sheet_name="개요", index=False)
        event_dist.to_excel(writer, sheet_name="event_type 분포", index=False)
        daily.to_excel(writer, sheet_name="일별 이벤트 추이", index=False)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("batch", type=int, choices=[1, 2])
    a = ap.parse_args()

    months = BATCHES[a.batch]
    print(f"=== 배치 {a.batch}: {months} ===")
    raw = read_batch_raw(months)
    print(f"[읽기 완료] {len(raw):,}행")

    s, counts = clean(raw)
    print(f"[정제] {counts['raw_rows']:,} -> 중복제거 {counts['after_dedup']:,} "
          f"-> 세션결측제거 {counts['after_drop_null_session']:,}")
    print(f"[결과] 세션 {s['sess'].nunique():,} / 주문 {s['order_id'].nunique():,}")

    out_csv = DATA / f"batch{a.batch}_clean.csv"
    s.to_csv(out_csv, index=False)
    print(f"[저장] {out_csv} ({len(s):,}행)")

    out_xlsx = REPORTS / f"batch{a.batch}_summary.xlsx"
    write_summary_xlsx(out_xlsx, a.batch, months, s, counts)
    print(f"[저장] {out_xlsx}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
