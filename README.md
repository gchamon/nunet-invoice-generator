# Invoice Generator

A Python tool for generating HTML invoices with automatic currency conversion support.
The tool fetches current exchange rates for USD/EUR from the European Central Bank and EUR/NTX from CoinMarketCap to generate both fiat and token payment invoices.

## Features

- Automatic generation of invoices for multiple months
- Generates both fiat and token payment invoices
- Automatic currency conversion using historical exchange rates
- Configuration-based setup

## Installation

This project uses `uv` for package management. See <https://github.com/astral-sh/uv?tab=readme-ov-file#installation> for details.

To install dependencies:

```bash
# Create a new virtual environment and install dependencies
uv venv --python 3.12
uv python pin 3.12
uv sync
```

## Configuration

Copy the example configuration file and modify it according to your needs:

```bash
cp config.yml.dist config.yml
```

The configuration file (`config.yml`) supports the following options:

```yaml
token_usd: 1000                 # Amount in USD for token invoices
fiat_usd: 2000                  # Amount in USD for fiat invoices
company_name: |                 # Company name to appear on invoices
  Your
  Company
  Name
company_address: "Full Address" # Company address for invoices
service_description: "Service Description" # Description of services rendered
bank_name: "Bank Name"          # Bank name for fiat invoices
bank_info: |                    # Bank details for fiat invoices
  Branch Address: XXXXX
  IBAN: XXXXX
  SWIFT: XXXXX
cardano_wallet_address: addr1xxx # Cardano wallet address for token invoices
invoice_filename_prefix: your_name  # prefix to use to compose the filenames
invoice_start_month: "2024-01"   # First month to generate invoices (YYYY-MM)
invoice_issue_day: 20            # Day of month for invoice dates
create_token_invoice: true       # Whether to generate token invoices
create_fiat_invoice: true        # Whether to generate fiat invoices
```

## Usage

```bash
uv run main.py [-h] [-c CONFIG] [-r]
```

### Arguments

- `-c, --config`: YAML config file name (default: config.yml)
- `-r, --recreate`: If invoice exists, recreate invoice with fresh conversion values (default: False)

### Examples

1. Generate all invoices using default config file:
```bash
uv run main.py
```

2. Generate invoices using a custom config file:
```bash
uv run main.py --config custom_config.yml
```

3. Regenerate all invoices with fresh exchange rates:
```bash
uv run main.py --recreate
```

4. To convert the generated HTML files to PDF, use the convenience script:
```bash
./convert-html-to-pdf.sh
```

## Output

The tool generates two HTML files for each month between the start date and current date:
- Token invoice: `token/YOUR_NAME_MMM_YY.html`
- Fiat invoice: `fiat/YOUR_NAME_MMM_YY.html`

Each invoice includes:
- Invoice number (automatically incremented)
- Date range for the billing period
- Amount in original currency (USD)
- Converted amounts (EUR, NTX for token invoices)
- Exchange rates used for conversion
- Dates when exchange rates were retrieved

## Project Structure

```
├──  convert-html-to-pdf.sh
├──  main.py
├──  pyproject.toml
├──  README.md
├──  style.css
├──  config.yml.dist
├──  templates
│   ├──  fiat.j2
│   └──  token.j2
└──  uv.lock
```

## Notes

- Exchange rates are fetched from:
  - European Central Bank API for USD/EUR rates
  - CoinMarketCap API for EUR/NTX rates
- The tool requires internet connection to fetch current exchange rates
- Generated invoices use the exchange rates from the specified date
- If the exchange rate is not available for the specified date, the tool will use the most recent available rate within the last 2 days
- The tool automatically generates invoices for all months between the start date specified in config.yml and the current date
