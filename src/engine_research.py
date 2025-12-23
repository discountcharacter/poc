import re
import statistics
import time
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
try:
    from playwright.sync_api import sync_playwright
    from src.engine_smart_scraper import PLAYWRIGHT_READY
except ImportError:
    sync_playwright = None
    PLAYWRIGHT_READY = False

class MarketResearchEngine:
    """
    Intelligent market research with strict filtering.
    Ported from the user's provided 'FixedMarketSearch' system.
    """
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.min_listings_required = 2 

    def _safe_launch(self, playwright):
        """Helper to safely launch browser with circuit breaker."""
        # Using the global flag from smart_scraper to synchronize failures
        from src.engine_smart_scraper import PLAYWRIGHT_READY as PR_GLOBAL
        if not PR_GLOBAL:
            return None
        try:
            return playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--no-sandbox',
                    '--disable-gpu',
                    '--disable-dev-shm-usage',
                    '--disable-setuid-sandbox'
                ]
            )
        except Exception as e:
            print(f"❌ MarketResearch Launch Failed: {e}")
            # We don't set PR_GLOBAL = False here because we can't easily write to it,
            # but usually it's set by smart_scraper which runs earlier.
            return None

    def search_specific_car(self, make: str, model: str, year: int, 
                           city: str = "hyderabad") -> Dict:
        """
        Search with STRICT validation - only return exact matches
        """
        print(f"\n🔍 RESEARCHING: {year} {make} {model} in {city}")
        
        all_results = []
        
        # Strategy 1: CarWale Scrape
        all_results.extend(self._scrape_carwale(make, model, year, city))
        
        # Strategy 2: Spinny Scrape (requires Playwright)
        all_results.extend(self._scrape_spinny(make, model, year, city))
        
        # CRITICAL: Validate all results
        validated = self._validate_listings(all_results, make, model, year)
        
        if not validated:
            return {
                'success': False,
                'median_price': None,
                'count': 0,
                'message': f'No valid validated listings found for {year} {make} {model}',
                'raw_results': all_results[:5]
            }
        
        prices = [lst['price'] for lst in validated]
        cleaned_prices = self._remove_outliers(prices)
        
        return {
            'success': True,
            'median_price': statistics.median(cleaned_prices),
            'mean_price': statistics.mean(cleaned_prices),
            'min_price': min(cleaned_prices),
            'max_price': max(cleaned_prices),
            'count': len(validated),
            'listings': validated[:5],
            'price_range': f"₹{min(cleaned_prices):.2f}L - ₹{max(cleaned_prices):.2f}L",
            'debug_log': f"Validated {len(validated)} listings after strict filtering."
        }

    def _scrape_carwale(self, make: str, model: str, year: int, city: str) -> List[Dict]:
        listings = []
        # Attempt BeautifulSoup first for CarWale as it's faster
        try:
            make_slug = make.lower().replace(' ', '-')
            model_slug = model.lower().replace(' ', '-')
            city_slug = city.lower().replace(' ', '-')
            url = f"https://www.carwale.com/used/{make_slug}-{model_slug}-cars-in-{city_slug}/"
            
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.content, 'html.parser')
                cards = soup.find_all('div', class_='o-cpnuEd')
                for card in cards[:15]:
                    text = card.get_text()
                    price_match = re.search(r'₹\s*([\d.]+)\s*(?:Lakh|L)', text, re.IGNORECASE)
                    if not price_match: continue
                    
                    price = float(price_match.group(1))
                    year_match = re.search(r'\b(20\d{2})\b', text)
                    car_year = int(year_match.group(1)) if year_match else None
                    
                    listings.append({
                        'source': 'CarWale',
                        'price': price,
                        'year': car_year,
                        'title': text[:100].replace('\n', ' ')
                    })
        except:
            pass
        return listings

    def _scrape_spinny(self, make: str, model: str, year: int, city: str) -> List[Dict]:
        # Requires Playwright
        from src.engine_smart_scraper import PLAYWRIGHT_READY as PR_GLOBAL
        if not sync_playwright or not PR_GLOBAL:
            return []
            
        listings = []
        try:
            with sync_playwright() as p:
                browser = self._safe_launch(p)
                if not browser: return []
                page = browser.new_page()
                make_slug = make.lower().replace(' ', '-')
                model_slug = model.lower().replace(' ', '-')
                city_slug = city.lower().replace(' ', '-')
                url = f"https://www.spinny.com/buy-used-{make_slug}-{model_slug}-cars-in-{city_slug}/"
                
                page.goto(url, wait_until="domcontentloaded", timeout=20000)
                time.sleep(3)
                cards = page.query_selector_all('[data-testid="car-card"], .car-card')
                for card in cards[:15]:
                    text = card.inner_text()
                    price_match = re.search(r'₹\s*([\d.]+)\s*(?:Lakh|L)', text, re.IGNORECASE)
                    if not price_match: continue
                    price = float(price_match.group(1))
                    year_match = re.search(r'\b(20\d{2})\b', text)
                    car_year = int(year_match.group(1)) if year_match else None
                    listings.append({
                        'source': 'Spinny',
                        'price': price,
                        'year': car_year,
                        'title': text[:100].replace('\n', ' ')
                    })
                browser.close()
        except:
            pass
        return listings

    def _validate_listings(self, listings: List[Dict], target_make: str, 
                          target_model: str, target_year: int) -> List[Dict]:
        """
        STRICT validation to prevent random car pollution.
        """
        validated = []
        target_make = target_make.lower()
        target_model = target_model.lower()
        
        for lst in listings:
            # Price sanity (Filter out down-payments/absurd values)
            # 1.0L is usually a down payment for most modern cars
            if lst['price'] < 2.0 or lst['price'] > 100.0:
                continue
            
            # Year match (Strict ±1 year)
            if not lst['year'] or abs(lst['year'] - target_year) > 1:
                continue
            
            # Make/Model match in title
            title_lower = lst['title'].lower()
            if target_make not in title_lower:
                continue
            
            # Fuzzy model match (check if at least one word of model is present)
            model_words = target_model.split()
            if not any(word in title_lower for word in model_words if len(word) > 2):
                continue
            
            validated.append(lst)
        return validated

    def _remove_outliers(self, prices: List[float]) -> List[float]:
        if len(prices) < 4: return prices
        q1, q3 = statistics.quantiles(prices, n=4)[0], statistics.quantiles(prices, n=4)[2]
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        cleaned = [p for p in prices if lower <= p <= upper]
        return cleaned if cleaned else prices

def get_market_estimate(make, model, year, city):
    engine = MarketResearchEngine()
    return engine.search_specific_car(make, model, year, city)
