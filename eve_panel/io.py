import yaml
import json
import pandas as pd


def read_csv(f):
    df = pd.read_csv(f).dropna(axis=1, how="all")
    return df.to_dict(orient="records")


FILE_READERS = {
    "json": json.load,
    "yml": yaml.safe_load,
    "yaml": yaml.safe_load,
    "csv": read_csv,
}


def read_data_file(f, ext):
    if ext in FILE_READERS:
        data = FILE_READERS[ext](f)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            return [data]
    return []

