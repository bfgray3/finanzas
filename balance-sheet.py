#!/usr/bin/env python

import os
from typing import List, Set

import altair as alt
import gspread
from oauth2client.service_account import ServiceAccountCredentials as Creds
import pandas as pd


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


creds_scope: List[str] = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive'
]

creds: Creds = Creds.from_json_keyfile_name(
    find_creds_file(), creds_scope
)

gc: gspread.client.Client = gspread.authorize(creds)  # TODO: rename

balance_sheet: gspread.models.Spreadsheet = gc.open('balance-sheet').sheet1

data: List[List[str]] = balance_sheet.get_all_values()
# first row holds the column groupings, last row is in the future
data = data[1:-1]
colnames: List[str] = data.pop(0)

pasta_df: pd.DataFrame = pd.DataFrame(data, columns=colnames)

dollar_columns: List[str] = [
    c for c in pasta_df.columns if c not in {'Date', 'Notes'}
]

pasta_df[dollar_columns] = pasta_df[dollar_columns].apply(pasta_str_to_float)
pasta_df['Date'] = pasta_df['Date'].apply(
    lambda c: pd.to_datetime(c, infer_datetime_format=True)
)

alt.Chart(pasta_df).mark_line().encode(x='Date', y='Total')

non_asset_cols: Set[str] = {
    'Date', 'Notes', 'Change', 'Total', 'Student Loans', 'NFCU Credit Cards'
}

pasta_df_long = pd.melt(
    pasta_df,
    id_vars=['Date'],
    value_vars=[c for c in pasta_df.columns if c not in non_asset_cols]
)

alt.Chart(pasta_df_long).mark_area().encode(
    x='Date',
    y='value',
    color='variable'
)
