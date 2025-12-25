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
    df_clean['weight'] = 100.0 # High weight for ground truth
    
    # 3. Load & Merge Large Public Dataset (Augmentation)
    large_data_path = "data/cardekho_large.csv"
    if os.path.exists(large_data_path):
        print(f"✅ Integrating Large Dataset: {large_data_path}")
        try:
            df_lg = pd.read_csv(large_data_path)
            
            # Map Column Names
            # CSV: brand, model, vehicle_age, km_driven, fuel_type, transmission_type, selling_price
            df_aug = pd.DataFrame()
            df_aug['make'] = df_lg['brand']
            df_aug['model'] = df_lg['model']
            df_aug['variant'] = "Standard" # Missing in public data
            df_aug['fuel'] = df_lg['fuel_type']
            df_aug['transmission'] = df_lg['transmission_type']
            df_aug['city'] = "Mumbai" # Generic
            df_aug['km_driven'] = df_lg['km_driven']
            
            # Year derivation (Age is relative to dataset collection, assume base 2023)
            # Better to use age directly if predictor supports it, but predictor derives age from year.
            # Predictor logic: age = 2024 - year. 
            # So if dataset says age=9, year = 2024 - 9 = 2015.
            df_aug['year'] = 2024 - pd.to_numeric(df_lg['vehicle_age'], errors='coerce')
            
            df_aug['price'] = pd.to_numeric(df_lg['selling_price'], errors='coerce')
            df_aug['weight'] = 1.0 # Standard weight
            
            df_aug = df_aug.dropna(subset=['price'])
            
            # Merge
            print(f"   - User Data: {len(df_clean)} records (Weight: 100.0)")
            print(f"   - Public Data: {len(df_aug)} records (Weight: 1.0)")
            
            df_final = pd.concat([df_clean, df_aug], ignore_index=True)
            print(f"📊 Combined Training Set: {len(df_final)} records")
            
        except Exception as e:
            print(f"⚠️ Augmentation failed: {e}")
            df_final = df_clean
    else:
        df_final = df_clean
    
    # 4. Train Ensemble Models
    # Note: EnsemblePricePredictor.train() needs update to accept weights or we just duplicate rows.
    # Duplicating rows is cleaner for generic sklearn usage without changing the class signature too much.
    
    # Strategy: Oversample user data 100x (Simple & Effective)
    df_user = df_final[df_final['weight'] > 50]
    df_public = df_final[df_final['weight'] < 50]
    
    # Repeat user data 100 times
    df_user_boot = pd.concat([df_user] * 100, ignore_index=True)
    df_train_final = pd.concat([df_user_boot, df_public], ignore_index=True)
    print(f"🔢 Final Weighted Dataset Size: {len(df_train_final)} rows")
    
    predictor = EnsemblePricePredictor()
    predictor.train(df_train_final)
    print("✅ Ensemble Models retrained and saved to models/ensemble/")
    
    # 5. Train Simple ML Model (Brain v1)
    # This matches src/engine_ml.py expectations
    print("🚀 Training Simple ML Model (Brain v1)...")
    from sklearn.pipeline import Pipeline
    from sklearn.compose import ColumnTransformer
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    from sklearn.ensemble import RandomForestRegressor
    import joblib
    
    # Simple Model features: make, model, year, km, city
    X_simple = df_train_final[['make', 'model', 'year', 'km_driven', 'city']].copy()
    X_simple.columns = ['make', 'model', 'year', 'km', 'city'] # Rename
    
    # FILL NANS
    X_simple['make'] = X_simple['make'].fillna('unknown')
    X_simple['model'] = X_simple['model'].fillna('unknown')
    X_simple['city'] = X_simple['city'].fillna('Data Not Available')
    X_simple['year'] = X_simple['year'].fillna(2018)
    X_simple['km'] = X_simple['km'].fillna(50000)
    
    y_simple = df_train_final['price']
    
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
