"""Real persisted estimators; no mocked model or feature processor."""
import math
import warnings
import numpy as np
import pandas as pd
from datetime import date
from django.test import TestCase
from forecasting.services.model_loader import load_prediction_artifact
from forecasting.services.prediction_service import run_attendance_prediction


class PredictionCompatibilityTests(TestCase):
    def test_three_persisted_estimators_load_and_predict(self):
        for meal in ['breakfast', 'lunch', 'dinner']:
            with self.subTest(meal=meal):
                artifact, _ = load_prediction_artifact(meal)
                columns = artifact.get('feature_columns') or list(getattr(artifact['model'], 'feature_names_in_', []))
                if not columns:
                    columns = [f'feature_{i}' for i in range(artifact['model'].n_features_in_)]
                self.assertTrue(columns)
                data = pd.DataFrame(np.zeros((1, len(columns))), columns=columns)
                result = artifact['model'].predict(data)
                self.assertTrue(math.isfinite(float(result[0])))
                print(f'ARTIFACT_SMOKE {meal}: {type(artifact["model"]).__name__}, {len(columns)} features, prediction={float(result[0])}')

    def test_offline_prediction_pipeline_persists_three_meals(self):
        for meal in ['breakfast', 'lunch', 'dinner']:
            with self.subTest(meal=meal):
                prediction = run_attendance_prediction(date(2026,10,15),meal,menu_text='쌀밥 미역국 제육볶음')
                self.assertIsNotNone(prediction.pk)
                self.assertGreaterEqual(prediction.predicted_count,0)
                self.assertTrue(prediction.input_features['feature_columns'])
                print(f'OFFLINE_PIPELINE {meal}: prediction={prediction.predicted_count}')
