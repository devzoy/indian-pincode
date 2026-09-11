# Data License and Attribution

The **source code** of this project is licensed under the MIT License (see [LICENSE](LICENSE)).

The **data** shipped with this project is **not** MIT-licensed. It is derived from an
open government dataset and is governed by the terms below.

## Source

- **Dataset:** All India Pincode Directory (till last month)
- **Publisher:** Department of Posts, Ministry of Communications, Government of India
- **Platform:** Open Government Data (OGD) Platform India — https://www.data.gov.in
- **Catalog:** https://www.data.gov.in/catalog/all-india-pincode-directory-through-webservice
- **Resource:** https://www.data.gov.in/resource/all-india-pincode-directory-till-last-month
- **First published:** 04/12/2020
- **Update granularity:** Monthly

## License

Released under the **National Data Sharing and Accessibility Policy (NDSAP)**
(policy document: https://data.gov.in/sites/default/files/NDSAP.pdf) and licensed
under the **Government Open Data License – India (GODL-India)**:
https://www.data.gov.in/Godl

GODL-India permits both **commercial and non-commercial use** and the creation of
**derivative works**, subject to **attribution** of the source.

## Adapted work notice

The data distributed in this package is an **adapted work**. This project applies
processing to the original dataset, including:

- Whitespace normalization and canonicalization of state/UT names.
- Coordinate cleaning (parsing, bounding-box validation, coordinate-swap correction,
  outlier flagging, and per-pincode centroid computation).
- Inferred fields (e.g. backfilled state values, marked with a `state_source` field).

Anyone redistributing this data, in original or adapted form, **must retain the
attribution below**.

## Required attribution

> Department of Posts, Ministry of Communications, Government of India, 2020, All India
> Pincode Directory till last month, Open Government Data (OGD) Platform India,
> {source_updated_date}, https://www.data.gov.in/resource/all-india-pincode-directory-till-last-month.
> Released under NDSAP and licensed under Government Open Data License – India:
> https://www.data.gov.in/Godl

> **Note:** `{source_updated_date}` is a placeholder. The pipeline regenerates this
> attribution from `data/build/metadata.json` (field `source_updated_date`, formatted
> `DD/MM/YYYY`) whenever the data is refreshed. Do not hand-edit the date.
