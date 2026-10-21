import re
import pandas as pd


SEED = 42


def normalize(s):
    """Masque ce qui change d'une ligne à l'autre sans changer son sens."""
    s = re.sub(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", "<UUID>", s)
    s = re.sub(r"\b[0-9a-fA-F]{16,}\b", "<HEX>", s)
    s = re.sub(r"\d+(\.\d+)*", "<N>", s)
    return s


def load(path):
    df = pd.read_csv(path).dropna(subset=["log_message", "target_label"])
    df["groupe"] = df["log_message"].map(normalize)
    return df.reset_index(drop=True)