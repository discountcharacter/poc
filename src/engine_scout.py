import requests
import re
import os

def fetch_market_prices(make, model, year, variant, km, api_key, cx, location, remarks=""):
    """
    Engine B: The Scout
    Fetches live listings via Google Custom Search API and extracts prices.
    Returns: (avg_price, debug_data) where debug_data is a list of found listings.
    """
    if not api_key or not cx:
        print("Scout Engine: Missing API Key or CX")
        return None, []

    # Smart Query Construction
    # Include location for better relevance
    # Limit remarks to first 3 words to avoid query overflow or confusion
    remark_keywords = " ".join(remarks.split()[:3]) if remarks else ""
    
    query = f"{year} {make} {model} {variant} price {km}km {location} {remark_keywords} site:spinny.com OR site:cars24.com OR site:cardekho.com OR site:carwale.com"
    
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": api_key,
        "cx": cx,
        "q": query,
        "num": 7 # Fetch a few more to allow better filtering
    }
    
    debug_data = [] # List of {title, price_lakh}

    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if "items" not in data:
            return None, []
            
        prices = []
        # Regex for price extraction
        price_pattern = re.compile(r"(\d+(\.\d+)?)\s*(?:Lakh|Lakhs|L)", re.IGNORECASE)
        
        for item in data["items"]:
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            full_text = snippet + " " + title
            
            matches = price_pattern.findall(full_text)
            
            for match in matches:
                try:
                    val = float(match[0])
                    # Basic sanity check
                    if 1.0 < val < 200.0: 
                        actual_price = val * 100000
                        prices.append(actual_price)
                        debug_data.append({"title": title, "raw_price": f"{val} Lakh"})
                except ValueError:
                    continue
                    
        if not prices:
            return None, debug_data
            
        # Outlier Filtering
        import statistics
        
        prices.sort()
        # Median filtering
        median_price = statistics.median(prices)
        
        filtered_prices = []
        for p in prices:
            if 0.5 * median_price <= p <= 1.5 * median_price:
                filtered_prices.append(p)
                
        if not filtered_prices:
            return int(median_price), debug_data
            
        final_avg = sum(filtered_prices) / len(filtered_prices)
        return int(final_avg), debug_data
        
    except Exception as e:
        print(f"Scout Engine Error: {e}")
        return None, [f"Error: {str(e)}"]
