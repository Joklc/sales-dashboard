import pandas as pd
d = pd.read_parquet('kam_cache.parquet')
# Gia lap dung cach bang so sanh gom nhom
act = d.groupby('Product Line', as_index=False)['Net_KAM'].sum()
act.columns = ['PL','NS']
print("Tong NS Actual (gom theo PL):", f"{act['NS'].sum():,.0f}")
print("So Product Line:", len(act))
print(act.to_string())
