"""0단계: zip에서 직접 읽어 사용자 2% 표본을 뽑고, 전체 대비 검증표를 출력한다.
표본 기준: md5(user_id) 16진수 끝 8자리 -> 정수 -> mod 100 < K"""
import zipfile, hashlib, json, time, sys
import pandas as pd
import numpy as np

from paths import ZIP, SAMPLE, WORK
OUT = SAMPLE
STATS = WORK / "full_stats.json"
K = 2  # percent

def keep_mask(uids):
    # md5(user_id) 마지막 2자리(16진수) -> 0~255 대신 10진 나머지 사용
    h = [int(hashlib.md5(str(u).encode()).hexdigest()[-8:], 16) % 100 < K for u in uids]
    return np.array(h)

months = ["2019-Oct","2019-Nov","2019-Dec","2020-Jan","2020-Feb"]
stats = {}
first = True
t0 = time.time()
if not ZIP.exists():
    raise SystemExit(f"원본 zip이 없습니다: {ZIP}  (캐글에서 archive.zip을 받아 raw/ 에 두거나 COSMETICS_ZIP 환경변수로 지정)")
with zipfile.ZipFile(ZIP) as z:
    for m in months:
        rows = 0; ev = {}; null_cat = 0; null_brand = 0; kept = 0
        with z.open(f"{m}.csv") as f:
            for chunk in pd.read_csv(f, chunksize=1_000_000, dtype={"user_id":"int64","product_id":"int64","category_id":"int64"}):
                rows += len(chunk)
                for k, v in chunk["event_type"].value_counts().items():
                    ev[k] = ev.get(k, 0) + int(v)
                null_cat += int(chunk["category_code"].isna().sum())
                null_brand += int(chunk["brand"].isna().sum())
                # 사용자 단위 해시: 청크 내 unique user에 대해서만 해시 계산
                uu = chunk["user_id"].unique()
                km = dict(zip(uu, keep_mask(uu)))
                sel = chunk[chunk["user_id"].map(km)]
                kept += len(sel)
                sel.to_csv(OUT, mode="w" if first else "a", header=first, index=False)
                first = False
        stats[m] = {"rows": rows, "events": ev, "null_category_code": null_cat, "null_brand": null_brand, "sample_rows": kept}
        print(m, rows, kept, f"{time.time()-t0:.0f}s", flush=True)
json.dump(stats, open(STATS, "w"), indent=1)
print("done")

# ---- 검증: 전체 vs 표본 ----
st = json.load(open(STATS)); s = pd.read_csv(OUT); s["month"] = s["event_time"].str[:7]
tot = sum(v["rows"] for v in st.values())
print(f"\n표본 {len(s):,}행 / 사용자 {s.user_id.nunique():,} / 세션 {s.user_session.nunique():,} / 구매 세션 {s[s.event_type=='purchase'].user_session.nunique():,}")
print("\n[검증] 지표, 전체%, 표본%, 차이")
mm = {"Oct":"10","Nov":"11","Dec":"12","Jan":"01","Feb":"02"}
for m, v in st.items():
    key = m[:5] + mm[m[5:]]; fs = v["rows"]/tot*100; ss = (s.month==key).mean()*100
    print(f"{m} 비중, {fs:.2f}, {ss:.2f}, {ss-fs:+.2f}")
fe = {}
for v in st.values():
    for k, c in v["events"].items(): fe[k] = fe.get(k, 0) + c
se = s.event_type.value_counts(normalize=True)*100
for k in ["view","cart","remove_from_cart","purchase"]: print(f"{k} 비중, {fe[k]/tot*100:.2f}, {se[k]:.2f}, {se[k]-fe[k]/tot*100:+.2f}")
fc = sum(v["null_category_code"] for v in st.values())/tot*100; fb = sum(v["null_brand"] for v in st.values())/tot*100
print(f"category_code 결측, {fc:.2f}, {s.category_code.isna().mean()*100:.2f}"); print(f"brand 결측, {fb:.2f}, {s.brand.isna().mean()*100:.2f}")
