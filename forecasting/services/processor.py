import warnings
from pathlib import Path

import holidays
import numpy as np
import pandas as pd
from django.conf import settings
from sklearn.cluster import KMeans

_SBERT_MODEL = None


def get_sbert_model():
    global _SBERT_MODEL
    if _SBERT_MODEL is None:
        if SentenceTransformer is None:
            raise ImportError("sentence-transformers 미설치")
        _SBERT_MODEL = SentenceTransformer("snunlp/KR-SBERT-V40K-klueNLI-augSTS")
    return _SBERT_MODEL

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None


class DataProcessor:
    def __init__(self, data_path="new_data.csv", schedule_path="학사일정.csv"):
        base_dir = Path(settings.BASE_DIR) / "data"

        self.data_path = base_dir / data_path
        self.schedule_path = base_dir / schedule_path

        if not self.data_path.exists():
            raise FileNotFoundError(f"데이터 파일이 없습니다: {self.data_path}")

        self.raw_df = pd.read_csv(self.data_path)
        self.raw_df["date"] = pd.to_datetime(self.raw_df["date"], errors="coerce")
        self.raw_df = self.raw_df.dropna(subset=["date"]).copy()
        self.raw_df["date"] = self.raw_df["date"].astype("datetime64[ns]")
        self.raw_df.sort_values("date", inplace=True)
        self.raw_df.drop_duplicates(subset=["date"], keep="last", inplace=True)
        
        self.kr_holidays = holidays.KR()
        self.menu_clusterers = {}

        print("[Init] SBERT 모델 로딩 중...")
        try:
            self.nlp_model = get_sbert_model()
        except Exception as e:
            print(f"Warning: SBERT 로드 실패. 텍스트 피처는 제외됩니다. ({e})")
            self.nlp_model = None

    def append_prediction_row(self, prediction_date, meal_type, menu_text=None):
        df = self.raw_df.copy()
        menu_col = f"{meal_type}_menu"

        new_row = {}
        for col in df.columns:
            if col == "date":
                new_row[col] = pd.to_datetime(prediction_date)
            elif col.endswith("_menu"):
                new_row[col] = ""
            else:
                new_row[col] = np.nan

        if menu_col in df.columns:
            if menu_text and str(menu_text).strip():
                new_row[menu_col] = str(menu_text).strip()
            else:
                historical = df[menu_col].dropna().astype(str)
                new_row[menu_col] = historical.iloc[-1] if not historical.empty else ""

        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"]).copy()
        df["date"] = df["date"].astype("datetime64[ns]")

        numeric_cols = [c for c in self.raw_df.columns if c != "date" and not c.endswith("_menu")]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        menu_cols = [c for c in df.columns if c.endswith("_menu")]
        for col in menu_cols:
            df[col] = df[col].fillna("").astype(str)

        df = df.sort_values("date").reset_index(drop=True)
        self.raw_df = df

    def _add_holiday_features(self, df):
        df = df.copy()
        df["weekday"] = df["date"].dt.dayofweek
        df["is_weekend"] = df["weekday"].apply(lambda x: 1 if x >= 5 else 0)
        df["is_holiday"] = df["date"].apply(lambda x: 1 if x in self.kr_holidays else 0)
        df["is_day_off"] = (df["is_weekend"] | df["is_holiday"]).astype(int)

        tomorrow_series = df["date"] + pd.Timedelta(days=1)
        df["tomorrow_is_day_off"] = tomorrow_series.apply(
            lambda x: 1 if (x.weekday() >= 5) or (x in self.kr_holidays) else 0
        )
        return df

    def _add_holiday_dday(self, df):
        df = df.copy()

        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"]).copy()
        df["date"] = df["date"].astype("datetime64[ns]")

        years = range(df["date"].dt.year.min(), df["date"].dt.year.max() + 2)

        holiday_list = []
        for holiday_date, _name in self.kr_holidays.items():
            if holiday_date.year in years:
                holiday_list.append(pd.Timestamp(holiday_date).to_datetime64())

        holiday_df = pd.DataFrame({"next_holiday": holiday_list})
        holiday_df["next_holiday"] = pd.to_datetime(holiday_df["next_holiday"], errors="coerce")
        holiday_df = holiday_df.dropna(subset=["next_holiday"]).copy()
        holiday_df["next_holiday"] = holiday_df["next_holiday"].astype("datetime64[ns]")
        holiday_df = holiday_df.sort_values("next_holiday").reset_index(drop=True)

        df = df.sort_values("date").reset_index(drop=True)

        
        print("df['date'] dtype:", df["date"].dtype)
        print("holiday_df['next_holiday'] dtype:", holiday_df["next_holiday"].dtype)

        df = pd.merge_asof(
            df,
            holiday_df,
            left_on="date",
            right_on="next_holiday",
            direction="forward",
        )

        df["d_day_holiday"] = (df["next_holiday"] - df["date"]).dt.days
        df["d_day_holiday"] = df["d_day_holiday"].fillna(365)
        df = df.drop(columns=["next_holiday"])
        return df
    

    def _get_sbert_features(self, df, target, n_clusters=20, fit_clusterer=True):
        df = df.copy()
        menu_col = f"{target}_menu"

        if self.nlp_model is None or menu_col not in df.columns:
            df["menu_cluster"] = 0
            df["emb_mean"] = 0.0
            return df

        texts = df[menu_col].fillna("").astype(str).tolist()
        embeddings = self.nlp_model.encode(texts, show_progress_bar=False)

        if fit_clusterer:
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
            df["menu_cluster"] = kmeans.fit_predict(embeddings)
            self.menu_clusterers[target] = kmeans
        else:
            if target not in self.menu_clusterers:
                raise ValueError(f"저장된 KMeans가 없습니다: target={target}")
            kmeans = self.menu_clusterers[target]
            df["menu_cluster"] = kmeans.predict(embeddings)

        df["emb_mean"] = np.mean(embeddings, axis=1)
        return df

    def _add_ts_features(self, df, target, lags=None, ewms=None):
        df = df.copy()
        lags = lags or [1, 2, 3, 7]
        ewms = ewms or [3, 7, 14]

        for lag in lags:
            df[f"lag_{lag}"] = df[target].shift(lag).bfill()
        for span in ewms:
            df[f"ewm_{span}"] = df[target].shift(1).ewm(span=span).mean().bfill()
        return df

    def _add_dday_exam(self, df):
        df = df.copy()
        df["d_day_exam"] = 365
        return df

    def get_data(self, target, fit_clusterer=True):
        df = self.raw_df.copy()
        df = self._add_holiday_features(df)
        df = self._add_holiday_dday(df)

        if target == "breakfast":
            df = self._get_sbert_features(df, target, fit_clusterer=fit_clusterer)
            df = self._add_ts_features(df, target, lags=[1, 2], ewms=[5])

        elif target == "lunch":
            df = self._add_ts_features(df, target)
            df = self._get_sbert_features(df, target, fit_clusterer=fit_clusterer)

        elif target == "dinner":
            df = self._add_dday_exam(df)
            df = self._add_ts_features(df, target, lags=[1], ewms=[7])
            df["d_day_min"] = df[["d_day_holiday", "d_day_exam"]].min(axis=1)

        else:
            raise ValueError(f"지원하지 않는 target 입니다: {target}")

        df = df.bfill().fillna(0)
        return df