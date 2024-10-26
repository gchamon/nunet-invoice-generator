import argparse
import calendar
import csv
import os
from datetime import datetime
from typing import Any, Dict, TypedDict

import requests
from dateutil.relativedelta import relativedelta
from jinja2 import Template


class ExchangeRate(TypedDict):
    """Type definition for exchange rate response"""

    conversion_rate: float
    date: datetime


def get_template(filename: str) -> Template:
    """
    Read and return a Jinja2 template from a file.

    Args:
        filename: Path to the template file

    Returns:
        Jinja2 Template object
    """
    with open(filename) as fp:
        return Template(fp.read())


def write_html(filename: str, contents: str) -> None:
    """
    Write HTML contents to a file.

    Args:
        filename: Path where the HTML file should be written
        contents: HTML content to write
    """
    with open(filename, "w") as html_fp:
        html_fp.write(contents)


def get_html_filename(template_name: str, invoice_date: datetime) -> str:
    """
    Gets html filename from template name and requested date.
    For instance, "token" and a invoice date of "2024-10-20" will result in
    "token/{first_name}_{last_name}_Oct_2024.html"

    Args:
        template_name: Name of the template to use (without extension)
        invoice_date: Date of the invoice

    Returns:
        filename used for writing the html file
    """

    formatted_invoice_date = invoice_date.strftime("%b_%y")
    return f"{template_name}/gabriel_chamon_{formatted_invoice_date}.html"


def render_html_from_template(
    template_name: str, invoice_date: datetime, template_data: Dict[str, Any]
) -> None:
    """
    Render HTML invoice from a template and save it to a file.

    Args:
        template_name: Name of the template to use (without extension)
        invoice_date: Date of the invoice
        template_data: Dictionary containing data to be rendered in the template
    """
    with open("style.css") as style_css_fp:
        template_data["style_css"] = style_css_fp.read()

    template_filename = f"templates/{template_name}.j2"
    os.makedirs(template_name, exist_ok=True)
    html_filename = get_html_filename(template_name, invoice_date)
    template = get_template(template_filename)
    html_contents = template.render(template_data)

    print(f"writing invoice to '{html_filename}'...")
    write_html(html_filename, html_contents)


def get_eur_exchange_rate(requested_date: datetime) -> ExchangeRate:
    """
    Get EUR/USD exchange rate from the European Central Bank API.

    Args:
        requested_date: Date for which to get the exchange rate

    Returns:
        Dictionary containing the conversion rate and the date it was recorded
    """
    start_date = requested_date - relativedelta(days=2)
    url = "https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A?format=csvdata&startPeriod={start}&endPeriod={end}".format(
        start=start_date.strftime("%Y-%m-%d"),
        end=requested_date.strftime("%Y-%m-%d"),
    )
    response = requests.get(url)
    rates = [r for r in csv.DictReader(response.text.splitlines(), delimiter=",")]
    rate = rates[-1]
    return {
        "conversion_rate": float(rate["OBS_VALUE"]),
        "date": datetime.strptime(rate["TIME_PERIOD"], "%Y-%m-%d"),
    }


def get_ntx_exchange_rate(requested_date: datetime) -> ExchangeRate:
    """
    Get EUR/NTX exchange rate from CoinMarketCap API.

    Args:
        requested_date: Date for which to get the exchange rate

    Returns:
        Dictionary containing the conversion rate and the date it was recorded
    """
    start_date = requested_date - relativedelta(days=2)
    url = "https://api.coinmarketcap.com/data-api/v3.1/cryptocurrency/historical?id=13198&convertId=2790&timeStart={start}&timeEnd={end}&interval=1d".format(
        start=int(start_date.timestamp()), end=int(requested_date.timestamp())
    )
    response = requests.get(url)
    rate = response.json()["data"]["quotes"][-1]
    return {
        "conversion_rate": rate["quote"]["open"],
        "date": datetime.strptime(rate["timeOpen"].split("T")[0], "%Y-%m-%d"),
    }


