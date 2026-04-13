# electricityinfo-nz

Python client for the WITS Market Prices API (`/api/market-prices/v1`) for New Zealand wholesale
electricity prices.

Use this documentation site for installation, usage examples, OpenAPI reference material, and
contributor guidance.

Quick facts:

- Use **`PRSL`** by default for next-24h energy forecasts.
- Use `market_type="E"` for **energy** and `market_type="R"` for **reserve**.
- Price fields are expressed in **NZD/MWh**.
- Credentials are created through the WITS Developer Portal:
  <https://developer.electricityinfo.co.nz/WITS/guides>

```{toctree}
:caption: Installation & Usage
:maxdepth: 2

installation
usage
api-spec
```

```{toctree}
:caption: Project Info
:maxdepth: 2

changelog
contributing
```

```{toctree}
:caption: API Reference
:maxdepth: 2

electricityinfo_nz
```
