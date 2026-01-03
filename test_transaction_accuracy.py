from src.engine_transaction import TransactionCompEngine
import pandas as pd
import random

def test_accuracy():
    print("🚀 Starting Comprehensive Accuracy Verification (35 Random Samples)...")
    
    # Initialize Engine
    engine = TransactionCompEngine()
    
    # Load Real Data
    try:
        df = pd.read_csv("data/real_sales_data.csv")
        # Clean price column
        df['Closing Price'] = pd.to_numeric(df['Closing Price'], errors='coerce')
        df = df.dropna(subset=['Closing Price'])
    except Exception as e:
        print(f"Failed to load CSV: {e}")
        return

    # Select 35 Random Samples (or all if less than 35)
    test_samples = df.sample(n=min(35, len(df))).to_dict('records')
    
    score = 0
    total = len(test_samples)
    
    print(f"\n🧪 Validating {total} Real Transaction Records:\n")
    print(f"{'CAR':<50} | {'REAL PRICE':<12} | {'PREDICTED':<12} | {'DELTA':<10} | {'RESULT'}")
    print("-" * 105)
    
    for case in test_samples:
        # Extract fields
        make = str(case.get('Make', ''))
        model = str(case.get('Model', ''))
        variant = str(case.get('Variant', ''))
        km = int(case.get('Kms Driven', 0))
        
        # Parse Year (handle floats like 1.2016 -> 2016)
        raw_year = str(case.get('Yr Of Mfg', ''))
        year = None
        import re
        match = re.search(r'(199\d|20[0-2]\d)', raw_year)
        if match:
            year = int(match.group(1))
        
        if not year:
            print(f"Skipping {make} {model} due to invalid year: {raw_year}")
            total -= 1
            continue

        real_price = float(case['Closing Price'])
        
        # Run Valuation
        result = engine.get_valuation(make, model, year, variant, km)
        
        car_str = f"{year} {make} {model} {variant[:15]}"
        
        if result and result['price']:
            pred = result['price']
            error = abs(pred - real_price)
            error_pct = (error / real_price) * 100
            
            # Strict 1% tolerance for "Exact Match" check
            status = "✅ PASS" if error_pct < 1.0 else "⚠️ MISS"
            if error_pct < 1.0: score += 1
            
            print(f"{car_str:<50} | ₹{int(real_price):<10} | ₹{int(pred):<10} | {error_pct:.1f}%      | {status}")
        else:
            print(f"{car_str:<50} | ₹{int(real_price):<10} | {'None':<10} | N/A        | ❌ NO DATA")

    print("-" * 105)
    print(f"🎯 Accuracy Score: {score}/{total} ({(score/total)*100:.0f}%) within 1% tolerance")

    if score == total:
        print("\n🏆 EXCELLENT: The Transaction Engine is perfectly replicating the provided market data.")
    else:
        print("\n⚠️ ATTENTION: Some items were missed. Check date parsing or fuzzy logic.")

if __name__ == "__main__":
    test_accuracy()
