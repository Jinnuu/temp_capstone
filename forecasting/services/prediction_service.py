import numpy as np
import pandas as pd

from forecasting.models import AttendancePrediction
from .model_loader import load_prediction_artifact
from .processor import DataProcessor


def run_attendance_prediction(prediction_date, meal_type, menu_text=None):
    artifact, model_file_name = load_prediction_artifact(meal_type)

    
    print("=== ARTIFACT CHECK ===")
    print("artifact keys:", list(artifact.keys()))
    print("artifact target:", artifact.get("target"))
    print("artifact feature_columns length:", len(artifact.get("feature_columns", [])))
    print("======================")

    model = artifact["model"]
    saved_kmeans = artifact.get("menu_kmeans")
    feature_columns = artifact.get("feature_columns", [])

    processor = DataProcessor(data_path="new_data.csv")
    processor.append_prediction_row(
        prediction_date=prediction_date,
        meal_type=meal_type,
        menu_text=menu_text,
    )

    # breakfast / lunch 에서는 저장된 KMeans를 사용
    if saved_kmeans is not None:
        processor.menu_clusterers[meal_type] = saved_kmeans

    processed = processor.get_data(meal_type, fit_clusterer=False)

    target_row = processed[processed["date"] == pd.to_datetime(prediction_date)].tail(1)
    if target_row.empty:
        raise ValueError("예측 대상 날짜 행을 찾지 못했습니다.")

    drop_cols = [meal_type, "date"] + [c for c in processed.columns if "_max" in c]
    X_input = target_row.drop(columns=drop_cols, errors="ignore").select_dtypes(include=[np.number])

    # 학습 시 저장된 컬럼 순서에 맞추기
    if feature_columns:
        missing_cols = [col for col in feature_columns if col not in X_input.columns]
        for col in missing_cols:
            X_input[col] = 0

        extra_cols = [col for col in X_input.columns if col not in feature_columns]
        if extra_cols:
            X_input = X_input.drop(columns=extra_cols, errors="ignore")

        X_input = X_input.reindex(columns=feature_columns, fill_value=0)

    print("=== FEATURE CHECK ===")
    print("meal_type:", meal_type)
    print("X_input columns:", X_input.columns.tolist())
    print("artifact feature_columns:", feature_columns)
    print("X_input shape:", X_input.shape)
    print("=====================")
    
    raw_prediction = model.predict(X_input)[0]
    predicted_count = max(0, int(round(raw_prediction)))

    menu_col = f"{meal_type}_menu"
    menu_text_used = ""
    if menu_col in target_row.columns:
        menu_text_used = str(target_row.iloc[0][menu_col])

    prediction = AttendancePrediction.objects.create(
        prediction_date=prediction_date,
        meal_type=meal_type,
        predicted_count=predicted_count,
        model_name=model_file_name,
        input_features={
            "feature_columns": X_input.columns.tolist(),
            "feature_values": X_input.iloc[0].to_dict(),
            "menu_text_used": menu_text_used,
            "artifact_target": artifact.get("target"),
            "best_model_name": artifact.get("best_model_name"),
            "test_mae": artifact.get("test_mae"),
        },
    )
    return prediction