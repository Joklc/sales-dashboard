import pandas as pd
d = pd.read_parquet('kam_cache.parquet')
print("Tong Net_KAM:", f"{d['Net_KAM'].sum():,.0f}")
print("So dong Net_KAM bi NaN:", d['Net_KAM'].isna().sum())
print("So dong Product Line bi NaN that:", d['Product Line'].isna().sum())
# Net_KAM cua cac dong PL = NaN
print("Net_KAM cua dong PL NaN:", f"{d[d['Product Line'].isna()]['Net_KAM'].sum():,.0f}")
# Liet ke gia tri PL that (repr de thay ky tu an)
print("Cac gia tri Product Line (repr):")
for v in d['Product Line'].unique():
    print("  ", repr(v))
