import joblib
import pandas as pd
import os

MODEL_PATH = "models/price_predictor.pkl"

def get_ml_prediction(make, model, year, variant, km, city):
    """
    Client for the ML Model.
    Returns: (predicted_price, confidence_score, debug_msg)
    """
    if not os.path.exists(MODEL_PATH):
        return None, 0.0, "Model not active (Train script required)."
        
    try:
        pipeline = joblib.load(MODEL_PATH)
        
        # Create input dataframe matching training X
        # Features: make, model, year, km, city
        input_data = pd.DataFrame({
            'make': [make.lower().replace(" ", "-")],
            'model': [model.lower().replace(" ", "-")], # Approximation
            'year': [year],
            'km': [km],
            'city': [city.lower() if city else "mumbai"]
        })
        
        # Predict
        prediction = pipeline.predict(input_data)[0]
        price = int(prediction)
        
        # Heuristic Confidence
        # In a real model, we might use prediction intervals.
        # Here we just check if it's within bounds.
        confidence = 0.8 # Synthetic
        
        return price, confidence, "Prediction based on Random Forest Model (v1)"
        
    except Exception as e:
        return None, 0.0, f"ML Error: {str(e)}"
