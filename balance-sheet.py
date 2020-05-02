#!/usr/bin/env python

import os
from typing import List

import gspread
from oauth2client.service_account import ServiceAccountCredentials as Creds
import pandas as pd


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

balance_sheet_df: pd.DataFrame = pd.DataFrame(data, columns=colnames)
print(balance_sheet_df)


# TODO: parse Date column as a date, rest except for Notes are dollars
