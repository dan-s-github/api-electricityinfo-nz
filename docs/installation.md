# Installation

Install from PyPI:

```bash
pip install electricityinfo-nz
```

The package requires **Python 3.9+**.

## Authentication

The API uses OAuth2 client credentials.

To get credentials:

1. Sign up in the WITS Developer Portal.
2. Create an application under **My Apps**.
3. Copy the generated **Client ID** and **Client Secret**.
4. Enable the API services your application needs.

Official guide:

- <https://developer.electricityinfo.co.nz/WITS/guides>

You can pass credentials directly:

```python
from electricityinfo_nz import MarketPricesClient

client = MarketPricesClient(
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET",
)
```

Or use environment variables:

```bash
export WITS_CLIENT_ID=YOUR_CLIENT_ID
export WITS_CLIENT_SECRET=YOUR_CLIENT_SECRET
```

```python
from electricityinfo_nz import MarketPricesClient

client = MarketPricesClient()
```
