#!/usr/bin/env python

import os
import sys
from typing import Final, List

import altair as alt
from gspread.client import Client
from gspread.models import Spreadsheet
from oauth2client.service_account import ServiceAccountCredentials as Creds
import pandas as pd


NON_FLOAT_COLS: Final = {'Date', 'Notes'}

NON_ASSET_COLS: Final = {
    'Change', 'Total', 'Student Loans', 'NFCU Credit Cards'
} | NON_FLOAT_COLS

CREDS_SCOPE: Final = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive'
]


def pasta_str_to_float(pasta_str: pd.Series) -> pd.Series:
    return pd.to_numeric(pasta_str.str.replace('[$,]', ''))


def find_creds_file() -> str:
    finanzas_dir: str = os.path.dirname(os.path.realpath(__file__))
    finanzas_dir_files: List[str] = os.listdir(finanzas_dir)
    finanzas_dir_json: List[str] = [
        f for f in finanzas_dir_files if f.endswith('.json')
    ]
    if len(finanzas_dir_json) > 1:
        raise RuntimeError(
            'more than one JSON file found; not sure which is the config.'
        )
    return finanzas_dir_json[0]


def main() -> int:
    creds: Creds = Creds.from_json_keyfile_name(
        find_creds_file(), CREDS_SCOPE
    )

    client: Client = gspread.authorize(creds)

    balance_sheet: Spreadsheet = client.open('balance-sheet').sheet1

    data: List[List[str]] = balance_sheet.get_all_values()
    # first row holds the column groupings, last row is in the future
    data = data[1:-1]
    colnames: List[str] = data.pop(0)

    pasta_df: pd.DataFrame = pd.DataFrame(data, columns=colnames)

    dollar_columns: List[str] = [
        c for c in pasta_df.columns if c not in NON_FLOAT_COLS
    ]

    pasta_df[dollar_columns] = pasta_df[dollar_columns].apply(pasta_str_to_float)
    pasta_df['Date'] = pasta_df['Date'].apply(
        pd.to_datetime, infer_datetime_format=True
    )

    alt.Chart(pasta_df).mark_line().encode(x='Date', y='Total')

    pasta_df_long: pd.DataFrame = pd.melt(
        pasta_df,
        id_vars=['Date'],
        value_vars=[c for c in pasta_df.columns if c not in NON_ASSET_COLS]
    )

    alt.Chart(pasta_df_long).mark_area().encode(
        x='Date',
        y='value',
        color='variable'
    )

    return 0


if __name__ == '__main__':
    sys.exit(main())
