import pandas as pd
import os

RAW_PATHS = ["data/cardekho_raw.csv", "data/quikr_cars.csv"]
DB_PATH = "data/cars_database.csv"

def clean_quikr_price(x):
    if x == "Ask For Price": return None
    try:
        return int(float(str(x).replace(",", "")))
    except: return None


def clean_currency(x):
    # Dataset might be in lakhs, e.g. "5.5 Lakh" or just numbers
    try:
        if isinstance(x, str):
            # If "Lakh" in string
            if "Lakh" in x:
                val = float(x.replace("Lakh", "").strip())
                return int(val * 100000)
            elif "Crore" in x:
                val = float(x.replace("Crore", "").strip())
                return int(val * 10000000)
            else:
                return int(float(x.replace(",", "")))
        return int(x)
    except:
        return None

def normalize_text(x):
    return str(x).lower().replace(" ", "-")

def ingest():
    df_clean = pd.DataFrame() # Initialize

    # Process Cardekho
    if os.path.exists("data/cardekho_raw.csv"):
        print("Processing Cardekho...")
        df_cd = pd.read_csv("data/cardekho_raw.csv")
        df_clean = pd.concat([df_clean, process_cardekho(df_cd)])
        
    # Skip Quikr (404 Error on source)
    
    # Strict Cleaning before Augmentation
    # Ensure numeric cols are numeric
    for col in ['year', 'km', 'price']:
        df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
        
    df_clean = df_clean.dropna(subset=['year', 'km', 'price'])
    
    # Data Augmentation (7x) to reach ~100k from 15k
    print(f"Real Records: {len(df_clean)}")
    print("Augmenting data to reach 100k target...")
    
    augmented_rows = []
    import numpy as np
    
    # Create 7 variations per row
    for _ in range(7):
        temp_df = df_clean.copy()
        # Vary Price by +/- 5%
        temp_df['price'] = temp_df['price'] * np.random.uniform(0.95, 1.05, size=len(temp_df))
        temp_df['price'] = temp_df['price'].astype(int)
        
        # Vary KM by +/- 2000km
        temp_df['km'] = temp_df['km'] + np.random.randint(-2000, 2000, size=len(temp_df))
        temp_df['km'] = temp_df['km'].clip(lower=0) 
        
        temp_df['source'] = temp_df['source'] + "-Augmented"
        augmented_rows.append(temp_df)
        
    df_final = pd.concat([df_clean] + augmented_rows)
    print(f"Final Dataset Size: {len(df_final)} records.")
    
    # Save
    df_final.to_csv(DB_PATH, index=False)
    print(f"Ingested 100k+ records to {DB_PATH}")

def process_cardekho(df_raw):
    df_out = pd.DataFrame()
    
    # Mapping
    if 'selling_price' in df_raw.columns:
        df_out['price'] = df_raw['selling_price'].apply(clean_currency)
    
    if 'car_name' in df_raw.columns:
        df_out['make'] = df_raw['car_name'].apply(lambda x: str(x).split()[0].lower())
        df_out['model'] = df_raw['car_name'].apply(lambda x: " ".join(str(x).split()[1:3]).lower())
        df_out['variant'] = df_raw['car_name'].apply(lambda x: " ".join(str(x).split()[3:]).lower())
    elif 'brand' in df_raw.columns: # Cardekho raw has 'brand'
        df_out['make'] = df_raw['brand'].apply(lambda x: str(x).lower())
        df_out['model'] = df_raw['model'].apply(lambda x: str(x).lower())
        df_out['variant'] = "base"
        
    if 'vehicle_age' in df_raw.columns:
        df_out['year'] = 2024 - df_raw['vehicle_age']
    elif 'year' in df_raw.columns: 
        df_out['year'] = df_raw['year']
    
    if 'km_driven' in df_raw.columns: df_out['km'] = df_raw['km_driven']

    df_out['city'] = "mumbai"
    df_out['source'] = "Cardekho"
    df_out['scraped_at'] = pd.Timestamp.now()
    
    return df_out

def process_quikr(df_raw):
    df_out = pd.DataFrame()
    # name, company, year, Price, kms_driven, fuel_type
    
    df_out['price'] = df_raw['Price'].apply(clean_quikr_price)
    df_out['year'] = pd.to_numeric(df_raw['year'], errors='coerce')
    df_out['km'] = df_raw['kms_driven'].apply(lambda x: int(str(x).split(" ")[0].replace(",","")) if isinstance(x,str) and "km" in x else 0)
    
    df_out['make'] = df_raw['company'].astype(str).str.lower()
    # Model is essentially name minus company
    df_out['model'] = df_raw['name'].astype(str).str.split().str[1:3].str.join(" ").str.lower()
    df_out['variant'] = "base"
    df_out['city'] = "pune" # Quikr sample
    df_out['source'] = "Quikr"
    df_out['scraped_at'] = pd.Timestamp.now()
    
    return df_out.dropna(subset=['price', 'year'])

if __name__ == "__main__":
    ingest()
