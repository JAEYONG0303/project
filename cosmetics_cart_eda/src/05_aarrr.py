"""4단계: 매출 분해 트리, 활성화, 리텐션 코호트, 재구매 간격"""
import pandas as pd, numpy as np
from paths import WORK as SP
s=pd.read_pickle(f"{SP}/clean.pkl"); f=pd.read_pickle(f"{SP}/sessions.pkl")
p=s[s.event_type=="purchase"]
pd.set_option("display.width",220)

print("[Revenue tree]")
users=s.user_id.nunique(); buyers=p.user_id.nunique(); orders=p.order_id.nunique(); items=len(p); rev=p.price.sum()
sessions=len(f); psess=f.has_p.sum()
print(f"users {users} buyers {buyers} user_conv {buyers/users*100:.2f}% sessions {sessions} sess/user {sessions/users:.2f} sess_conv {psess/sessions*100:.2f}%")
print(f"orders {orders} orders/buyer {orders/buyers:.2f} items/order {items/orders:.2f} price/item {rev/items:.2f} AOV {rev/orders:.2f} rev/buyer {rev/buyers:.2f} rev/user {rev/users:.3f} revenue {rev:.0f}")
print("check:", round(buyers*(orders/buyers)*(items/orders)*(rev/items)), "vs", round(rev))
ob=p.groupby("user_id").order_id.nunique()
print("buyers with 2+ orders %", round((ob>=2).mean()*100,1), "3+ %", round((ob>=3).mean()*100,1), "orders from repeat buyers %", round(ob[ob>=2].sum()/ob.sum()*100,1))
print("rev share top10% buyers", round(p.groupby("user_id").price.sum().sort_values(ascending=False).head(int(buyers*0.1)).sum()/rev*100,1))

print("\n[Activation] first session of each user")
fs=f[f.is_first]
print("users", len(fs), "first-session cart %", round(fs.has_cart.mean()*100,2), "first-session purchase %", round(fs.has_p.mean()*100,2), "first session 1 event %", round((fs.n==1).mean()*100,1))
# activation within 7 days of first seen: cart or purchase
first=f.groupby("user").start.min().rename("first_seen")
f2=f.join(first,on="user"); f2["d"]=(f2.start-f2.first_seen).dt.days
act7=f2[f2.d<=7].groupby("user").agg(cart=("has_cart","any"), buy=("has_p","any"))
print("within 7 days: cart %", round(act7.cart.mean()*100,2), "purchase %", round(act7.buy.mean()*100,2))
# users first seen Nov+ (less left-censored)
fm=first.dt.strftime("%Y-%m")
print("first-seen month counts", fm.value_counts().sort_index().to_dict())

print("\n[Retention] cohort by first-seen month: share active (any event) in month+k, share purchasing in month+k")
um=s.groupby(["user_id","month"]).size().reset_index()[["user_id","month"]]
um["fm"]=um.user_id.map(fm); months=sorted(s.month.unique()); idx={m:i for i,m in enumerate(months)}
um["k"]=um.month.map(idx)-um.fm.map(idx)
coh=um.groupby("fm").user_id.nunique()
ret=um.groupby(["fm","k"]).user_id.nunique().unstack().div(coh,axis=0).mul(100).round(1)
ret.insert(0,"n",coh); print(ret.to_string())
pm=p.groupby(["user_id","month"]).size().reset_index()[["user_id","month"]]; pm["fm"]=pm.user_id.map(fm); pm["k"]=pm.month.map(idx)-pm.fm.map(idx)
pret=pm.groupby(["fm","k"]).user_id.nunique().unstack().div(coh,axis=0).mul(100).round(2)
pret.insert(0,"n",coh); print("purchase in month+k (% of cohort)"); print(pret.to_string())
# buyer cohort: first purchase month -> repurchase in later months
fpm=p.groupby("user_id").month.min().rename("fpm")
pm["fpm"]=pm.user_id.map(fpm); pm["kb"]=pm.month.map(idx)-pm.fpm.map(idx)
bc=pm.groupby("fpm").user_id.nunique()
bret=pm.groupby(["fpm","kb"]).user_id.nunique().unstack().div(bc,axis=0).mul(100).round(1); bret.insert(0,"n",bc)
print("buyer cohort (first purchase month) repurchasing in month+k %"); print(bret.to_string())
# repurchase interval
od=p.groupby(["user_id","order_id"]).ts.min().reset_index().sort_values(["user_id","ts"])
gap=od.groupby("user_id").ts.diff().dt.days.dropna()
print("repurchase interval days: median", gap.median(), "p25", gap.quantile(.25), "p75", gap.quantile(.75), "n gaps", len(gap))
# 30-day repurchase among buyers whose first purchase <= 2020-01-30
fp=od.groupby("user_id").ts.min(); elig=fp[fp<=pd.Timestamp("2020-01-30",tz="UTC")]
rep30=od.merge(elig.rename("fp"),on="user_id"); rep30=rep30[(rep30.ts>rep30.fp)&(rep30.ts<=rep30.fp+pd.Timedelta(days=30))].user_id.nunique()
print("30-day repurchase rate (eligible buyers", len(elig), "):", round(rep30/len(elig)*100,1))
