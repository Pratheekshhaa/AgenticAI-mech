import os
import pandas as pd
import re

def load_all_datasets(data_dir="data"):
    datasets = []

    for file in os.listdir(data_dir):
        if file.lower() == "datasett.csv":
            continue

        path = os.path.join(data_dir, file)

        try:
            if file.endswith(".csv"):
                df = pd.read_csv(path)
            elif file.endswith(".xlsx"):
                df = pd.read_excel(path)
            else:
                continue

            df["__text__"] = df.astype(str).agg(" ".join, axis=1)
            datasets.append(df)

        except:
            pass

    if not datasets:
        raise RuntimeError("No datasets loaded")

    return datasets


def extract_keywords(text):
    return re.findall(r"[a-zA-Z]{3,}", text.lower())


def build_rca_signal(user_text, datasets):
    keywords = extract_keywords(user_text)
    signals = set()

    for df in datasets:
        for k in keywords:
            if df["__text__"].str.contains(k, case=False, na=False).any():
                signals.add(k)

    if not signals:
        return "Use general mechanical reasoning."

    return "Focus on components related to: " + ", ".join(list(signals)[:6])
