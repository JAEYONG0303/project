"""3단계: 구매 전환. 세션 깔때기, 장바구니 제거, 가격대·브랜드·카테고리별 전환, 무구매 세션 특징 -> work/sessions.pkl 등"""
import pandas as pd, numpy as np
from paths import WORK as SP
s=pd.read_pickle(f"{SP}/clean.pkl")
pd.set_option("display.width",220)

f=s.groupby("sess").agg(user=("user_id","first"), n=("event_type","size"),
    has_view=("event_type",lambda x:(x=="view").any()), has_cart=("event_type",lambda x:(x=="cart").any()),
    has_rm=("event_type",lambda x:(x=="remove_from_cart").any()), has_p=("event_type",lambda x:(x=="purchase").any()),
    start=("ts","min"), end=("ts","max"), month=("month","first"), hour=("hour","first"), dow=("dow","first"),
    n_prod=("product_id","nunique"))
f["dur_min"]=(f.end-f.start).dt.total_seconds()/60
N=len(f)
print("[1] session funnel  N sessions", N)
print("view", f.has_view.sum(), "cart", f.has_cart.sum(), "purchase", f.has_p.sum())
print("view&cart", (f.has_view&f.has_cart).sum(), "view&cart&purchase", (f.has_view&f.has_cart&f.has_p).sum(), "cart&purchase", (f.has_cart&f.has_p).sum())
print("purchase w/o cart in session", (f.has_p&~f.has_cart).sum(), "purchase w/o view", (f.has_p&~f.has_view).sum(), "cart w/o view", (f.has_cart&~f.has_view).sum())
print("sessions with one event:", f[f.n==1].shape[0])
print("first event type of sessions:", s.sort_values("ts").groupby("sess").event_type.first().value_counts(normalize=True).mul(100).round(1).to_dict())
comp=(f.has_view.map({True:"V",False:""})+f.has_cart.map({True:"C",False:""})+f.has_rm.map({True:"R",False:""})+f.has_p.map({True:"P",False:""}))
print("session composition top:", comp.value_counts(normalize=True).mul(100).round(1).head(12).to_dict())

ss=s.sort_values(["sess","ts"])
fv=ss[ss.event_type=="view"].groupby("sess").ts.min(); fc=ss[ss.event_type=="cart"].groupby("sess").ts.min(); fp=ss[ss.event_type=="purchase"].groupby("sess").ts.min()
o=pd.DataFrame({"fv":fv,"fc":fc,"fp":fp})
step1=(o.fv.notna()).sum(); step2=((o.fv.notna())&(o.fc>=o.fv)).sum(); step3=((o.fv.notna())&(o.fc>=o.fv)&(o.fp>=o.fc)).sum()
print("ordered funnel: view", step1, "-> cart after view", step2, "-> purchase after cart", step3)

print("\n[2] cart -> remove")
cp=ss[ss.event_type=="cart"].groupby(["sess","product_id"]).ts.min().rename("tc")
rp=ss[ss.event_type=="remove_from_cart"].groupby(["sess","product_id"]).ts.max().rename("tr")
pp=ss[ss.event_type=="purchase"].groupby(["sess","product_id"]).ts.max().rename("tp")
cart_items=cp.to_frame().join(rp).join(pp)
cart_items["removed"]=cart_items.tr>=cart_items.tc
cart_items["purchased"]=cart_items.tp>=cart_items.tc
print("cart items (sess,product):", len(cart_items), "removed later %", round(cart_items.removed.mean()*100,1), "purchased %", round(cart_items.purchased.mean()*100,1), "neither %", round((~cart_items.removed&~cart_items.purchased).mean()*100,1), "both %", round((cart_items.removed&cart_items.purchased).mean()*100,1))
rm_all=ss[ss.event_type=="remove_from_cart"].groupby(["sess","product_id"]).size()
print("remove pairs total", len(rm_all), "had cart in same session %", round(rm_all.index.isin(cp.index).mean()*100,1))
cs=f[f.has_cart]
print("cart sessions", len(cs), "with remove %", round(cs.has_rm.mean()*100,1))
print("purchase rate: cart sessions w/ remove", round(cs[cs.has_rm].has_p.mean()*100,2), "w/o remove", round(cs[~cs.has_rm].has_p.mean()*100,2))
price=ss.groupby("product_id").price.median()
cart_items=cart_items.reset_index(); cart_items["price"]=cart_items.product_id.map(price)
bins=[0,1,2,3,5,8,12,20,50,1e9]; lab=["0-1","1-2","2-3","3-5","5-8","8-12","12-20","20-50","50+"]
cart_items["band"]=pd.cut(cart_items.price,bins,labels=lab,right=False)
print("\ncart item outcome by price band")
print(cart_items[cart_items.price>0].groupby("band",observed=True).agg(n=("removed","size"), removed_pct=("removed",lambda x:round(x.mean()*100,1)), purchased_pct=("purchased",lambda x:round(x.mean()*100,1))).to_string())
cart_items.to_pickle(f"{SP}/cart_items.pkl")

