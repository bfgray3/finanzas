#!/usr/bin/env python

import os
import sys
from contextlib import suppress
from datetime import datetime
from typing import Final, Set, Tuple

import altair as alt
import pandas as pd
from gspread import authorize
from oauth2client.service_account import ServiceAccountCredentials as Creds

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
    finanzas_dir = os.path.dirname(os.path.realpath(__file__))
    finanzas_dir_files = os.listdir(finanzas_dir)
    (creds_file,) = filter(lambda f: f.endswith(".json"), finanzas_dir_files)
    return creds_file


def save_chart(chart: alt.Chart, filename: str, subdir: str = "plots") -> None:
    if not os.path.exists(subdir):
        os.mkdir(subdir)
    else:
        for old_plot in os.listdir(subdir):
            if TODAY not in old_plot:
                with suppress(Exception):
                    os.unlink(os.path.join(subdir, old_plot))
    chart.save(f"plots/{TODAY}-{filename}")


def get_df_from_sheets(
    sheet_name: str = "balance-sheet",
    creds_scope: Tuple[str, ...] = (
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ),
) -> pd.DataFrame:
    # https://medium.com/@vince.shields913/reading-google-sheets-into-a-pandas-dataframe-with-gspread-and-oauth2-375b932be7bf
    creds = Creds.from_json_keyfile_name(find_creds_file(), creds_scope)

    client = authorize(creds)

    balance_sheet = client.open(sheet_name).sheet1

    data = balance_sheet.get_all_values()
    # first row holds the column groupings, last row is in the future
    data = data[1:-1]
    colnames = data.pop(0)

    return pd.DataFrame(data, columns=colnames)


def format_df(df: pd.DataFrame) -> pd.DataFrame:
    dollar_cols = [c for c in df.columns if c not in NON_FLOAT_COLS]

    df[dollar_cols] = df[dollar_cols].apply(pasta_str_to_float)
    df["Date"] = pd.to_datetime(df["Date"], infer_datetime_format=True)
    df.dropna(subset=["Date"], inplace=True)
    return df


def main() -> int:

    pasta_df = get_df_from_sheets()

    formatted_df = format_df(pasta_df)

    save_chart(
        alt.Chart(formatted_df).mark_line().encode(x="Date", y="Change"),
        "monthly-changes.html",
    )

    save_chart(
        alt.Chart(formatted_df).mark_line().encode(x="Date", y="Total"),
        "net-worth.html",
    )

    pasta_df_long = pd.melt(
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
