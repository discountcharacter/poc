import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import LabelEncoder
import joblib
import os
from typing import Dict, List, Any
import warnings
warnings.filterwarnings('ignore')

# Note: xgboost and lightgbm are requested by the user. 
# We import them here. In a real environment, they need to be installed.
try:
    from xgboost import XGBRegressor
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False

try:
    from lightgbm import LGBMRegressor
    LGBM_AVAILABLE = True
except ImportError:
    LGBM_AVAILABLE = False

class EnsemblePricePredictor:
    """
    ENSEMBLE ML ENGINE (FIXED)
    1. Unit Standardization (Force Lakhs)
    2. Feature Engineering (Age, Age^2, KM/Year)
    3. Validation Layer (Reject absurd predictions)
    4. Fallback Logic
    """
    VERSION = "Rescue-v1.0.9"
    
    def __init__(self, models_path: str = "models/ensemble"):
        self.models_path = models_path
        self.models = {
            'rf': None,
            'gb': None,
            'xgb': None,
            'lgbm': None
        }
        self.label_encoders = {}
        self.features = []
        self.price_bounds = {'min': 0.5, 'max': 150.0}
        
    def _ensure_dir(self):
        if not os.path.exists(self.models_path):
            os.makedirs(self.models_path, exist_ok=True)

    def prepare_features(self, df: pd.DataFrame, is_training: bool = True) -> (pd.DataFrame, List[str]):
        """
        Standardized feature engineering.
        """
        df = df.copy()
        
        # 1. Clean column names
        df.columns = [c.lower() for c in df.columns]
        
        # 2. Derive Age
        current_year = 2024
        if 'year' in df.columns:
            df['age'] = current_year - df['year']
            df['age_squared'] = df['age'] ** 2
        else:
            df['age'] = 5
            df['age_squared'] = 25
            
        # 3. KM Metrics (Standardize to 'km')
        if 'km_driven' in df.columns and 'km' not in df.columns:
            df['km'] = df['km_driven']
        
        if 'km' in df.columns:
            df['km_per_year'] = df['km'] / (df['age'] + 1)
        else:
            df['km'] = 50000
            df['km_per_year'] = 10000
            
        # 4. Categorical Encoding
        cat_cols = ['make', 'model', 'fuel', 'transmission', 'city', 'variant']
        available_cat = [c for c in cat_cols if c in df.columns or not is_training]
        
        for col in cat_cols:
            if col not in df.columns:
                df[col] = "unknown" # Ensure column exists
                
            df[col] = df[col].astype(str).str.lower().str.strip()
            
            if is_training:
                le = LabelEncoder()
                df[col] = le.fit_transform(df[col])
                self.label_encoders[col] = le
            else:
                le = self.label_encoders.get(col)
                if le:
                    df[col] = df[col].map(lambda x: le.transform([x])[0] if x in le.classes_ else -1)
                else:
                    df[col] = -1
        
        # 5. Select Final Features (Must match exactly)
        # ARCHITECTURE DEFINITION: This is the ONLY source of truth for features.
        target_features = ['age', 'age_squared', 'km', 'km_per_year', 'make', 'model', 'fuel', 'transmission', 'city', 'variant']
        
        # 6. Final Stand: Manual Padding
        # This ensures every single expected column exists before we even touch reindex or indexers
        for col in target_features:
            if col not in df.columns:
                if col in ['make', 'model', 'fuel', 'transmission', 'city', 'variant']:
                    df[col] = -1 if not is_training else "unknown" # Ensure types match what encoders expect
                else:
                    df[col] = 0.0
                    
        # Debug trace for server logs
        print(f"[{self.VERSION}] prepare_features: Finalizing alignment for {target_features}")
        
        # 7. Safe Selection
        # Use reindex to force order and filter any ghosts
        try:
            df = df.reindex(columns=target_features, fill_value=0)
            df = df.fillna(0)
            return df[target_features], target_features
        except Exception as e:
            print(f"[{self.VERSION}] FATAL: Safe selection failed: {e}")
            # Absolute fallback: return just the values in correct order
            return df[target_features], target_features

    def train(self, df: pd.DataFrame):
        """
        Train with strict unit validation.
        """
        self._ensure_dir()
        df = df.copy()
        df.columns = [c.lower() for c in df.columns]
        
        # Unit Check
        target_col = None
        for col in ['price', 'selling_price']:
            if col in df.columns:
                target_col = col
                break
        
        if not target_col:
            print("❌ No target price column found.")
            return
            
        median_price = df[target_col].median()
        if median_price > 200:
            print(f"⚠️ Unit Mismatch Detected (Median: {median_price}). Converting to Lakhs.")
            df[target_col] = df[target_col] / 100000
            
        X, self.features = self.prepare_features(df, is_training=True)
        y = df[target_col].values
        
        print(f"📊 Training on {len(X)} rows with features: {self.features}")
        print(f"DEBUG: First 5 target prices (y): {y[:5]}")
        
        self.models['rf'] = RandomForestRegressor(n_estimators=100, max_depth=12, random_state=42, n_jobs=-1)
        self.models['rf'].fit(X, y)
        
        self.models['gb'] = GradientBoostingRegressor(n_estimators=100, max_depth=5, random_state=42)
        self.models['gb'].fit(X, y)
        
        if XGB_AVAILABLE:
            self.models['xgb'] = XGBRegressor(n_estimators=100, learning_rate=0.1, random_state=42)
            self.models['xgb'].fit(X, y)
            
        self.save_models()

    def save_models(self):
        self._ensure_dir()
        for name, model in self.models.items():
            if model:
                joblib.dump(model, f"{self.models_path}/{name}.pkl")
        joblib.dump(self.label_encoders, f"{self.models_path}/encoders.pkl")
        joblib.dump(self.features, f"{self.models_path}/features.pkl")

    def load_models(self):
        if not os.path.exists(self.models_path): return
        for name in self.models.keys():
            path = f"{self.models_path}/{name}.pkl"
            if os.path.exists(path):
                self.models[name] = joblib.load(path)
        
        encoder_path = f"{self.models_path}/encoders.pkl"
        if os.path.exists(encoder_path):
            self.label_encoders = joblib.load(encoder_path)
            
        feat_path = f"{self.models_path}/features.pkl"
        if os.path.exists(feat_path):
            self.features = joblib.load(feat_path)

    def predict(self, car_data: Dict, market_data: Dict = None) -> Dict:
        """
        Safe prediction with validation layer.
        """
        df_input = pd.DataFrame([car_data])
        X, _ = self.prepare_features(df_input, is_training=False)
        
        predictions = {}
        for name, model in self.models.items():
            if model:
                try:
                    raw_p = model.predict(X)[0]
                    p = float(raw_p)
                    # Validation: Reject if absurd
                    if self.price_bounds['min'] <= p <= self.price_bounds['max']:
                        predictions[name] = round(p, 2)
                    else:
                        print(f"DEBUG: {name} model predicted {p} (OUT OF BOUNDS {self.price_bounds})")
                except Exception as e:
                    print(f"⚠️ {name} prediction error: {e}")
                    
        if not predictions:
            return self._fallback_estimate(car_data)
            
        # Weighted Ensemble
        # Weights: RF (40%), GB (40%), XGB/LGB (20%)
        final_price = 0
        total_w = 0
        weights = {'rf': 0.4, 'gb': 0.4, 'xgb': 0.2, 'lgbm': 0.2}
        
        for name, p in predictions.items():
            w = weights.get(name, 0.1)
            final_price += p * w
            total_w += w
            
        final_price /= total_w
        
        # Market Adjustment
        if market_data and market_data.get('success'):
            m_median = market_data['statistics']['median']
            # Anchor to market (30% weight)
            final_price = (final_price * 0.7) + (m_median * 0.3)
            
        return {
            'final_price': round(final_price, 2),
            'breakdown': predictions,
            'confidence': 'High' if len(predictions) >= 2 else 'Medium',
            'models_used': list(predictions.keys())
        }

    def _fallback_estimate(self, car_data: Dict) -> Dict:
        """Rule-based estimate if ML fails."""
        # Very crude fallback
        year = car_data.get('year', 2018)
        age = 2024 - year
        base = 8.0 # Default segment average
        dep = (0.85) ** age
        est = base * dep
        return {
            'final_price': round(est, 2),
            'breakdown': {'fallback': round(est, 2)},
            'confidence': 'Low (Fallback)',
            'models_used': ['rule']
        }

if __name__ == "__main__":
    predictor = EnsemblePricePredictor()
    car_data = {'km_driven': 45000}
    print(predictor.predict(car_data))
