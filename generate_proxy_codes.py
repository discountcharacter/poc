"""
Generate unique proxy codes for each car model in the database.
Uses the character set: A-Z, a-z, 1-9, 0 (as specified by Cars24 format)
"""
import pandas as pd
import os

# Character set for encoding (A-Z, a-z, 1-9, 0)
CHARSET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890"

def number_to_code(num):
    """Convert a number to a code using the custom character set."""
    if num == 0:
        return CHARSET[0]
    
    result = ""
    base = len(CHARSET)
    
    while num > 0:
        result = CHARSET[num % base] + result
        num = num // base
    
    return result

def generate_proxy_codes():
    """Generate proxy codes for all unique car models."""
    # Read the cars database
    csv_path = os.path.join("data", "cars_database.csv")
    df = pd.read_csv(csv_path)
    
    # Extract unique make-model combinations
    unique_models = df[['make', 'model']].drop_duplicates()
    
    # Sort alphabetically by make, then model
    unique_models = unique_models.sort_values(['make', 'model']).reset_index(drop=True)
    
    # Generate proxy codes
    unique_models['proxy_code'] = unique_models.index.map(number_to_code)
    
    # Save to CSV
    output_path = os.path.join("data", "car_model_proxy_codes.csv")
    unique_models.to_csv(output_path, index=False)
    
    print(f"✓ Generated {len(unique_models)} proxy codes")
    print(f"✓ Saved to: {output_path}")
    print(f"\nFirst 10 codes:")
    print(unique_models.head(10).to_string(index=False))
    
    return unique_models

if __name__ == "__main__":
    result = generate_proxy_codes()
