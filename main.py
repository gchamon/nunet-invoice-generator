import argparse
import calendar
import csv
from datetime import datetime
import os
from typing import Any, Dict, Optional, TypedDict

from dateutil.relativedelta import relativedelta
from dateutil.rrule import MONTHLY, rrule
from jinja2 import Environment, FileSystemLoader, Template
import requests
import yaml


class ExchangeRate(TypedDict):
    """Type definition for exchange rate response.

    Attributes:
        conversion_rate: The exchange rate value
        date: The date when the rate was recorded
    """

    conversion_rate: float
    date: datetime


class Config(TypedDict):
    """
    Type definition for configuration loaded from config.yml.
    """

    token_usd: float
    fiat_usd: float
    company_name: str
    company_address: str
    service_description: str
    bank_name: str
    bank_info: str
    cardano_wallet_address: str
    invoice_filename_prefix: str
    invoice_start_month: str
    invoice_issue_day: int
    create_token_invoice: bool
    create_fiat_invoice: bool


def load_config(config_file: str) -> Config:
    """
    Load and parse configuration from a YAML file.

    Args:
        config_file: Path to the YAML configuration file

    Returns:
        Dictionary containing the configuration values matching the Config type

    Raises:
        yaml.YAMLError: If the YAML file is invalid
        KeyError: If required configuration keys are missing
    """
    with open(config_file) as config_fp:
        return yaml.safe_load(config_fp)


def diff_month(d1: datetime, d2: datetime) -> int:
    """
    Calculate the number of months between two dates.

    Args:
        d1: Later date
        d2: Earlier date

    Returns:
        Number of months between the two dates
    """
    return (d1.year - d2.year) * 12 + d1.month - d2.month


def get_template(filename: str) -> Template:
    """
    Read and return a Jinja2 template from a file.

    Creates a Jinja2 environment with the current directory as template search path
    and loads the specified template.

    Args:
        filename: Path to the template file

    Returns:
        Jinja2 Template object

    Raises:
        jinja2.TemplateNotFound: If the template file doesn't exist
    """
    env = Environment(loader=FileSystemLoader(searchpath="./"))
    return env.get_template(filename)


def write_html(filename: str, contents: str) -> None:
    """
    Write HTML contents to a file.

    Creates parent directories if they don't exist.

    Args:
        filename: Path where the HTML file should be written
        contents: HTML content to write
    """
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w") as html_fp:
        html_fp.write(contents)


def get_html_filename(
    template_name: str, invoice_date: datetime, invoice_filename_prefix: str
) -> str:
    """
    Generate the HTML filename for an invoice.

    Creates a filename in the format:
    "{template_name}/{invoice_filename_prefix}_{month}_{year}.html"

    Args:
        template_name: Name of the template to use (without extension)
        invoice_date: Date of the invoice
        invoice_filename_prefix: Prefix for the filename from config

    Returns:
        Complete path for the HTML file
    """
    formatted_invoice_date = invoice_date.strftime("%b_%y")
    return f"{template_name}/{invoice_filename_prefix}_{formatted_invoice_date}.html"


def render_html_from_template(
    template_name: str,
    invoice_date: datetime,
    invoice_filename_prefix: str,
    template_data: Dict[str, Any],
) -> None:
    """
    Render HTML invoice from a template and save it to a file.

    Loads CSS styles and combines them with template data before rendering.
    Creates output directory if it doesn't exist.

    Args:
        template_name: Name of the template to use (without extension)
        invoice_date: Date of the invoice
        invoice_filename_prefix: Prefix for the filename from config
        template_data: Dictionary containing data to be rendered in the template
    """
    with open("style.css") as style_css_fp:
        template_data["style_css"] = style_css_fp.read()

    template_filename = f"templates/{template_name}.j2"
    os.makedirs(template_name, exist_ok=True)
    html_filename = get_html_filename(
        template_name, invoice_date, invoice_filename_prefix
    )
    template = get_template(template_filename)
    html_contents = template.render(template_data)

    print(f"writing invoice to '{html_filename}'...")
    write_html(html_filename, html_contents)


