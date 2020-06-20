#!/usr/bin/env python

from datetime import datetime
import os
import sys
from typing import Final, List, Tuple, Set

import altair as alt
from gspread import authorize
from gspread.client import Client
from gspread.models import Spreadsheet
from oauth2client.service_account import ServiceAccountCredentials as Creds
import pandas as pd


TODAY: str = datetime.now().strftime("%Y-%m-%d")

NON_FLOAT_COLS: Final[Set[str]] = {"Date", "Notes"}

NON_ASSET_COLS: Final[Set[str]] = {
    "Change",
    "Total",
    "Student Loans",
    "NFCU Credit Cards",
} | NON_FLOAT_COLS


def pasta_str_to_float(pasta_str: pd.Series) -> pd.Series:
    return pd.to_numeric(pasta_str.str.replace("[$,]", ""))


def find_creds_file() -> str:
    finanzas_dir: str = os.path.dirname(os.path.realpath(__file__))
    finanzas_dir_files: List[str] = os.listdir(finanzas_dir)
    finanzas_dir_json: List[str] = [
        f for f in finanzas_dir_files if f.endswith(".json")
    ]
    if len(finanzas_dir_json) > 1:
        raise RuntimeError(
            "more than one JSON file found; not sure which is the config."
        )
    return finanzas_dir_json[0]


def save_chart(chart: alt.Chart, filename: str) -> None:
    if not os.path.exists("plots"):
        os.mkdir("plots")
    chart.save(f"plots/{TODAY}-{filename}")


def get_df_from_sheets(
    sheet_name: str = "balance-sheet",
    creds_scope: Tuple[str, str] = (
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ),
) -> pd.DataFrame:
    creds: Creds = Creds.from_json_keyfile_name(find_creds_file(), creds_scope)

    client: Client = authorize(creds)

    balance_sheet: Spreadsheet = client.open(sheet_name).sheet1

    data: List[List[str]] = balance_sheet.get_all_values()
    # first row holds the column groupings, last row is in the future
    data = data[1:-1]
    colnames: List[str] = data.pop(0)

    return pd.DataFrame(data, columns=colnames)


def format_df(df: pd.DataFrame) -> pd.DataFrame:
    dollar_cols: List[str] = [c for c in df.columns if c not in NON_FLOAT_COLS]

    df[dollar_cols] = df[dollar_cols].apply(pasta_str_to_float)
    df["Date"] = df["Date"].apply(pd.to_datetime, infer_datetime_format=True)

    return df


def main() -> int:
    pasta_df: pd.DataFrame = get_df_from_sheets()

    formatted_df: pd.DataFrame = format_df(pasta_df)

    save_chart(
        alt.Chart(formatted_df).mark_line().encode(x="Date", y="Total"),
        "net-worth.html",
    )

    pasta_df_long: pd.DataFrame = pd.melt(
        formatted_df,
        id_vars=["Date"],
        value_vars=[c for c in formatted_df.columns if c not in NON_ASSET_COLS],
    )

    save_chart(
        alt.Chart(pasta_df_long)
        .mark_area()
        .encode(x="Date", y="value", color="variable"),
        "asset-breakdown.html",
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
