
import pandas as pd
from src.ensemble_predictor import EnsemblePricePredictor
import os

def train_ensemble():
    data_path = "data/cars_database.csv"
    if not os.path.exists(data_path):
        print(f"❌ Data file {data_path} not found.")
        return
        
    print(f"📂 Loading data from {data_path}...")
    df = pd.read_csv(data_path)
    
    # Pre-checks for columns
    # The train method expects specific columns or will handle what it finds.
    # Let's ensure 'selling_price' exists.
    if 'selling_price' not in df.columns:
        # Some datasets use different names
        for col in ['price', 'Selling_Price']:
            if col in df.columns:
                df = df.rename(columns={col: 'selling_price'})
                break
    
    predictor = EnsemblePricePredictor()
    predictor.train(df)
    
if __name__ == "__main__":
    train_ensemble()
