import requests
from bs4 import BeautifulSoup
import pandas as pd
import random
import time
import os
import re

# Database Path
DB_PATH = "data/cars_database.csv"

# Configuration
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
]

TARGET_CITIES = ["mumbai", "delhi", "bangalore", "hyderabad", "chennai", "pune"]
TARGET_MAKES = ["maruti-suzuki", "hyundai", "tata", "mahindra", "honda", "toyota", "kia", "mg"]

def get_random_header():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }

def clean_price(price_str):
    """Converts price text (e.g., '₹ 10.5 Lakh') to integer."""
    try:
        # Regex for "10.5 Lakh" or "10.5"
        matches = re.findall(r"(\d+(\.\d+)?)\s*(?:Lakh|Lakhs|L)?", price_str, re.IGNORECASE)
        if matches:
            val = float(matches[0][0])
            if 1.0 < val < 200.0: # Sanity check (1L to 2Cr)
                return int(val * 100000)
    except:
        pass
    return None

def clean_km(km_str):
    try:
        return int(re.sub(r"\D", "", km_str))
    except:
        return 0

def scrape_carwale_city_make(city, make):
    """
    Scrapes a specific City + Make page on CarWale.
    URL Pattern: https://www.carwale.com/used/cars-in-{city}/?masking=1&sc=-1&so=-1&pn=1&make={make_id} (Hard to guess IDs)
    Better Pattern: https://www.carwale.com/used/{city}/{make}-cars/
    """
    url = f"https://www.carwale.com/used/{city}/{make}-cars/"
    print(f"Harvesting: {url}...")
    
    try:
        response = requests.get(url, headers=get_random_header(), timeout=10)
        if response.status_code != 200:
            print(f"Failed to fetch {url}: {response.status_code}")
            return []
            
        soup = BeautifulSoup(response.text, 'html.parser')
        listings = []
        
        # This selector is heuristic; CarWale structure is complex.
        # We look for listing blocks. Class names are obfuscated usually.
        # We look for links that contain regex patterns.
        
        links = soup.find_all('a', href=True)
        for link in links:
            href = link['href']
            title = link.get_text(" ", strip=True)
            
            # Simple heuristic: if title contains Year and "Used", it's a card
            if "used" in href and any(str(y) in title for y in range(2010, 2026)):
                # Extract details from title: "2020 Hyundai Creta SX..."
                
                # 1. Year
                year_match = re.search(r"\b(20\d{2})\b", title)
                if not year_match: continue
                year = int(year_match.group(1))
                
                # 2. Price (Try to find price in the parent block)
                parent = link.find_parent('div')
                full_text = parent.get_text(" ", strip=True) if parent else title
                
                price = clean_price(full_text)
                if not price: continue
                
                # 3. KM (Regex for "10,000 km")
                km = 0
                km_match = re.search(r"(\d{1,3}(?:,\d{3})*)\s*km", full_text, re.IGNORECASE)
                if km_match:
                    km = clean_km(km_match.group(1))
                
                # 4. Model (Remove Make and Year from title)
                model_str = title.lower().replace(str(year), "").replace(make.replace("-", " "), "").strip()
                # Use first 2 words as Model estimate
                model_parts = model_str.split()
                model = " ".join(model_parts[:2]) if len(model_parts) >= 2 else model_str
                
                listings.append({
                    "make": make,
                    "model": model,
                    "year": year,
                    "variant": "Base", # Hard to parse without deep link
                    "km": km,
                    "city": city,
                    "price": price,
                    "source": "CarWale",
                    "scraped_at": pd.Timestamp.now()
                })
        
        print(f"  -> Found {len(listings)} listings.")
        return listings
        
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return []

def main():
    print("Starting Car Data Harvester...")
    
    all_data = []
    
    # Load existing to avoid duplicates? For now just append.
    
    for city in TARGET_CITIES:
        for make in TARGET_MAKES:
            new_data = scrape_carwale_city_make(city, make)
            all_data.extend(new_data)
            
            # Polite Sleep
            sleep_time = random.uniform(2.0, 5.0)
            time.sleep(sleep_time)
            
    if all_data:
        df = pd.DataFrame(all_data)
        # Append to CSV
        if os.path.exists(DB_PATH):
            df.to_csv(DB_PATH, mode='a', header=False, index=False)
        else:
            df.to_csv(DB_PATH, mode='w', header=True, index=False)
            
        print(f"Successfully harvested {len(all_data)} records to {DB_PATH}")
    else:
        print("No data harvested. Possible IP block or DOM change.")

if __name__ == "__main__":
    main()
