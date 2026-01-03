import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
import joblib
import os

# Paths
DB_PATH = "data/cars_database.csv"
MODEL_PATH = "models/price_predictor.pkl"
os.makedirs("models", exist_ok=True)

def train():
    print("Loading data...")
    if not os.path.exists(DB_PATH):
        print("No database found.")
        return
        
    df = pd.read_csv(DB_PATH)
    print(f"Loaded {len(df)} records.")
    
    # Feature Engineering
    # We predict Price based on: Make, Model, Year, KM, City
    X = df[['make', 'model', 'year', 'km', 'city']]
    y = df['price']
    
    # Preprocessing Pipeline
    categorical_features = ['make', 'model', 'city']
    numeric_features = ['year', 'km']
    
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', SimpleImputer(strategy='median'), numeric_features),
            ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_features)
        ])
    
    # Model Pipeline
    # Optimized for speed (n_jobs=-1, n_estimators=30)
    model = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('regressor', RandomForestRegressor(n_estimators=30, n_jobs=-1, random_state=42))
    ])
    
    # Train
    print("Training Random Forest Model...")
    model.fit(X, y)
    
    # Save
    joblib.dump(model, MODEL_PATH)
    print(f"Model saved to {MODEL_PATH}")
    
    # Test Prediction
    test_sample = pd.DataFrame({
        'make': ['hyundai'],
        'model': ['creta'],
        'year': [2021],
        'km': [30000],
        'city': ['hyderabad']
    })
    pred = model.predict(test_sample)[0]
    print(f"Test Prediction for 2021 Creta (30k km): ₹ {int(pred):,}")

if __name__ == "__main__":
    train()
