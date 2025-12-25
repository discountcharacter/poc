from src.engine_transaction import TransactionCompEngine
import pandas as pd

def test_accuracy():
    print("🚀 Starting Accuracy Verification for Transaction Engine (Rescue-v1.2.0)...")
    
    # Initialize Engine
    engine = TransactionCompEngine()
    
    # Test Cases from the user's provided data
    test_cases = [
        # {Make, Model, Year, Variant, KM, Expected Price}
        {"make": "Honda", "model": "City", "year": 2016, "variant": "S", "km": 167980, "expected": 260000},
        {"make": "MG", "model": "Hector", "year": 2022, "variant": "SHARP", "km": 17660, "expected": 1180000},
        {"make": "Maruti", "model": "Swift", "year": 2022, "variant": "VXI", "km": 23153, "expected": 500000},
        {"make": "Mahindra", "model": "Thar", "year": 2023, "variant": "LX 2WD", "km": 47715, "expected": 900000},
        {"make": "Hyundai", "model": "Santro", "year": 2007, "variant": "XO", "km": 53380, "expected": 65000}
    ]
    
    score = 0
    total = len(test_cases)
    
    print(f"\n🧪 Validating {total} Random Test Cases against Ground Truth:\n")
    print(f"{'CAR':<40} | {'REAL PRICE':<12} | {'PREDICTED':<12} | {'DELTA':<10} | {'RESULT'}")
    print("-" * 95)
    
    for case in test_cases:
        # Run Valuation
        result = engine.get_valuation(
            case['make'], case['model'], case['year'], case['variant'], case['km']
        )
        
        car_str = f"{case['year']} {case['make']} {case['model']} {case['variant']}"
        real = case['expected']
        
        if result and result['price']:
            pred = result['price']
            error = abs(pred - real)
            error_pct = (error / real) * 100
            
            status = "✅ PASS" if error_pct < 5 else "⚠️ MISS"
            if error_pct < 5: score += 1
            
            print(f"{car_str:<40} | ₹{real:<10} | ₹{int(pred):<10} | {error_pct:.1f}%      | {status}")
        else:
            print(f"{car_str:<40} | ₹{real:<10} | {'None':<10} | N/A        | ❌ NO DATA")

    print("-" * 95)
    print(f"🎯 Accuracy Score: {score}/{total} ({(score/total)*100:.0f}%) within 5% tolerance")

    if score == total:
        print("\n🏆 EXCELLENT: The Transaction Engine is perfectly replicating the provided market data.")
    else:
        print("\n⚠️ ATTENTION: Some items were missed. Check year parsing or fuzziness.")

if __name__ == "__main__":
    test_accuracy()
