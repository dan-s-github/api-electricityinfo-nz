# electricityinfo-nz

<p align="center">
  <a href="https://github.com/dan-s-github/api-electricityinfo-nz/actions/workflows/ci.yml?query=branch%3Amain">
    <img src="https://img.shields.io/github/actions/workflow/status/dan-s-github/api-electricityinfo-nz/ci.yml?branch=main&label=CI&logo=github&style=flat-square" alt="CI Status">
  </a>
  <a href="https://codecov.io/gh/dan-s-github/api-electricityinfo-nz">
    <img src="https://img.shields.io/codecov/c/github/dan-s-github/api-electricityinfo-nz.svg?logo=codecov&logoColor=fff&style=flat-square" alt="Test coverage percentage">
  </a>
</p>
<p align="center">
  <a href="https://github.com/astral-sh/uv">
    <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json" alt="uv">
  </a>
  <a href="https://github.com/astral-sh/ruff">
    <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff">
  </a>
  <a href="https://github.com/pre-commit/pre-commit">
    <img src="https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white&style=flat-square" alt="pre-commit">
  </a>
</p>
<p align="center">
  <a href="https://pypi.org/project/electricityinfo-nz/">
    <img src="https://img.shields.io/pypi/v/electricityinfo-nz.svg?logo=python&logoColor=fff&style=flat-square" alt="PyPI Version">
  </a>
  <img src="https://img.shields.io/pypi/pyversions/electricityinfo-nz.svg?style=flat-square&logo=python&amp;logoColor=fff" alt="Supported Python versions">
  <img src="https://img.shields.io/pypi/l/electricityinfo-nz.svg?style=flat-square" alt="License">
</p>

---

**Documentation**: <a href="https://github.com/dan-s-github/api-electricityinfo-nz/blob/main/docs/index.md" target="_blank">https://github.com/dan-s-github/api-electricityinfo-nz/blob/main/docs/index.md</a>

**Source Code**: <a href="https://github.com/dan-s-github/api-electricityinfo-nz" target="_blank">https://github.com/dan-s-github/api-electricityinfo-nz</a>

---

Python client for the WITS Market Prices API (`/api/market-prices/v1`) for New Zealand wholesale
electricity prices.

## Installation

Install this via pip:

`pip install electricityinfo-nz`

Requires **Python 3.9+**.

## Quick start

Create credentials in the WITS Developer Portal:

1. Sign up in the portal.
2. Create an application under **My Apps**.
3. Copy the generated **Client ID** and **Client Secret**.
4. Enable the API services your application needs.

Official guide: <https://developer.electricityinfo.co.nz/WITS/guides>

```python
from electricityinfo_nz import MarketPricesClient

client = MarketPricesClient(
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET",
)

result = client.get_schedule_prices(
    schedule="PRSL",
    market_type="E",
    nodes=["OTA2201"],
    forward=48,
)
```

For a next-24h forecast, use **`PRSL`** by default. Use `market_type="E"` for **energy** prices
and `market_type="R"` for **reserve** prices. Prices are expressed in **NZD/MWh**.

More detailed guides:

- Installation: <https://github.com/dan-s-github/api-electricityinfo-nz/blob/main/docs/installation.md>
- Usage: <https://github.com/dan-s-github/api-electricityinfo-nz/blob/main/docs/usage.md>
- OpenAPI spec: <https://github.com/dan-s-github/api-electricityinfo-nz/blob/main/docs/market-prices.yaml>
- Contributing: <https://github.com/dan-s-github/api-electricityinfo-nz/blob/main/CONTRIBUTING.md>

## Contributors ✨

Thanks goes to these wonderful people ([emoji key](https://allcontributors.org/docs/en/emoji-key)):

<!-- prettier-ignore-start -->
<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- markdownlint-disable -->
<!-- markdownlint-enable -->
<!-- ALL-CONTRIBUTORS-LIST:END -->
<!-- prettier-ignore-end -->

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors)
specification. Contributions of any kind welcome!

## Credits

This package wraps the Electricity Info NZ / WITS Market Prices API for the New Zealand wholesale
electricity market and is guided by the official WITS Developer Portal documentation.