def main() -> None:
    """
    Main function to generate invoices with currency conversions.

    This script generates two types of invoices (token and fiat) based on input parameters.
    It fetches current exchange rates and generates HTML invoices using templates.

    Command line arguments:
        -d, --date: Invoice date (YYYY-MM-DD format)
        -i, --first-invoice-date: Date of first invoice (default: 2024-03-01)
        -t, --token-amount-usd: Amount in USD for token payment (default: 1500)
        -f, --fiat-amount-usd: Amount in USD for fiat payment (default: 3500)

    Raises:
        Exception: If requested date is before the first invoice date
    """
    parser = argparse.ArgumentParser(
        description="Generate token and fiat invoices with currency conversions"
    )
    parser.add_argument(
        "-d", "--date", required=True, type=str, help="Invoice date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "-i",
        "--first-invoice-date",
        required=False,
        type=str,
        default="2024-03-01",
        help="Date of first invoice (default: 2024-03-01)",
    )
    parser.add_argument(
        "-t",
        "--token-amount-usd",
        required=False,
        type=int,
        default=1500,
        help="Amount in USD for token payment (default: 1500)",
    )
    parser.add_argument(
        "-f",
        "--fiat-amount-usd",
        required=False,
        type=int,
        default=3500,
        help="Amount in USD for fiat payment (default: 3500)",
    )
    parser.add_argument(
        "-r", "--recreate", action="store_true", default=False, required=False
    )
    args = parser.parse_args()

    token_amount_usd = args.token_amount_usd
    fiat_amount_usd = args.fiat_amount_usd
    date_str = args.date
    requested_date = datetime.strptime(date_str, "%Y-%m-%d")
    first_invoice_date = datetime.strptime(args.first_invoice_date, "%Y-%m-%d")

    if requested_date < first_invoice_date:
        raise Exception(
            f"{date_str} must come after first invoice from {args.first_invoice_date}"
        )

    invoice_number = relativedelta(requested_date, first_invoice_date).months + 1

    invoice_from_date = datetime(requested_date.year, requested_date.month, 1)
    invoice_to_date = datetime(
        requested_date.year,
        requested_date.month,
        calendar.monthrange(requested_date.year, requested_date.month)[1],
    )

    if (
        args.recreate is False
        and os.path.isfile(get_html_filename("token", invoice_date=requested_date))
        and os.path.isfile(get_html_filename("fiat", invoice_date=requested_date))
    ):
        print(f"Invoices exist for {date_str} exists. Skipping...")
    else:
        print(f"retrieving exchange rates for {date_str}...")
        usd_eur_exchange_rate_obj = get_eur_exchange_rate(requested_date)
        eur_ntx_exchange_rate_obj = get_ntx_exchange_rate(requested_date)
        usd_eur_exchange_rate = usd_eur_exchange_rate_obj["conversion_rate"]
        eur_ntx_exchange_rate = eur_ntx_exchange_rate_obj["conversion_rate"]

        print("usd to eur exchange rate:", usd_eur_exchange_rate)
        print("eur to ntx exchange rate:", eur_ntx_exchange_rate)

        eur_total_token = token_amount_usd / usd_eur_exchange_rate
        ntx_total = eur_total_token / eur_ntx_exchange_rate
        print("\nvalues for token invoice:")
        print("USD to receive in token:", token_amount_usd)
        print("EUR to receive in token:", eur_total_token)
        print("NTX to receive:", ntx_total)
        render_html_from_template(
            "token",
            invoice_date=requested_date,
            template_data={
                "invoice_number": invoice_number,
                "amount_usd": token_amount_usd,
                "amount_eur": eur_total_token,
                "amount_ntx": ntx_total,
                "date": requested_date.strftime("%d-%b-%Y"),
                "invoice_from_date": invoice_from_date.strftime("%d-%b-%Y"),
                "invoice_to_date": invoice_to_date.strftime("%d-%b-%Y"),
                "usd_eur_rate": usd_eur_exchange_rate,
                "eur_ntx_rate": eur_ntx_exchange_rate,
                "fiat_rate_date": usd_eur_exchange_rate_obj["date"].strftime(
                    "%d-%b-%y"
                ),
                "token_rate_date": eur_ntx_exchange_rate_obj["date"].strftime(
                    "%d-%b-%y"
                ),
            },
        )

        eur_total_fiat = fiat_amount_usd / usd_eur_exchange_rate
        print("\nvalues for fiat invoice:")
        print("USD to receive in fiat:", fiat_amount_usd)
        print("EUR to receive in token:", eur_total_fiat)
        render_html_from_template(
            "fiat",
            invoice_date=requested_date,
            template_data={
                "invoice_number": invoice_number,
                "amount_usd": fiat_amount_usd,
                "amount_eur": eur_total_fiat,
                "date": requested_date.strftime("%d-%b-%Y"),
                "invoice_from_date": invoice_from_date.strftime("%d-%b-%Y"),
                "invoice_to_date": invoice_to_date.strftime("%d-%b-%Y"),
                "usd_eur_rate": usd_eur_exchange_rate,
                "fiat_rate_date": usd_eur_exchange_rate_obj["date"].strftime(
                    "%d-%b-%y"
                ),
            },
        )
        print("done")


if __name__ == "__main__":
    main()
