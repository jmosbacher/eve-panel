import yaml
import json


def read_csv(f):
    import pandas as pd
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

