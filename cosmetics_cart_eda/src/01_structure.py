"""1단계: 구조 점검. 표본 CSV 기준 월별 행 수, 이벤트 비율, 결측, 세션당 이벤트, price, 시간대, 중복."""
import pandas as pd, numpy as np
from paths import SAMPLE
s = pd.read_csv(SAMPLE)
s["ts"] = pd.to_datetime(s["event_time"].str.replace(" UTC",""), utc=True); s["month"] = s.ts.dt.strftime("%Y-%m")
print("기간", s.ts.min(), "~", s.ts.max(), "| UTC 표기:", s["event_time"].str[-3:].value_counts().to_dict())
print("\n[1] 월 x 이벤트 유형")
ct = pd.crosstab(s.month, s.event_type)[["view","cart","remove_from_cart","purchase"]]; ct["total"] = ct.sum(axis=1)
print(ct.to_string()); print((ct.div(ct.total, axis=0)*100).round(1).to_string())
print("\n[2] 결측 % (월별)")
print(s.groupby("month")[["category_code","brand","user_session","price"]].apply(lambda d: d.isna().mean()*100).round(2).to_string())
print("category_code 비결측 종류:", s.category_code.dropna().nunique(), s.category_code.value_counts().head(10).to_dict())
print("category_id", s.category_id.nunique(), "brand", s.brand.nunique(), "product", s.product_id.nunique())
print("\n[3] 세션당 이벤트 수")
ss = s.dropna(subset=["user_session"]); ev = ss.groupby("user_session").size()
print(ev.describe(percentiles=[.25,.5,.75,.9,.95,.99]).round(1).to_string())
bins = [0,1,2,5,10,20,50,100,1e9]; lab = ["1","2","3-5","6-10","11-20","21-50","51-100","100+"]
print(pd.cut(ev, bins, labels=lab).value_counts(normalize=True).sort_index().mul(100).round(1).to_string())
dur = ss.groupby("user_session").ts.agg(["min","max"]); d = (dur["max"]-dur["min"]).dt.total_seconds()/60
print("세션 길이(분) 중앙", round(d.median(),1), "p90", round(d.quantile(.9),1), "p99", round(d.quantile(.99),1), "최대", round(d.max(),1))
print("하루 넘긴 세션", int((dur["min"].dt.date != dur["max"].dt.date).sum()))
sso = ss.sort_values(["user_session","ts"]); gap = sso.groupby("user_session").ts.diff().dt.total_seconds()/60
print("30분 초과 공백 포함 세션", int((gap>30).groupby(sso.user_session).any().sum()), "/", ss.user_session.nunique())
print("\n[4] price")
print(s.price.describe(percentiles=[.01,.05,.25,.5,.75,.95,.99]).round(2).to_string())
print("0 이하 행", int((s.price<=0).sum()), "| 이벤트별", s[s.price<=0].event_type.value_counts().to_dict(), "| 0:", int((s.price==0).sum()), "음수:", int((s.price<0).sum()))
print("구매 price 중앙값", s[s.event_type=="purchase"].price.median())
print("\n[5] 시간대(UTC) %"); print(s.ts.dt.hour.value_counts(normalize=True).sort_index().mul(100).round(1).to_dict())
print("요일 % (0=월)", s.ts.dt.dayofweek.value_counts(normalize=True).sort_index().mul(100).round(1).to_dict())
print("\n[6] 완전 중복 행", int(s.duplicated().sum()), s[s.duplicated()].event_type.value_counts().to_dict())
p = s[s.event_type=="purchase"]
print("구매 행", len(p), "| (세션,초) 조합 =", p.groupby(["user_session","ts"]).ngroups, "| (세션,초,상품) =", p.groupby(["user_session","ts","product_id"]).ngroups)
