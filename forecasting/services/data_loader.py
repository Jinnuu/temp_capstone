from pathlib import Path

import pandas as pd
from django.conf import settings


def get_data_dir():
    return Path(settings.BASE_DIR) / "data"


def load_new_data():
    data_path = get_data_dir() / "new_data.csv"
    if not data_path.exists():
        raise FileNotFoundError(f"new_data.csv 파일이 없습니다: {data_path}")

    df = pd.read_csv(data_path)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").drop_duplicates(subset=["date"], keep="last").reset_index(drop=True)
    return df


def load_weather_data():
    weather_path = get_data_dir() / "weather_data.csv"
    if not weather_path.exists():
        return pd.DataFrame()

    df = pd.read_csv(weather_path)
    df["date"] = pd.to_datetime(df["date"])
    return df


def load_schedule_data():
    """
    학사일정.csv가 없으면 빈 DataFrame 반환.
    날짜 컬럼이 엑셀 serial number일 수도 있으므로 처리.
    """
    schedule_path = get_data_dir() / "학사일정.csv"
    if not schedule_path.exists():
        return pd.DataFrame(columns=["date", "event"])

    df = pd.read_csv(schedule_path)

    if "날짜" not in df.columns:
        return pd.DataFrame(columns=["date", "event"])

    raw_date = df["날짜"]

    # 엑셀 일련번호 처리
    if pd.api.types.is_numeric_dtype(raw_date):
        df["date"] = pd.to_datetime(raw_date, unit="D", origin="1899-12-30")
    else:
        df["date"] = pd.to_datetime(raw_date, errors="coerce")

    event_col = "일정" if "일정" in df.columns else None
    if event_col:
        df["event"] = df[event_col].astype(str)
    else:
        df["event"] = ""

    df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    return df[["date", "event"]]