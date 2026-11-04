"""
Country-year integration of apparel e-commerce clickstream and UN Comtrade data.
The join is contextual (country x year), not a person- or order-level match.
"""
from pathlib import Path
import json
import re
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

def normalise_name(value):
    return re.sub(r"[^a-z0-9]+", "", str(value).strip().lower())

def find_column(df, candidates, required=True):
    lookup = {normalise_name(c): c for c in df.columns}
    for candidate in candidates:
        key = normalise_name(candidate)
        if key in lookup:
            return lookup[key]
    if required:
        raise ValueError(f"Missing expected column. Tried: {candidates}. Found: {list(df.columns)}")
    return None

def numeric(series):
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False), errors="coerce")

def load_clickstream(path):
    df = pd.read_csv(path, dtype=str)
    cols = {
        "year": find_column(df, ["year"]),
        "month": find_column(df, ["month"]),
        "day": find_column(df, ["day"]),
        "session_id": find_column(df, ["session ID", "session_id", "sessionid"]),
        "country": find_column(df, ["country"]),
        "model": find_column(df, ["page 2 (clothing model)", "page2", "clothing model"]),
        "category": find_column(df, ["page 1 (main category)", "page1", "main category"], required=False),
        "price": find_column(df, ["price", "price usd"], required=False),
    }
    out = pd.DataFrame()
    out["event_year"] = numeric(df[cols["year"]]).astype("Int64")
    out["event_month"] = numeric(df[cols["month"]]).astype("Int64")
    out["event_day"] = numeric(df[cols["day"]]).astype("Int64")
    out["session_id"] = df[cols["session_id"]].astype("string").str.strip()
    out["country_source"] = df[cols["country"]].astype("string").str.strip()
    out["clothing_model"] = df[cols["model"]].astype("string").str.strip()
    out["main_category"] = df[cols["category"]].astype("string").str.strip() if cols["category"] else pd.NA
    out["price_usd"] = numeric(df[cols["price"]]) if cols["price"] else pd.NA
    out["event_date"] = pd.to_datetime(
        dict(year=out["event_year"], month=out["event_month"], day=out["event_day"]),
        errors="coerce"
    )
    before = len(out)
    out = out.drop_duplicates()
    exact_duplicates_removed = before - len(out)
    out = out.dropna(subset=["event_year", "session_id", "country_source", "event_date"])
    out["event_year"] = out["event_year"].astype(int)
    out["country_source"] = out["country_source"].str.strip()
    out["session_id"] = out["session_id"].str.strip()
    out["clothing_model"] = out["clothing_model"].str.strip()
    out.loc[out["price_usd"] < 0, "price_usd"] = pd.NA
    return out, exact_duplicates_removed

def load_comtrade(path):
    df = pd.read_csv(path, dtype=str)
    c_reporter = find_column(df, ["reporterCode", "reporter code", "reporter"])
    c_period = find_column(df, ["period", "year"])
    c_hs = find_column(df, ["cmdCode", "commodity code", "hs code"])
    c_flow = find_column(df, ["flowCode", "flow code", "trade flow"], required=False)
    c_partner = find_column(df, ["partnerCode", "partner code", "partner"], required=False)
    c_value = find_column(df, ["primaryValue", "trade value", "tradevalue", "primary value"])
    c_weight = find_column(df, ["netWgt", "net weight", "netweight"], required=False)
    out = pd.DataFrame({
        "reporter_code": df[c_reporter].astype("string").str.strip(),
        "trade_year": numeric(df[c_period]).astype("Int64"),
        "hs_code": df[c_hs].astype("string").str.strip(),
        "trade_value_usd": numeric(df[c_value]),
    })
    out["flow"] = df[c_flow].astype("string").str.strip() if c_flow else "UNSPECIFIED"
    out["partner_code"] = df[c_partner].astype("string").str.strip() if c_partner else "UNSPECIFIED"
    out["net_weight_kg"] = numeric(df[c_weight]) if c_weight else pd.NA
    out = out.dropna(subset=["reporter_code", "trade_year", "hs_code"])
    out["trade_year"] = out["trade_year"].astype(int)
    out = out[out["hs_code"].str.startswith(("61", "62"))]
    if c_flow:
        out = out[out["flow"].str.lower().isin(["x", "export", "exports"])]
    if c_partner:
        out = out[out["partner_code"].isin(["0", "World", "WORLD"])]
    return out

