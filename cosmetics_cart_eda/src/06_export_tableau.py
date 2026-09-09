"""Tableau Public 용 CSV 4개 내보내기: events_clean, sessions, cart_items, cohort_retention"""
import pandas as pd, numpy as np, os
from paths import WORK as SP, TABLEAU
OUT=str(TABLEAU)
os.makedirs(OUT, exist_ok=True)
s=pd.read_pickle(f"{SP}/clean.pkl"); f=pd.read_pickle(f"{SP}/sessions.pkl")
bins=[0,1,2,3,5,8,12,20,50,1e9]; lab=["0-1","1-2","2-3","3-5","5-8","8-12","12-20","20-50","50+"]
dow_kr={0:"월",1:"화",2:"수",3:"목",4:"금",5:"토",6:"일"}

# 1. events_clean
e=s.copy()
e["event_time_utc"]=e.ts.dt.strftime("%Y-%m-%d %H:%M:%S")
e["date"]=e.ts.dt.strftime("%Y-%m-%d")
e["weekday"]=e.dow.map(dow_kr); e["weekday_num"]=e.dow+1
e["price_band"]=pd.cut(e.price,bins,labels=lab,right=False).astype(object).where(e.price>0,"0 이하")
e["brand_filled"]=e.brand.fillna("(미상)")
e["session_id"]=e.sess
e=e[["event_time_utc","date","month","weekday_num","weekday","hour","event_type","product_id","category_id","brand","brand_filled","price","price_band","user_id","user_session","session_id","order_id"]]
e.to_csv(f"{OUT}/events_clean.csv", index=False, encoding="utf-8-sig")
print("events_clean", e.shape)

# 2. sessions
ss=f.reset_index().rename(columns={"sess":"session_id","user":"user_id","n":"n_events","n_prod":"n_products","sess_idx":"session_order"})
ss["user_session"]=ss.session_id.str.rsplit("_",n=1).str[0]
ss["start_utc"]=ss.start.dt.strftime("%Y-%m-%d %H:%M:%S"); ss["end_utc"]=ss.end.dt.strftime("%Y-%m-%d %H:%M:%S")
ss["weekday"]=ss.dow.map(dow_kr)
ss["duration_min"]=ss.dur_min.round(2)
ss["prior_buyer"]=ss.prior_buyer.fillna(False)
ss["stage"]=np.select([ss.has_p, ss.has_cart, ss.has_view],["purchase","cart","view"],"other")
ss=ss[["session_id","user_id","user_session","start_utc","end_utc","month","weekday","hour","n_events","n_products","duration_min","has_view","has_cart","has_rm","has_p","stage","session_order","is_first","prior_buyer"]]
ss.columns=["session_id","user_id","user_session","start_utc","end_utc","month","weekday","hour","n_events","n_products","duration_min","has_view","has_cart","has_remove","has_purchase","funnel_stage","session_order","is_first_session","prior_buyer"]
ss.to_csv(f"{OUT}/sessions.csv", index=False, encoding="utf-8-sig")
print("sessions", ss.shape)

# 3. cohort_retention (long format)
p=s[s.event_type=="purchase"]
first=f.groupby("user").start.min(); fm=first.dt.strftime("%Y-%m")
months=sorted(s.month.unique()); idx={m:i for i,m in enumerate(months)}
um=s.groupby(["user_id","month"]).size().reset_index()[["user_id","month"]]; um["cohort"]=um.user_id.map(fm); um["k"]=um.month.map(idx)-um.cohort.map(idx)
coh=um.groupby("cohort").user_id.nunique()
a=um.groupby(["cohort","k"]).user_id.nunique().rename("users").reset_index(); a["cohort_type"]="첫 등장 월"; a["metric"]="활동"
pm=p.groupby(["user_id","month"]).size().reset_index()[["user_id","month"]]; pm["cohort"]=pm.user_id.map(fm); pm["k"]=pm.month.map(idx)-pm.cohort.map(idx)
b=pm.groupby(["cohort","k"]).user_id.nunique().rename("users").reset_index(); b["cohort_type"]="첫 등장 월"; b["metric"]="구매"
fpm=p.groupby("user_id").month.min(); pm2=pm.copy(); pm2["cohort"]=pm2.user_id.map(fpm); pm2["k"]=pm2.month.map(idx)-pm2.cohort.map(idx)
bc=pm2.groupby("cohort").user_id.nunique()
c=pm2.groupby(["cohort","k"]).user_id.nunique().rename("users").reset_index(); c["cohort_type"]="첫 구매 월"; c["metric"]="재구매"
cr=pd.concat([a,b,c]); cr["cohort_size"]=np.where(cr.cohort_type=="첫 등장 월", cr.cohort.map(coh), cr.cohort.map(bc))
cr["rate_pct"]=(cr.users/cr.cohort_size*100).round(2)
cr=cr[["cohort_type","metric","cohort","cohort_size","k","users","rate_pct"]].rename(columns={"k":"months_since"})
cr.to_csv(f"{OUT}/cohort_retention.csv", index=False, encoding="utf-8-sig")
print("cohort", cr.shape)

# 4. cart_items: session-product pairs with view/cart/remove/purchase flags
ssort=s.sort_values(["sess","ts"])
vp=ssort[ssort.event_type=="view"].groupby(["sess","product_id"]).ts.min().rename("t_view")
cp=ssort[ssort.event_type=="cart"].groupby(["sess","product_id"]).ts.min().rename("t_cart")
rp=ssort[ssort.event_type=="remove_from_cart"].groupby(["sess","product_id"]).ts.max().rename("t_remove")
pp=ssort[ssort.event_type=="purchase"].groupby(["sess","product_id"]).ts.max().rename("t_purchase")
it=pd.concat([vp,cp,rp,pp],axis=1).reset_index().rename(columns={"sess":"session_id"})
it["viewed"]=it.t_view.notna(); it["carted"]=it.t_cart.notna()
it["removed_after_cart"]=(it.t_remove>=it.t_cart).fillna(False)
it["purchased_after_cart"]=(it.t_purchase>=it.t_cart).fillna(False)
it["purchased"]=it.t_purchase.notna()
meta=s.groupby("product_id").agg(price=("price","median"), brand=("brand","first"), category_id=("category_id","first"))
it=it.join(meta,on="product_id")
it["price_band"]=pd.cut(it.price,bins,labels=lab,right=False).astype(object).where(it.price>0,"0 이하")
it["brand_filled"]=it.brand.fillna("(미상)")
it["user_id"]=it.session_id.map(f.user); it["month"]=it.session_id.map(f.month)
for c_ in ["t_view","t_cart","t_remove","t_purchase"]: it[c_]=it[c_].dt.strftime("%Y-%m-%d %H:%M:%S")
it=it[["session_id","user_id","month","product_id","category_id","brand","brand_filled","price","price_band","viewed","carted","removed_after_cart","purchased_after_cart","purchased","t_view","t_cart","t_remove","t_purchase"]]
it.to_csv(f"{OUT}/cart_items.csv", index=False, encoding="utf-8-sig")
print("cart_items", it.shape, "carted", it.carted.sum(), "removed_after_cart %", round(it[it.carted].removed_after_cart.mean()*100,1))
for fn in os.listdir(OUT): print(fn, round(os.path.getsize(f"{OUT}/{fn}")/1e6,1), "MB")
