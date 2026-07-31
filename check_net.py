import pandas as pd
d = pd.read_parquet('kam_cache.parquet')
print(f"Tong Net_KAM toan bo : {d['Net_KAM'].sum():,.0f}")
print(f"Tong Net_FIN toan bo : {d['Net_FIN'].sum():,.0f}")
pl = d['Product Line'].astype(str).str.strip()
mask_empty = pl.isin(['', 'nan', 'None'])
print(f"So dong Product Line rong : {mask_empty.sum()}")
print(f"Net_KAM cua dong PL rong  : {d.loc[mask_empty, 'Net_KAM'].sum():,.0f}")
print("Net_KAM theo tung Product Line:")
g = d.groupby('Product Line')['Net_KAM'].sum().sort_values(ascending=False)
for k, v in g.items():
    print(f"  {str(k):<30} {v:,.0f}")
