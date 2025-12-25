import pandas as pd
import numpy as np
from src.ensemble_predictor import EnsemblePricePredictor
import os

def train_new_models():
    print("🚀 Starting Ensemble Model Retraining (Rescue-v1.2.4)...")
    
    # 1. Load Real Data
    data_path = "data/real_sales_data.csv"
    if not os.path.exists(data_path):
        print(f"❌ Error: {data_path} not found.")
        return

    try:
        df = pd.read_csv(data_path)
        print(f"✅ Loaded {len(df)} records from {data_path}")
    except Exception as e:
        print(f"❌ Failed to load CSV: {e}")
        return

    # 2. Map Columns to Training Format
    # The CSV has 'Closing Price', predictor expects 'price' or 'selling_price'
    # CSV has 'Yr Of Mfg', predictor expects 'year' (handled in prepare_features via derived logic, but let's be explicit)
    
    # We need to clean the dataframe to match what EnsemblePricePredictor expects
    # It expects: make, model, variant, year (or age derived), km_driven (or km), fuel, transmission
    
    df_clean = pd.DataFrame()
    df_clean['make'] = df['Make']
    df_clean['model'] = df['Model']
    df_clean['variant'] = df['Variant']
    df_clean['fuel'] = df['Fuel Type']
    df_clean['transmission'] = df['Transmission']
    df_clean['city'] = "Hyderabad" # Defaulting since training data doesn't have city, but live app uses it. 
                                    # This is a weakness, but better than random.
    df_clean['km_driven'] = df['Kms Driven']
    
    # Parse Year
    import re
    def parse_year(val):
        s = str(val)
        match = re.search(r'(199\d|20[0-2]\d)', s)
        if match:
            return int(match.group(1))
        # Handle "9.202" -> 2020
        match_trunc = re.search(r'(20[0-2])\b', s)
        if match_trunc:
             y_part = match_trunc.group(1)
             if len(y_part) == 3:
                 return int(y_part + "0")
        return 2018 # Median fallback

    df_clean['year'] = df['Yr Of Mfg'].apply(parse_year)
    
    # Parse Price
    df_clean['price'] = pd.to_numeric(df['Closing Price'], errors='coerce')
    df_clean = df_clean.dropna(subset=['price'])
    
    print(f"📊 Training Data Sample:\n{df_clean.head()}")
    
    # 3. Train Ensemble Models
    predictor = EnsemblePricePredictor()
    predictor.train(df_clean)
    print("✅ Ensemble Models retrained and saved to models/ensemble/")
    
    # 4. Train Simple ML Model (Brain v1)
    # This matches src/engine_ml.py expectations
    print("🚀 Training Simple ML Model (Brain v1)...")
    from sklearn.pipeline import Pipeline
    from sklearn.compose import ColumnTransformer
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    from sklearn.ensemble import RandomForestRegressor
    import joblib
    
    # Simple Model features: make, model, year, km, city
    X_simple = df_clean[['make', 'model', 'year', 'km_driven', 'city']].copy()
    X_simple.columns = ['make', 'model', 'year', 'km', 'city'] # Rename
    
    # FILL NANS
    X_simple['make'] = X_simple['make'].fillna('unknown')
    X_simple['model'] = X_simple['model'].fillna('unknown')
    X_simple['city'] = X_simple['city'].fillna('Data Not Available')
    X_simple['year'] = X_simple['year'].fillna(2018)
    X_simple['km'] = X_simple['km'].fillna(50000)
    
    y_simple = df_clean['price']
    
    # Preprocessor
    preprocessor = ColumnTransformer(
        transformers=[
            ('cat', OneHotEncoder(handle_unknown='ignore'), ['make', 'model', 'city']),
            ('num', StandardScaler(), ['year', 'km'])
        ]
    )
    
    pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('regressor', RandomForestRegressor(n_estimators=100, random_state=42))
    ])
    
    pipeline.fit(X_simple, y_simple)
    
    # Save
    if not os.path.exists("models"): os.makedirs("models")
    joblib.dump(pipeline, "models/price_predictor.pkl")
    print("✅ Simple ML Model saved to models/price_predictor.pkl")

if __name__ == "__main__":
    train_new_models()