def get_eur_exchange_rate(requested_date: datetime) -> ExchangeRate:
    """
    Get EUR/USD exchange rate from the European Central Bank API.

    Fetches exchange rates for a few days before the requested date to ensure
    data availability and returns the most recent rate.

    Args:
        requested_date: Date for which to get the exchange rate

    Returns:
        Dictionary containing the conversion rate and the date it was recorded

    Raises:
        requests.RequestException: If the API request fails
        ValueError: If no exchange rate data is available
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

    Fetches exchange rates for a few days before the requested date to ensure
    data availability and returns the most recent rate.

    Args:
        requested_date: Date for which to get the exchange rate

    Returns:
        Dictionary containing the conversion rate and the date it was recorded

    Raises:
        requests.RequestException: If the API request fails
        ValueError: If no exchange rate data is available
        KeyError: If the API response format is unexpected
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

    Generates two types of invoices (token and fiat) based on input parameters.
    For each month between the start date and current date:
    1. Fetches current exchange rates (USD/EUR and EUR/NTX)
    2. Calculates converted amounts
    3. Generates HTML invoices using templates

    Command line arguments:
        -c, --config: YAML config file name (default: config.yml)
        -r, --recreate: If invoice exists, recreate with fresh conversion values

    Raises:
        Exception: If requested date is before the first invoice date
        yaml.YAMLError: If the config file is invalid
        requests.RequestException: If exchange rate API requests fail
    """
    parser = argparse.ArgumentParser(
        description="Generate token and fiat invoices with currency conversions"
    )
    parser.add_argument(
        "-c", "--config", type=str, default="config.yml", required=False
    )
    parser.add_argument("-r", "--recreate", default=False, action="store_true")
    args = parser.parse_args()

    config = load_config(args.config)

    token_amount_usd = config["token_usd"]
    fiat_amount_usd = config["fiat_usd"]
    invoice_filename_prefix = config["invoice_filename_prefix"]
    first_invoice_date = datetime.strptime(config["invoice_start_month"], "%Y-%m")
    for requested_date in rrule(
        freq=MONTHLY,
        dtstart=datetime(
            first_invoice_date.year,
            first_invoice_date.month,
            config["invoice_issue_day"],
        ),
        until=datetime.now(),
    ):
        date_str = requested_date.strftime("%Y-%m-%d")

        if requested_date < first_invoice_date:
            raise Exception(
                f"{date_str} must come after first invoice from {args.first_invoice_date}"
            )

        invoice_number = diff_month(requested_date, first_invoice_date) + 1

        invoice_from_date = datetime(requested_date.year, requested_date.month, 1)
        invoice_to_date = datetime(
            requested_date.year,
            requested_date.month,
            calendar.monthrange(requested_date.year, requested_date.month)[1],
        )

        if (
            args.recreate is False
            and os.path.isfile(
                get_html_filename(
                    "token",
                    invoice_filename_prefix=invoice_filename_prefix,
                    invoice_date=requested_date,
                )
            )
            and os.path.isfile(
                get_html_filename(
                    "fiat",
                    invoice_filename_prefix=invoice_filename_prefix,
                    invoice_date=requested_date,
                )
            )
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

            if config["create_token_invoice"]:
                eur_total_token = token_amount_usd / usd_eur_exchange_rate
                ntx_total = eur_total_token / eur_ntx_exchange_rate
                print(f"\nvalues for token invoice {invoice_number}:")
                print("USD to receive in token:", token_amount_usd)
                print("EUR to receive in token:", eur_total_token)
                print("NTX to receive:", ntx_total)
                render_html_from_template(
                    "token",
                    invoice_date=requested_date,
                    invoice_filename_prefix=invoice_filename_prefix,
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
                        "company_name": config["company_name"],
                        "company_address": config["company_address"],
                        "service_description": config["service_description"],
                        "cardano_wallet_address": config["cardano_wallet_address"],
                    },
                )

            if config["create_fiat_invoice"]:
                eur_total_fiat = fiat_amount_usd / usd_eur_exchange_rate
                print(f"\nvalues for fiat invoice {invoice_number}:")
                print("USD to receive in fiat:", fiat_amount_usd)
                print("EUR to receive in token:", eur_total_fiat)
                render_html_from_template(
                    "fiat",
                    invoice_date=requested_date,
                    invoice_filename_prefix=invoice_filename_prefix,
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
                        "company_name": config["company_name"],
                        "company_address": config["company_address"],
                        "service_description": config["service_description"],
                        "bank_name": config["bank_name"],
                        "bank_info": config["bank_info"],
                    },
                )
    print("done")


if __name__ == "__main__":
    main()
