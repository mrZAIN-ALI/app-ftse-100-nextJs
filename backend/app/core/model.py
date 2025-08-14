from pathlib import Path
import numpy as np
import joblib
from tensorflow.keras.models import load_model

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "models" / "best_lstm_model.h5"
SCALER_PATH = ROOT / "models" / "scaler.save"

_model = None
_scaler = None

def get_scaler():
    global _scaler
    if _scaler is None:
        _scaler = joblib.load(SCALER_PATH)
    return _scaler

def get_model():
    global _model
    if _model is None:
        _model = load_model(str(MODEL_PATH), compile=False)
    return _model

def predict_next_close(last60_rows):
    """
    last60_rows: np.array shape [60,5] ordered as [Close,High,Low,Open,Volume]
    returns float predicted_close
    """
    scaler = get_scaler()
    X_scaled = scaler.transform(last60_rows)
    X = np.expand_dims(X_scaled, axis=0)  # [1,60,5]
    y_scaled = get_model().predict(X, verbose=0)  # [1,1]
    dummy = np.zeros((1, last60_rows.shape[1]))
    dummy[0,0] = y_scaled[0,0]  # inverse only Close
    return float(scaler.inverse_transform(dummy)[0][0])
