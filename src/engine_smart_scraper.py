from playwright.sync_api import sync_playwright
import re
import statistics
import time
from typing import List, Dict

class SmartCarScraper:
    """
    Intelligent scraper using Playwright to bypass anti-bot measures.
    Extracts multiple listings and applies statistical cleaning.
    """
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        
    def _get_page_content(self, url: str) -> str:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            try:
                page.goto(url, wait_until="networkidle", timeout=30000)
                time.sleep(2) # Allow dynamic content
                content = page.content()
                browser.close()
                return content
            except Exception as e:
                print(f"❌ Scraper error for {url}: {e}")
                browser.close()
                return ""

    def scrape_carwale_listings(self, make: str, model: str, year: int, 
                                city: str, max_results: int = 10) -> List[Dict]:
        city_slug = city.lower().replace(' ', '-')
        make_slug = make.lower().replace(' ', '-')
        model_slug = model.lower().replace(' ', '-')
        url = f"https://www.carwale.com/used/{make_slug}-{model_slug}-cars-in-{city_slug}/"
        
        print(f"🔍 Scraping CarWale: {url}")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            page = browser.new_page(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
            listings = []
            
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=20000)
                page.wait_for_selector('[data-track-label="ListingCard"], .o-cpnuEd', timeout=10000)
                
                cards = page.query_selector_all('[data-track-label="ListingCard"], .o-cpnuEd')
                for card in cards[:max_results]:
                    text = card.inner_text()
                    
                    # Parse price
                    price_match = re.search(r'₹\s*([\d.]+)\s*Lakh', text, re.IGNORECASE)
                    if not price_match: continue
                    price = float(price_match.group(1))
                    
                    # Parse Year
                    year_match = re.search(r'\b(20\d{2})\b', text)
                    f_year = int(year_match.group(1)) if year_match else 0
                    
                    # Parse KM
                    km_match = re.search(r'([\d,]+)\s*km', text, re.IGNORECASE)
                    km = int(km_match.group(1).replace(',', '')) if km_match else 0
                    
                    if f_year and abs(f_year - year) > 1: continue # Tolerance
                    
                    listings.append({
                        'source': 'CarWale',
                        'price': price,
                        'year': f_year,
                        'km': km,
                        'title': text.split('\n')[0]
                    })
                browser.close()
            except Exception as e:
                print(f"⚠️ CarWale fail: {e}")
                browser.close()
            return listings

    def scrape_spinny_listings(self, make: str, model: str, year: int,
                               city: str, max_results: int = 10) -> List[Dict]:
        make_s = make.lower().replace(' ', '-')
        model_s = model.lower().replace(' ', '-')
        city_s = city.lower().replace(' ', '-')
        url = f"https://www.spinny.com/buy-used-{make_s}-{model_s}-cars-in-{city_s}/"
        
        print(f"🔍 Scraping Spinny: {url}")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            page = browser.new_page()
            listings = []
            try:
                page.goto(url, wait_until="networkidle", timeout=20000)
                cards = page.query_selector_all('[data-testid="car-card"], .car-card')
                for card in cards[:max_results]:
                    text = card.inner_text()
                    
                    price_m = re.search(r'₹\s*([\d.]+)\s*(?:Lakh|L)', text, re.IGNORECASE)
                    if not price_m: continue
                    price = float(price_m.group(1))
                    
                    year_m = re.search(r'\b(20\d{2})\b', text)
                    f_year = int(year_m.group(1)) if year_m else 0
                    
                    km_m = re.search(r'([\d,]+)\s*km', text, re.IGNORECASE)
                    km = int(km_m.group(1).replace(',', '')) if km_m else 0
                    
                    if f_year and abs(f_year - year) > 1: continue
                    
                    listings.append({
                        'source': 'Spinny',
                        'price': price,
                        'year': f_year,
                        'km': km,
                        'title': text.split('\n')[0]
                    })
                browser.close()
            except Exception as e:
                print(f"⚠️ Spinny fail: {e}")
                browser.close()
            return listings

    def get_market_data(self, make: str, model: str, year: int, 
                       fuel: str, city: str, km_driven: int) -> Dict:
        all_listings = []
        all_listings.extend(self.scrape_carwale_listings(make, model, year, city))
        all_listings.extend(self.scrape_spinny_listings(make, model, year, city))
        
        # IQR Outlier filter
        if not all_listings:
            return {'success': False, 'message': 'No listings found', 'count': 0}
            
        prices = [l['price'] for l in all_listings]
        if len(prices) >= 4:
            q1, q3 = statistics.quantiles(prices, n=4)[0], statistics.quantiles(prices, n=4)[2]
            iqr = q3 - q1
            lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            filtered = [l for l in all_listings if lower <= l['price'] <= upper]
        else:
            filtered = all_listings
            
        filtered.sort(key=lambda x: abs(x['km'] - km_driven))
        
        f_prices = [l['price'] for l in filtered]
        
        return {
            'success': True,
            'count': len(filtered),
            'listings': filtered[:5],
            'statistics': {
                'median': round(statistics.median(f_prices), 2),
                'mean': round(statistics.mean(f_prices), 2),
                'min': min(f_prices),
                'max': max(f_prices)
            }
        }

if __name__ == "__main__":
    s = SmartCarScraper(headless=True)
    print(s.get_market_data("Maruti", "Swift", 2020, "Petrol", "Mumbai", 35000))

if __name__ == "__main__":
    scraper = SmartCarScraper()
    print(scraper.get_market_data("Hyundai", "Creta", 2020, "Petrol", "Mumbai", 35000))
