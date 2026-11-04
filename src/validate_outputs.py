"""Independent sanity checks for the generated integration outputs."""
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed"

def main():
    required = [
        "clickstream_country_year.csv",
        "comtrade_apparel_country_year.csv",
        "integrated_country_year.csv",
        "validation_report.json",
    ]
    missing = [name for name in required if not (OUT / name).exists()]
    if missing:
        raise FileNotFoundError(f"Run src/integrate.py first; missing: {missing}")
    click = pd.read_csv(OUT / required[0])
    trade = pd.read_csv(OUT / required[1])
    integrated = pd.read_csv(OUT / required[2])
    report = json.loads((OUT / required[3]).read_text(encoding="utf-8"))

    assert not click.duplicated(["reporter_code", "event_year"]).any()
    assert not trade.duplicated(["reporter_code", "trade_year"]).any()
    assert integrated["reporter_code"].notna().all()
    assert (click["click_events"] >= 0).all()
    assert (click["unique_sessions"] >= 0).all()
    assert (trade["apparel_export_value_usd"].dropna() >= 0).all(), "Review negative/adjustment values."
    assert integrated["trade_match_status"].isin(["matched", "no_trade_record"]).all()
    assert report["integrated_country_year_rows"] == len(integrated)
    print("PASS: output schema, key uniqueness, non-negative counts and match-status checks.")
    print(f"Integrated country-year rows: {len(integrated)}")

if __name__ == "__main__":
    main()
