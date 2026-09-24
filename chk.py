import pandas as pd
a = pd.read_parquet("data_cache.parquet")
print("Tong NS_ACT that (tat ca thang co Actual):", f"{a['NS_ACT'].sum():,.0f}")
print("Cac thang Actual co:", sorted(a["MONTH"].dropna().unique()))
f = pd.read_parquet("forecast_cache.parquet")
fc = f[f["Forecast"]=="F8+4"]
print("Tong NS_FC F8+4 (ca 12 thang):", f"{fc['NS_FC'].sum():,.0f}")
# Forecast chi cac thang Actual co
am = set(a["MONTH"].dropna().unique())
# map ten thang neu can - xem MONTH forecast
print("Cac thang Forecast:", sorted(fc["MONTH"].dropna().unique()))
