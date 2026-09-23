import pandas as pd
a = pd.read_parquet("data_cache.parquet")
f = pd.read_parquet("forecast_cache.parquet")
fc = f[f["Forecast"]=="F8+4"]
FAMILY_MAP = {
    "CANISTER VAC CL":"CANISTER VACUUM CLEANER","CONVIVIAL COOKG":"CONVIVIAL COOKING",
    "DAILY ING.PROCESSOR":"DAILY INGREDIENTS PROCESSOR",
    "ELECT.PRES.CK&MULTI":"ELECTRIC PRESSURE COOKER & MULTICOOKER",
    "HANDSTICK VAC.CLEAN.":"HANDSTICK VACUUM CLEANER",
    "P&P FIXED HANDLES AL":"P&P FIXED HANDLES ALUMINIUM",
    "P&P FIXED HANDLES OT":"P&P FIXED HANDLES OTHER",
    "P&P FIXED HANDLES ST":"P&P FIXED HANDLES STAINLESS STEEL",
    "P&P STACKABLES ALU":"P&P STACKABLES ALUMINIUM",
    "P&P STACKABLES ST":"P&P STACKABLES STAINLESS STEEL",
    "PRESSURE COOKER":"PRESSURE COOKER","SP PART & OTHER":"SPARE PARTS & OTHER",
    "TOOL, GAD&MAN.FD PRE":"TOOLS, GADGETS & MANUAL FOOD PREPARATION",
}
def nf(s):
    s=" ".join(str(s).strip().upper().split())
    return FAMILY_MAP.get(s,s)
ak=set(a["Family Level 2"].dropna().map(nf).unique())
fk=set(fc["Family Level 2"].dropna().map(nf).unique())
print("=== Family ACTUAL khong khop F8+4 ===")
for x in sorted(ak-fk):
    ns=a[a["Family Level 2"].map(nf)==x]["NS_ACT"].sum()
    print(f"  '{x}'  NS={ns:,.0f}")
print()
print("=== Family co trong F8+4 ===")
for x in sorted(fk): print(f"  '{x}'")
