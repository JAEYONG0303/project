"""정제: 완전 중복 제거, user_session 결측 제거, 30분 초과 공백에서 세션 분할, 주문 ID 부여 -> work/clean.pkl"""
import pandas as pd, numpy as np
from paths import SAMPLE, WORK as SP
s=pd.read_csv(SAMPLE)
n0=len(s)
s=s.drop_duplicates()
n1=len(s)
s=s.dropna(subset=["user_session"])
n2=len(s)
s["ts"]=pd.to_datetime(s["event_time"].str.replace(" UTC",""), utc=True)
s=s.sort_values(["user_id","user_session","ts"]).reset_index(drop=True)
gap=s.groupby(["user_id","user_session"]).ts.diff().dt.total_seconds()
newflag=(gap.isna()) | (gap>1800)
s["sess"]=s["user_session"]+"_"+newflag.groupby([s.user_id,s.user_session]).cumsum().astype(str)
s["month"]=s.ts.dt.strftime("%Y-%m"); s["dow"]=s.ts.dt.dayofweek; s["hour"]=s.ts.dt.hour
s["order_id"]=np.where(s.event_type=="purchase", s.sess+"_"+s.ts.astype(str), None)
s.to_pickle(f"{SP}/clean.pkl")
print("rows", n0, "->dedup", n1, "->drop null session", n2)
print("sessions raw", s.user_session.nunique(), "after 30min split", s.sess.nunique(), "orders", s.order_id.nunique(), "purchase rows", (s.event_type=="purchase").sum())
