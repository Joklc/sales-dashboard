import pandas as pd
a = pd.read_parquet("data_cache.parquet")
f = pd.read_parquet("forecast_cache.parquet")
fc = f[f["Forecast"]=="F8+4"]
def norm(s):
    return str(s).strip().upper().replace("&","AND")
act_fam = set(a["Family Level 2"].dropna().map(norm).unique())
fc_fam  = set(fc["Family Level 2"].dropna().map(norm).unique())
missing = act_fam - fc_fam
print("Family ben ACTUAL khong khop FORECAST:")
for x in sorted(missing):
    ns = a[a["Family Level 2"].map(norm)==x]["NS_ACT"].sum()
    print(f"  {x:<40} NS_ACT={ns:,.0f}")