def main():
    click_path = RAW / "clickstream.csv"
    trade_path = RAW / "comtrade_apparel.csv"
    crosswalk_path = RAW / "country_crosswalk.csv"
    for path in (click_path, trade_path, crosswalk_path):
        if not path.exists():
            raise FileNotFoundError(f"Required input missing: {path}. See docs/DOWNLOAD_GUIDE.md")

    click, duplicate_count = load_clickstream(click_path)
    trade = load_comtrade(trade_path)
    crosswalk = pd.read_csv(crosswalk_path, dtype=str)
    required = {"clickstream_country", "reporter_code"}
    if not required.issubset(crosswalk.columns):
        raise ValueError(f"Crosswalk must contain columns: {sorted(required)}")
    crosswalk = crosswalk[list(required)].dropna().drop_duplicates()
    if crosswalk["clickstream_country"].duplicated().any():
        raise ValueError("A clickstream country maps to multiple reporter codes. Resolve ambiguity first.")
    if crosswalk["reporter_code"].duplicated().any():
        print("WARNING: multiple clickstream codes map to one reporter; verify this is intentional.")

    click = click.merge(crosswalk, left_on="country_source", right_on="clickstream_country", how="left", validate="many_to_one")
    click_summary = click.groupby(["reporter_code", "event_year"], dropna=False).agg(
        click_events=("session_id", "size"),
        unique_sessions=("session_id", "nunique"),
        unique_models=("clothing_model", "nunique"),
        mean_listed_price_usd=("price_usd", "mean"),
        unmapped_click_events=("reporter_code", lambda s: s.isna().sum())
    ).reset_index()
    click_summary.to_csv(OUT / "clickstream_country_year.csv", index=False)

    trade_summary = trade.groupby(["reporter_code", "trade_year"]).agg(
        apparel_export_value_usd=("trade_value_usd", "sum"),
        apparel_export_weight_kg=("net_weight_kg", "sum"),
        trade_records=("hs_code", "size"),
    ).reset_index()
    trade_summary.to_csv(OUT / "comtrade_apparel_country_year.csv", index=False)

    integrated = click_summary[click_summary["reporter_code"].notna()].merge(
        trade_summary, left_on=["reporter_code", "event_year"],
        right_on=["reporter_code", "trade_year"], how="left", validate="one_to_one",
        indicator=True
    )
    integrated["trade_match_status"] = integrated["_merge"].map(
        {"both": "matched", "left_only": "no_trade_record"}
    )
    integrated = integrated.drop(columns=["_merge"])
    integrated.to_csv(OUT / "integrated_country_year.csv", index=False)

    report = {
        "clickstream_rows_after_cleaning": int(len(click)),
        "exact_duplicate_rows_removed": int(duplicate_count),
        "unmapped_click_events": int(click["reporter_code"].isna().sum()),
        "trade_rows_after_filtering": int(len(trade)),
        "integrated_country_year_rows": int(len(integrated)),
        "matched_country_year_rows": int((integrated["trade_match_status"] == "matched").sum()),
        "unmatched_country_year_rows": int((integrated["trade_match_status"] == "no_trade_record").sum()),
        "checks": {
            "unique_clickstream_country_year": bool(not click_summary.duplicated(["reporter_code", "event_year"]).any()),
            "unique_trade_country_year": bool(not trade_summary.duplicated(["reporter_code", "trade_year"]).any()),
            "negative_trade_values": int((trade["trade_value_usd"] < 0).sum()),
            "negative_prices": int((click["price_usd"] < 0).sum()),
        },
        "note": "Country-year contextual integration only; not a transaction-level or causal link."
    }
    (OUT / "validation_report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(json.dumps(report, indent=2, default=str))

if __name__ == "__main__":
    main()
