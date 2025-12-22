import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import LabelEncoder
import joblib
import os
from typing import Dict, Tuple
import warnings
warnings.filterwarnings('ignore')

# Note: xgboost and lightgbm are requested by the user. 
# We import them here. In a real environment, they need to be installed.
try:
    from xgboost import XGBRegressor
    from lightgbm import LGBMRegressor
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False

class EnsemblePricePredictor:
    """
    Combines ML models with live market data for robust predictions.
    """
    
    def __init__(self):
        self.rf_model = None
        self.gb_model = None
        self.xgb_model = None
        self.lgbm_model = None
        self.label_encoders = {}
        self.models_path = "models/ensemble"
        
    def _ensure_dir(self):
        if not os.path.exists(self.models_path):
            os.makedirs(self.models_path)
            
    def train(self, df: pd.DataFrame):
        """
        Train ensemble on historical data.
        """
        self._ensure_dir()
        print("🔧 Training ensemble models...")
        
        df = df.copy()
        
        # Categorical columns to encode
        cat_cols = ['fuel', 'seller_type', 'transmission', 'owner', 'make', 'model', 'city', 'variant', 'source']
        
        target_col = None
        for col in ['selling_price', 'price', 'Selling_Price']:
            if col in df.columns:
                target_col = col
                break
        
        if target_col is None:
            print("❌ No target variable found.")
            return

        y = df[target_col].values
        X = df.drop(columns=[target_col])
        
        # Handle dates/stamps
        if 'scraped_at' in X.columns:
            X = X.drop(columns=['scraped_at'])
            
        # Encode string columns
        for col in X.columns:
            if X[col].dtype == 'object' or col in cat_cols:
                le = LabelEncoder()
                X[col] = le.fit_transform(X[col].astype(str))
                self.label_encoders[col] = le
        
        # Fill NaNs
        X = X.fillna(0)
        
        # Convert to numeric just in case
        X = X.apply(pd.to_numeric, errors='coerce').fillna(0)

        # Train models
        print(f"📊 Training on {len(X)} rows with {len(X.columns)} features: {list(X.columns)}")
        self.rf_model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
        self.rf_model.fit(X, y)
        
        self.gb_model = GradientBoostingRegressor(n_estimators=100, random_state=42)
        self.gb_model.fit(X, y)
        
        if XGB_AVAILABLE:
            try:
                self.xgb_model = XGBRegressor(n_estimators=100, random_state=42, n_jobs=-1)
                self.xgb_model.fit(X, y)
                self.lgbm_model = LGBMRegressor(n_estimators=100, random_state=42, n_jobs=-1)
                self.lgbm_model.fit(X, y)
            except Exception as e:
                print(f"⚠️ XGBoost/LightGBM training failed: {e}")
        
        self.save_models()
        self.features = list(X.columns) # Store feature order
        joblib.dump(self.features, f"{self.models_path}/features.pkl")
        print("✅ Models trained and saved.")

    def predict(self, car_data: Dict, market_data: Dict = None) -> Dict:
        """
        Generate weighted prediction.
        """
        # Load features list to ensure correct order
        if not hasattr(self, 'features'):
            if os.path.exists(f"{self.models_path}/features.pkl"):
                self.features = joblib.load(f"{self.models_path}/features.pkl")
            else:
                self.features = ['make', 'model', 'variant', 'year', 'km', 'city', 'source']

        # Prepare input row
        input_row = {}
        for feat in self.features:
            val = car_data.get(feat, "")
            # Mapping some common field differences if any
            if feat == 'km' and 'km_driven' in car_data: val = car_data['km_driven']
            
            # Encode if we have an encoder for it
            if feat in self.label_encoders:
                le = self.label_encoders[feat]
                try:
                    # Handle unseen labels by mapping to a safe default or -1
                    if str(val) in le.classes_:
                        val = le.transform([str(val)])[0]
                    else:
                        val = -1 # Or some other logic for unknown
                except:
                    val = -1
            
            input_row[feat] = val

        X_input = pd.DataFrame([input_row])[self.features]
        X_input = X_input.apply(pd.to_numeric, errors='coerce').fillna(0)

        # Model Predictions
        rf_pred = 0
        gb_pred = 0
        xgb_pred = 0
        
        if self.rf_model:
            rf_pred = self.rf_model.predict(X_input)[0]
        if self.gb_model:
            gb_pred = self.gb_model.predict(X_input)[0]
        if self.xgb_model:
            xgb_pred = self.xgb_model.predict(X_input)[0]

        # Weights: If models are near 0 (not loaded), use synthetic fallbacks or just 1.0 to avoid 0 price
        # Actually prices in the dataset are absolute, we should convert to Lakhs if they are in the millions
        def to_lakhs(val):
            return round(val / 100000, 2) if val > 1000 else val

        rf_l = to_lakhs(rf_pred)
        gb_l = to_lakhs(gb_pred)
        xgb_l = to_lakhs(xgb_pred) if xgb_pred > 0 else (rf_l + gb_l) / 2

        # Market Anchor
        market_median = market_data['statistics']['median'] if market_data and market_data.get('success') else (rf_l + gb_l) / 2
        
        # Weighted Ensemble: XGB (40%), RF (30%), GB (20%), Market (10%)
        # Adjusting weights if XGB is missing
        if self.xgb_model:
            final_price = (xgb_l * 0.40 + rf_l * 0.30 + gb_l * 0.20 + market_median * 0.10)
        else:
            final_price = (rf_l * 0.45 + gb_l * 0.35 + market_median * 0.20)
        
        # KM Adjustment (Secondary sanity check)
        km = car_data.get('km_driven', car_data.get('km', 50000))
        km_factor = 1.0
        if km < 20000: km_factor = 1.05
        elif km > 100000: km_factor = 0.90
        
        final_price *= km_factor
        
        confidence = "Medium"
        if market_data and market_data.get('success') and market_data['count'] > 5:
            confidence = "High"
        elif not self.rf_model:
            confidence = "Low (Models not loaded)"
            
        return {
            'final_price': round(final_price, 2),
            'confidence': confidence,
            'breakdown': {
                'xgboost': round(xgb_l, 2),
                'random_forest': round(rf_l, 2),
                'gradient_boosting': round(gb_l, 2),
                'market_anchor': round(market_median, 2)
            },
            'top_listings': market_data.get('listings', [])[:3] if market_data else [],
            'km_factor': km_factor
        }

    def save_models(self):
        self._ensure_dir()
        joblib.dump(self.rf_model, f"{self.models_path}/rf.pkl")
        joblib.dump(self.gb_model, f"{self.models_path}/gb.pkl")
        if XGB_AVAILABLE:
            joblib.dump(self.xgb_model, f"{self.models_path}/xgb.pkl")
    
    def load_models(self):
        if os.path.exists(f"{self.models_path}/rf.pkl"):
            self.rf_model = joblib.load(f"{self.models_path}/rf.pkl")
            self.gb_model = joblib.load(f"{self.models_path}/gb.pkl")
            print("✅ Models loaded.")
        else:
            print("⚠️ Models not found.")

if __name__ == "__main__":
    predictor = EnsemblePricePredictor()
    car_data = {'km_driven': 45000}
    print(predictor.predict(car_data))
