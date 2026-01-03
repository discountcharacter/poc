import pandas as pd
import numpy as np
from datetime import datetime
import re

class TransactionCompEngine:
    """
    Engine J: Transaction Prisms (The Real-World Truth)
    Uses actual sold car data to find comps.
    """
    
    def __init__(self, data_path="data/real_sales_data.csv"):
        self.data_path = data_path
        self.df = None
        self.load_data()

    def load_data(self):
        try:
            self.df = pd.read_csv(self.data_path)
            # Basic cleaning
            self.df['Closing Price'] = pd.to_numeric(self.df['Closing Price'], errors='coerce')
            self.df['Kms Driven'] = pd.to_numeric(self.df['Kms Driven'], errors='coerce')
            
            # Year Parsing: handle "1.2016", "11/11/2024", "2016"
            def parse_year(val):
                s = str(val)
                # Try finding a 4-digit year 1990-2029
                match = re.search(r'(199\d|20[0-2]\d)', s)
                if match:
                    return int(match.group(1))
                
                # Handle truncated years like "9.202" -> 2020 (common excel formatting issue)
                match_trunc = re.search(r'(20[0-2])\b', s) # Matches 200, 201, 202
                if match_trunc:
                     # If it's 202, assume 2020. If 201, assume 2010? No, 2019?
                     # Safest bet for "202" is 2020.
                     y_part = match_trunc.group(1)
                     if len(y_part) == 3:
                         return int(y_part + "0")
                
                return None
            
            self.df['Year'] = self.df['Yr Of Mfg'].apply(parse_year)
            # Fill missing years from Reg Date if needed
            
            self.df = self.df.dropna(subset=['Closing Price', 'Year', 'Make', 'Model'])
            print(f"✅ Loaded {len(self.df)} transaction records.")
            
        except Exception as e:
            print(f"❌ Failed to load transaction data: {e}")
            self.df = pd.DataFrame()

    def get_valuation(self, make, model, year, variant, km):
        if self.df.empty:
            return None
        
        # 1. Strict Filter: Make & Model
        # Fuzzy match model? For now strict contain
        matches = self.df[
            (self.df['Make'].str.lower() == make.lower()) & 
            (self.df['Model'].str.lower() == model.lower())
        ].copy()
        
        if matches.empty:
            return {
                'price': None,
                'confidence': 0,
                'comps': [],
                'message': "No historical transactions found for this car."
            }
            
        # 2. Similarity Scoring
        # Year diff
        matches['year_diff'] = abs(matches['Year'] - year)
        # KM diff ratio
        matches['km_diff'] = abs(matches['Kms Driven'] - km) / (km + 1)
        
        # Filter mostly relevant
        # Allow +/- 2 years
        matches = matches[matches['year_diff'] <= 2]
        
        if matches.empty:
             return {
                'price': None,
                'confidence': 0,
                'comps': [],
                'message': "No transactions found within 2 years."
            }

        # Weighting: Closer year is huge, closer KM is secondary
        # NEW STRATEGY: Exact Match Bonus
        # If we have the exact same record (based on KM and Year), we want that price to dominate.
        
        def calculate_score(row):
            base_score = 1.0
            
            # Penalize Year Diff heavily
            base_score -= (abs(row['Year'] - year) * 0.25)
            
            # Penalize KM Diff (normalized)
            km_diff_pct = abs(row['Kms Driven'] - km) / (km + 1)
            base_score -= (km_diff_pct * 0.15)
            
            # Variant Bonus
            if str(variant).lower() in str(row['Variant']).lower():
                base_score += 0.1
            
            # Exact Record Match Bonus (High Precision)
            # If KM and Year are almost identical, it's likely the same car or a perfect comp
            if abs(row['Year'] - year) == 0 and km_diff_pct < 0.05:
                base_score += 2.0 # SUPER BOOST
                
            return base_score

        matches['score'] = matches.apply(calculate_score, axis=1)
        
        # Sort by score
        matches = matches.sort_values('score', ascending=False)
        top_comps = matches.head(3)
        
        # If top match determines it's a "Perfect Match" (Score > 2.0), use only that
        if top_comps.iloc[0]['score'] > 2.0:
            top_comps = top_comps.head(1)
        
        if top_comps.empty:
             return {'price': None, 'confidence': 0, 'comps': []}
             
        # Calculate Weighted Average Price
        weighted_sum = 0
        total_score = 0
        
        comps_data = []
        for idx, row in top_comps.iterrows():
            w = max(0.1, row['score'])
            weighted_sum += row['Closing Price'] * w
            total_score += w
            comps_data.append({
                'year': int(row['Year']),
                'km': int(row['Kms Driven']),
                'price': float(row['Closing Price']),
                'variant': row['Variant'],
                'date': row['Date Of Reg'] # using Reg date as proxy for recency if transaction date unavailable
            })
            
        final_price = weighted_sum / total_score
        
        # Confidence logic
        best_score = top_comps.iloc[0]['score']
        confidence = "Low"
        if best_score > 1.5: confidence = "High" # Adjusted for bonus
        elif best_score > 0.8: confidence = "Medium"
        
        return {
            'price': final_price,
            'confidence': confidence,
            'match_score': best_score,
            'comps': comps_data,
            'count': len(matches)
        }

if __name__ == "__main__":
    eng = TransactionCompEngine()
    print(eng.get_valuation("Maruti", "Swift", 2022, "VXI", 23000))
