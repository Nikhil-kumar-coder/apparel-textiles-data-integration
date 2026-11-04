# Download and prepare the source files

## Source A — UCI clickstream
Official page: https://archive.ics.uci.edu/dataset/553/clickstream+data+for+online+shopping

The repository describes 165,474 sequential click records and 14 variables from an online store selling clothing for pregnant women, covering April–August 2008. Download the CSV and save it as `data/raw/clickstream.csv`. Keep the original headers; the script recognises common variants such as `session ID` and `session_id`.

The UCI page states that the dataset has no missing values. The pipeline still checks missingness because local copies may be altered or truncated.

## Source B — UN Comtrade
Portal: https://comtradeplus.un.org/
API documentation: https://uncomtrade.org/docs/un-comtrade-api/

Download annual **goods** trade data for:
- Classification: HS (select a consistent HS revision and record it)
- Period: 2008
- Trade flow: Exports
- Partner: World (partner code 0)
- Commodity codes: 61 and 62 (HS chapters; use the provider's supported code selection)
- Reporter: choose the countries that can be mapped from the UCI country field.
- Format: CSV

A public preview endpoint may be used for small requests; preview access is limited (the current documentation describes a maximum of 500 returned records). Larger or repeatable extracts may require a free account/API key or other access tier. Do not place an API key in source code or commit it to Git.

Save the downloaded file as `data/raw/comtrade_apparel.csv`. The script accepts common Comtrade column names, including `reporterCode`, `period`, `cmdCode`, `flowCode`, `primaryValue`, `TradeValue`, and `netWgt`.

## Country crosswalk (mandatory)
Create `data/raw/country_crosswalk.csv` with exactly these columns:
`clickstream_country,reporter_code`

The clickstream country field is an IP-origin country code, while Comtrade uses reporter identifiers (M49 numeric codes). These codes are not assumed to be interchangeable. Build the crosswalk by checking the UCI data description and the Comtrade country reference list. Keep only confidently mapped countries. Do not infer a country from a numeric code without checking its definition.

Example structure only (not real mappings):
```csv
clickstream_country,reporter_code
<verified UCI code A>,<verified Comtrade reporter code A>
<verified UCI code B>,<verified Comtrade reporter code B>
```

If the original country codebook is not available, record the limitation and do not fabricate mappings. The rest of the cleaning and aggregation pipeline can still be run separately; the integrated join should be treated as pending until the crosswalk is verified.

## Reproducibility log
Record download date, source URL, query filters, HS revision, file name, file size, and SHA-256 checksum for each downloaded file. Trade records can be revised by national reporting authorities; retain the exact downloaded snapshot used in an analysis.