print("\n[3] conversion by price band (session-product pairs viewed)")
vp=ss[ss.event_type=="view"].groupby(["sess","product_id"]).size().rename("v")
allp=vp.to_frame().join(cp).join(pp)
allp=allp.reset_index(); allp["price"]=allp.product_id.map(price); allp["band"]=pd.cut(allp.price,bins,labels=lab,right=False)
allp["carted"]=allp.tc.notna(); allp["bought"]=allp.tp.notna()
t=allp[allp.price>0].groupby("band",observed=True).agg(viewed=("v","size"), carted=("carted","sum"), bought=("bought","sum"))
t["view_to_cart_%"]=(t.carted/t.viewed*100).round(1); t["cart_to_buy_%"]=(t.bought/t.carted*100).round(1); t["view_to_buy_%"]=(t.bought/t.viewed*100).round(2)
print(t.to_string())
print("overall: viewed", len(allp), "v2c", round(allp.carted.mean()*100,1), "c2b", round(allp.bought.sum()/allp.carted.sum()*100,1), "v2b", round(allp.bought.mean()*100,2))
allp.to_pickle(f"{SP}/view_items.pkl")

print("\n[4] conversion by brand (top 12 by viewed pairs)")
allp["brand"]=allp.product_id.map(ss.groupby("product_id").brand.first())
b=allp.dropna(subset=["brand"]).groupby("brand").agg(viewed=("v","size"), carted=("carted","sum"), bought=("bought","sum"), med_price=("price","median")).sort_values("viewed",ascending=False)
b["view_to_cart_%"]=(b.carted/b.viewed*100).round(1); b["cart_to_buy_%"]=(b.bought/b.carted*100).round(1); b["view_to_buy_%"]=(b.bought/b.viewed*100).round(2)
print("brand-known overall: v2c", round(b.carted.sum()/b.viewed.sum()*100,1), "c2b", round(b.bought.sum()/b.carted.sum()*100,1))
print(b.head(12).round(2).to_string())
u=allp[allp.brand.isna()]; print("brand unknown: viewed", len(u), "v2c", round(u.carted.mean()*100,1), "c2b", round(u.bought.sum()/u.carted.sum()*100,1))

print("\n[5] conversion by category (top 10 by viewed pairs)")
allp["cat"]=allp.product_id.map(ss.groupby("product_id").category_id.first())
c=allp.groupby("cat").agg(viewed=("v","size"), carted=("carted","sum"), bought=("bought","sum"), med_price=("price","median")).sort_values("viewed",ascending=False)
c["view_to_cart_%"]=(c.carted/c.viewed*100).round(1); c["cart_to_buy_%"]=(c.bought/c.carted*100).round(1); c["view_to_buy_%"]=(c.bought/c.viewed*100).round(2)
print(c.head(10).round(2).to_string())

print("\n[6] non-purchase vs purchase sessions")
f["sess_idx"]=f.sort_values("start").groupby("user").cumcount()+1
f["is_first"]=f.sess_idx==1
ps=f[f.has_p].sort_values("start").groupby("user").start.min().rename("first_p")
f=f.join(ps, on="user"); f["prior_buyer"]=(f.start>f.first_p)
g=f.groupby("has_p").agg(n=("n","size"), median_events=("n","median"), mean_events=("n","mean"), median_prod=("n_prod","median"), median_dur=("dur_min","median"), one_event_pct=("n",lambda x:(x==1).mean()*100), first_sess_pct=("is_first","mean"), prior_buyer_pct=("prior_buyer","mean"), has_cart_pct=("has_cart","mean"), has_rm_pct=("has_rm","mean"))
for col in ["first_sess_pct","prior_buyer_pct","has_cart_pct","has_rm_pct"]: g[col]=(g[col]*100).round(1)
print(g.round(1).to_string())
print("non-purchase composition:", comp[~f.has_p].value_counts(normalize=True).mul(100).round(1).head(8).to_dict())
print("conv by session order: first", round(f[f.is_first].has_p.mean()*100,2), "2nd+", round(f[~f.is_first].has_p.mean()*100,2), "prior buyer", round(f[f.prior_buyer].has_p.mean()*100,2), "2nd+ non-prior-buyer", round(f[(~f.is_first)&(~f.prior_buyer)].has_p.mean()*100,2))
print("users", f.user.nunique(), "buyers", f[f.has_p].user.nunique(), "buyer share %", round(f[f.has_p].user.nunique()/f.user.nunique()*100,2))
ab=f[f.has_cart&~f.has_p]
nxt=f[f.has_p][["user","start"]].rename(columns={"start":"pstart"})
m=ab.reset_index().merge(nxt,on="user",how="left"); m["later"]=(m.pstart>m.start)&(m.pstart<=m.start+pd.Timedelta(days=7))
print("cart-no-purchase sessions", len(ab), "-> same user purchased within 7 days %", round(m.groupby("sess").later.any().mean()*100,1))
f.to_pickle(f"{SP}/sessions.pkl")
