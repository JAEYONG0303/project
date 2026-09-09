"""대시보드(HTML) 에 넣을 집계값을 work/dash.json 으로 출력"""
import pandas as pd, numpy as np, json
from paths import WORK as SP
s=pd.read_pickle(f"{SP}/clean.pkl"); f=pd.read_pickle(f"{SP}/sessions.pkl")
allp=pd.read_pickle(f"{SP}/view_items.pkl"); ci=pd.read_pickle(f"{SP}/cart_items.pkl")
p=s[s.event_type=="purchase"]
lab=["0-1","1-2","2-3","3-5","5-8","8-12","12-20","20-50","50+"]
out={}
# price band conversion (viewed pairs) + removal (carted pairs)
t=allp[allp.price>0].groupby("band",observed=True).agg(viewed=("v","size"), carted=("carted","sum"), bought=("bought","sum"))
r=ci[ci.price>0].groupby("band",observed=True).agg(n=("removed","size"), removed=("removed","sum"))
out["price"]=[{"band":b,"viewed":int(t.loc[b,"viewed"]),"carted":int(t.loc[b,"carted"]),"bought":int(t.loc[b,"bought"]),
  "v2c":round(t.loc[b,"carted"]/t.loc[b,"viewed"]*100,1),"c2b":round(t.loc[b,"bought"]/t.loc[b,"carted"]*100,1),
  "cart_n":int(r.loc[b,"n"]),"removed":round(r.loc[b,"removed"]/r.loc[b,"n"]*100,1)} for b in lab]
# funnel
N=len(f); out["funnel"]=[{"stage":"전체 세션","n":int(N)},{"stage":"조회","n":int(f.has_view.sum())},{"stage":"장바구니","n":int(f.has_cart.sum())},{"stage":"구매","n":int(f.has_p.sum())}]
out["funnel_note"]={"purchase_no_cart":int((f.has_p&~f.has_cart).sum()),"purchase":int(f.has_p.sum())}
# monthly
g=f.groupby("month").agg(sessions=("n","size"), users=("user","nunique"), purch=("has_p","sum"))
g["orders"]=p.groupby("month").order_id.nunique(); g["items"]=p.groupby("month").size(); g["revenue"]=p.groupby("month").price.sum()
out["monthly"]=[{"month":m,"sessions":int(v.sessions),"users":int(v.users),"orders":int(v.orders),"items":int(v["items"]),"revenue":round(float(v.revenue)),
  "conv":round(v.purch/v.sessions*100,2),"aov":round(v.revenue/v.orders,1),"ipo":round(v["items"]/v.orders,1)} for m,v in g.iterrows()]
# cohort (first seen month, active)
first=f.groupby("user").start.min(); fm=first.dt.strftime("%Y-%m"); months=sorted(s.month.unique()); idx={m:i for i,m in enumerate(months)}
um=s.groupby(["user_id","month"]).size().reset_index()[["user_id","month"]]; um["fm"]=um.user_id.map(fm); um["k"]=um.month.map(idx)-um.fm.map(idx)
coh=um.groupby("fm").user_id.nunique(); ret=um.groupby(["fm","k"]).user_id.nunique()
out["cohort"]=[{"cohort":c,"n":int(coh[c]),"rates":[round(ret.get((c,k),0)/coh[c]*100,1) if k<=4-idx[c] else None for k in range(1,5)]} for c in months[:-1]]
# weekday x hour views
v=s[s.event_type=="view"]; hm=v.groupby(["dow","hour"]).size().unstack(fill_value=0).reindex(index=range(7),columns=range(24),fill_value=0)
out["heat"]=hm.values.tolist()
# tree
users=s.user_id.nunique(); buyers=p.user_id.nunique(); orders=p.order_id.nunique(); items=len(p); rev=p.price.sum()
out["tree"]={"revenue":round(float(rev)),"users":int(users),"buyers":int(buyers),"user_conv":round(buyers/users*100,2),"sessions":int(N),"sess_conv":round(f.has_p.sum()/N*100,2),
  "orders":int(orders),"opb":round(orders/buyers,2),"ipo":round(items/orders,2),"ppi":round(rev/items,2),"aov":round(rev/orders,1),"rpb":round(rev/buyers,1)}
out["misc"]={"removed_pct":19.8,"cart_later7":26.5,"repeat_buyers":23.5,"repurchase_days":17,"rep30":16.5,"sample_rows":int(len(s)),"full_rows":20692840}
json.dump(out,open(f"{SP}/dash.json","w"),ensure_ascii=False)
print(json.dumps(out["price"][:2],ensure_ascii=False)); print(out["tree"]); print(out["cohort"])
