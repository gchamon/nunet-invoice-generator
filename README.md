# Invoice Generator

A Python tool for generating HTML invoices with automatic currency conversion support. The tool fetches current exchange rates for USD/EUR from the European Central Bank and EUR/NTX from CoinMarketCap to generate both fiat and token payment invoices.

## Features

- Batch creating of invoices
- Generates both fiat and token payment invoices
- Automatic currency conversion using historical exchange rates

## Installation

This project uses `uv` for package management. To install dependencies:

```bash
# Create a new virtual environment and install dependencies
uv venv --python 3.12
uv sync
```

## Usage

```bash
uv run main.py [-h] -d DATE [-i FIRST_INVOICE_DATE] [-t TOKEN_AMOUNT_USD] [-f FIAT_AMOUNT_USD]
```

### Arguments

- `-c, --config`: YAML config file name (default: config.yml)
- `-r, --recreate`: If invoice exists, recreate invoice with fresh conversion values (deafult: False)

### Examples

1. Generate invoices for a specific date with default amounts:
```bash
uv run main.py -d 2024-03-20
```

2. Generate invoices with custom amounts:
```bash
uv run main.py -d 2024-03-20 -t 2000 -f 4000
```

3. Generate invoices with a different first invoice date:
```bash
uv run main.py -d 2024-03-20 -i 2024-02-01
```

4. Generate multiple invoices for consecutive months (March to October):
```bash
for month in $(seq -f "%02g" 3 10); do
    uv run main.py -d 2024-$month-20
done
```

5. To convert the generated HTML files to PDF, use the convenience script:
```bash
./convert-html-to-pdf.sh
```

## Output

The tool generates two HTML files for each invoice date:
- Token invoice: `token/gabriel_chamon_MMM_YY.html`
- Fiat invoice: `fiat/gabriel_chamon_MMM_YY.html`

Each invoice includes:
- Invoice number (automatically incremented)
- Date range for the billing period
- Amount in original currency (USD)
- Converted amounts (EUR, NTX for token invoices)
- Exchange rates used for conversion
- Dates when exchange rates were retrieved

## Project Structure

```
├──  convert-html-to-pdf.sh
├──  main.py
├──  pyproject.toml
├──  README.md
├──  style.css
├──  templates
│   ├──  fiat.j2
│   └──  token.j2
└──  uv.lock
```

## Notes

- Exchange rates are fetched from:
  - European Central Bank API for USD/EUR rates
  - CoinMarketCap API for EUR/NTX rates
- The tool requires internet connection to fetch current exchange rates
- Generated invoices use the exchange rates from the specified date
- If the exchange rate is not available for the specified date, the tool will use the most recent available rate within the last 2 days
