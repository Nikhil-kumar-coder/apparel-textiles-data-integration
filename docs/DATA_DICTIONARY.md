# Data dictionary and integration design

## Source A: clickstream event table
| Canonical field | Meaning | Type | Rule |
|---|---|---|---|
| event_year | Calendar year | integer | Parse numeric; retain valid years |
| event_month | Month number | integer | 1–12 |
| event_day | Day of month | integer | Validate after date construction |
| event_date | Event date | date | Construct from year/month/day |
| click_order | Click sequence within session | integer | Positive integer where possible |
| country_source | Original IP-origin country code | string | Preserve leading zeros; never assume it is M49 |
| session_id | Session identifier | string | Preserve as string |
| main_category | Main product category | string | Trim and normalise whitespace/case |
| clothing_model | Product/model code | string | Preserve as string |
| colour | Product colour | string | Trim and normalise whitespace/case |
| page_location | Image position on page | string | Preserve as categorical |
| price_usd | Product price in USD | numeric | Coerce invalid values to null; inspect ranges |

UCI reports 14 variables; the table above lists core fields used in the integration. Additional source fields should be retained in the raw archive and documented before being discarded.

## Source B: UN Comtrade trade table
| Canonical field | Meaning | Type | Rule |
|---|---|---|---|
| reporter_code | Reporting economy identifier | string | Preserve code and crosswalk |
| trade_year | Reporting year | integer | Must match requested period |
| hs_code | Harmonized System commodity code | string | Retain original code and revision |
| flow | Export/import flow | string | Filter to exports for this exercise |
| partner_code | Partner economy | string | Filter to World (0) |
| trade_value_usd | Reported trade value | numeric | Use the selected USD value field; document field |
| net_weight_kg | Net weight | numeric | Optional; do not replace missing with zero |

## Common analytical grain
`country/reporter × year`

Clickstream events are aggregated to:
- click_events
- unique_sessions
- unique_models
- mean_listed_price_usd (only where price is valid)

Comtrade is aggregated to:
- apparel_export_value_usd (sum of HS 61 and 62 export values)
- apparel_export_weight_kg (sum where reported)

## Join logic
`clickstream_country_year.reporter_code = comtrade_country_year.reporter_code`
and `event_year = trade_year`.

The country crosswalk is an explicit bridge table. The join is a country-year contextual comparison, not a person-level or transaction-level linkage. The data sources are historically mismatched in scope and should not be interpreted causally.

## Null semantics
- Missing trade value is not automatically zero.
- A missing country mapping is `unmapped`, not a guessed country.
- Missing price stays null and is excluded from price averages.
- A zero click count is meaningful only after a complete country-year universe is defined.
