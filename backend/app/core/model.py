import os
import joblib
import numpy as np
from tensorflow.keras.models import load_model

# Default paths (in case no args passed)
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # backend/app
DEFAULT_MODEL_PATH = os.path.join(BASE_DIR, "models", "best_lstm_model.h5")
DEFAULT_SCALER_PATH = os.path.join(BASE_DIR, "models", "scaler.save")

def predict_next_close(last60: np.ndarray, model_path: str = None, scaler_path: str = None) -> float:
    """
    Predict the next closing price given last 60 rows of features.
    
    Args:
        last60 (np.ndarray): Shape (60, 5) → [Close, High, Low, Open, Volume]
        model_path (str): Optional path to Keras model.
        scaler_path (str): Optional path to saved scaler.

    Returns:
        float: Predicted close price
    """
    if model_path is None:
        model_path = DEFAULT_MODEL_PATH
    if scaler_path is None:
        scaler_path = DEFAULT_SCALER_PATH

    # Load model and scaler
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")
    if not os.path.exists(scaler_path):
        raise FileNotFoundError(f"Scaler file not found: {scaler_path}")

    model = load_model(model_path, compile=False)
    scaler = joblib.load(scaler_path)

    # Scale input
    scaled_input = scaler.transform(last60)
    X_input = np.expand_dims(scaled_input, axis=0)  # Shape: (1, 60, 5)

    # Predict
    pred_scaled = model.predict(X_input)
    pred_close = scaler.inverse_transform(
        np.hstack([pred_scaled, np.zeros((pred_scaled.shape[0], last60.shape[1] - 1))])
    )[0, 0]

    return float(pred_close)
