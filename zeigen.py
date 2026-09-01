import pandas as pd

d = pd.read_csv("daten/grosse5.csv")
print(d["quelle"].value_counts(dropna=False))
print()
for c in ["roic", "umsatz_cagr", "eps_cagr", "ek_cagr", "fcf_cagr"]:
    w = pd.to_numeric(d[c], errors="coerce")
    print(f"{c:12s} vorhanden {w.notna().sum():4d}   erfuellt {(w >= 10).sum():4d}")
print()
print(d["jahre"].describe())