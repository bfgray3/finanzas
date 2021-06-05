#!/usr/bin/env python
import contextlib
import datetime
import glob
import os
import sys
import webbrowser

import altair as alt
import gspread
import numpy as np
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

TODAY = datetime.date.today().strftime("%Y-%m-%d")

NON_FLOAT_COLS = frozenset(("Date", "Notes"))

NON_ASSET_COLS = (
    frozenset(
        (
            "Change",
            "Total",
            "StudentLoans",
            "CreditCards",
        )
    )
    | NON_FLOAT_COLS
)

FINANZAS_DIR = os.path.dirname(os.path.realpath(__file__))

PLOTS_DIR = os.path.join(FINANZAS_DIR, "plots")

if not os.path.exists(PLOTS_DIR):
    try:
        os.mkdir(PLOTS_DIR)
    except OSError:
        sys.exit("Unable to make directory for plots.")

with contextlib.suppress(OSError):
    # get rid of old plots on disk
    for plot in os.listdir(PLOTS_DIR):
        if TODAY not in plot:
            os.unlink(os.path.join(PLOTS_DIR, plot))


def pasta_str_to_float(pasta_str: pd.Series) -> pd.Series:
    return pd.to_numeric(pasta_str.str.replace("[$,]", "", regex=True))


def find_creds_file() -> str:
    (creds_file,) = glob.glob(os.path.join(FINANZAS_DIR, "*.json"))
    return creds_file


def save_chart(chart: alt.Chart, filename: str) -> None:
    chart.save(os.path.join(PLOTS_DIR, f"{TODAY}-{filename}"))


def get_df_from_sheets(
    sheet_name: str = "balance-sheet",
    creds_scope: tuple[str, ...] = (
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ),
) -> pd.DataFrame:
    # https://medium.com/@vince.shields913/reading-google-sheets-into-a-pandas-dataframe-with-gspread-and-oauth2-375b932be7bf
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        find_creds_file(), creds_scope
    )

    client = gspread.authorize(creds)

    balance_sheet = client.open(sheet_name).sheet1

    data = balance_sheet.get_all_values()
    # first row holds the column groupings
    # make sure we have a date for the row
    data = [x for x in data[1:] if x[0]]
    colnames = data.pop(0)

    return pd.DataFrame(data, columns=colnames)


def format_df(df: pd.DataFrame) -> pd.DataFrame:
    dollar_cols = [c for c in df.columns if c not in NON_FLOAT_COLS]

    df[dollar_cols] = df[dollar_cols].apply(pasta_str_to_float)
    df["Date"] = pd.to_datetime(df["Date"], infer_datetime_format=True)

    previous_month = df["Total"].shift()
    df["PercentChange"] = np.where(
        previous_month >= 0, df["Total"] / previous_month - 1, np.nan
    )

    return df


def main() -> int:

    pasta_df = get_df_from_sheets()

    formatted_df = format_df(pasta_df)

    save_chart(
        alt.Chart(formatted_df)
        .mark_line()
        .encode(
            x="Date",
            y=alt.Y("PercentChange", axis=alt.Axis(format="%", title="Percent Change")),
        ),
        "monthly-net-worth-percent-change.html",
    )

    save_chart(
        alt.Chart(formatted_df)
        .mark_line()
        .encode(x="Date", y=alt.Y("Total", axis=alt.Axis(format="$", title="Amount"))),
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
        .encode(
            x="Date",
            y=alt.Y("value", axis=alt.Axis(format="$", title="Amount")),
            color=alt.Color("variable", legend=alt.Legend(title="Asset type")),
        ),
        "asset-breakdown.html",
    )

    rolling_change_long_df = pd.melt(
        formatted_df.assign(
            SixPeriodMeanChange=formatted_df["Change"].rolling(6).mean()
        ),
        id_vars=["Date"],
        value_vars=["Change", "SixPeriodMeanChange"],
    )

    save_chart(
        alt.Chart(rolling_change_long_df)
        .mark_line()
        .encode(
            x="Date",
            y=alt.Y("value", axis=alt.Axis(format="$", title="Change")),
            color=alt.Color("variable", legend=alt.Legend(title="Series")),
        ),
        "monthly-changes.html",
    )

    for plot in os.listdir(PLOTS_DIR):
        webbrowser.open(os.path.join(f"file://{PLOTS_DIR}", plot))

    return 0


if __name__ == "__main__":
    sys.exit(main())
