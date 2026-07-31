import pandas as pd
d = pd.read_parquet('kam_cache.parquet')
missing = d[d['Product Line'].isna()]
out = (missing.groupby(['Item code','Item name'], as_index=False)
       .agg(Net_KAM=('Net_KAM','sum'), Qty=('Qty','sum'))
       .sort_values('Net_KAM', ascending=False))
out.to_excel('Item_chua_map_CMMF.xlsx', index=False)
print(f"Co {out['Item code'].nunique()} Item chua map, xuat ra: Item_chua_map_CMMF.xlsx")
print(out.head(20).to_string())
