from pathlib import Path
import joblib
from django.conf import settings


MODEL_FILE_MAP = {
    "breakfast": "best_model_breakfast.pkl",
    "lunch": "best_model_lunch.pkl",
    "dinner": "best_model_dinner.pkl",
}


def get_model_base_dir():
    return Path(settings.BASE_DIR) / "ml_models"


def load_prediction_artifact(meal_type: str):
    if meal_type not in MODEL_FILE_MAP:
        raise ValueError(f"지원하지 않는 meal_type 입니다: {meal_type}")

    model_path = get_model_base_dir() / MODEL_FILE_MAP[meal_type]

    if not model_path.exists():
        raise FileNotFoundError(
            f"모델 파일이 없습니다: {model_path} "
            f"(ml_models 폴더에 {MODEL_FILE_MAP[meal_type]} 파일을 넣어주세요)"
        )

    import sys
    try:
        import sklearn._loss.loss as sk_loss
        sys.modules['_loss'] = sk_loss
    except ImportError:
        pass
        
    artifact = joblib.load(model_path)

    if not isinstance(artifact, dict):
        raise ValueError(f"artifact 형식이 올바르지 않습니다: {model_path}")

    if "model" not in artifact:
        raise ValueError(f"artifact에 'model' 키가 없습니다: {model_path}")

    return artifact, MODEL_FILE_MAP[meal_type]