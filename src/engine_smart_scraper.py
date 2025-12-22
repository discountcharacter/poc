import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode
import re
import statistics
from typing import List, Dict
import time

class SmartCarScraper:
    """
    Intelligent scraper that applies filters and extracts multiple listings
    instead of just grabbing the first result.
    """
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5'
        }
        
    def build_carwale_url(self, make: str, model: str, year: int, 
                          fuel: str, city: str, max_km: int) -> str:
        """Build filtered CarWale URL"""
        city_slug = city.lower().replace(' ', '-')
        base = f"https://www.carwale.com/used/cars-in-{city_slug}/"
        
        # CarWale uses slug patterns for filters often, or query params
        params = {
            'make': make.lower(),
            'model': model.lower().replace(' ', '-'),
            'yearFrom': year - 1,  # ±1 year tolerance
            'yearTo': year + 1,
            'fuelType': fuel.lower(),
            'kmDriven': max_km + 15000  # tolerance
        }
        
        return base + '?' + urlencode(params)
    
    def build_spinny_url(self, make: str, model: str, year: int, 
                         fuel: str, city: str) -> str:
        """Build filtered Spinny URL"""
        make_slug = make.lower().replace(' ', '-')
        model_slug = model.lower().replace(' ', '-')
        city_slug = city.lower().replace(' ', '-')
        
        return f"https://www.spinny.com/buy-used-{make_slug}-{model_slug}-cars-in-{city_slug}/?year={year}&fuel={fuel.lower()}"
    
    def scrape_carwale(self, url: str, max_results: int = 12) -> List[Dict]:
        """
        Scrape multiple listings from CarWale with exact filters applied
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code != 200:
                return []
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            listings = []
            # Updated selectors based on common CarWale structure
            cards = soup.find_all('div', class_='used-card')[:max_results]
            
            # Fallback for different class names
            if not cards:
                cards = soup.select('div[data-listing-id]')[:max_results]
            
            for card in cards:
                try:
                    text_content = card.get_text(" ", strip=True)
                    
                    # Extract price
                    price = self._parse_price(text_content)
                    if not price: continue
                    
                    # Extract KM
                    km_match = re.search(r'(\d+(?:,\d+)*)\s*km', text_content, re.IGNORECASE)
                    km = int(km_match.group(1).replace(',', '')) if km_match else 0
                    
                    # Extract year
                    year_match = re.search(r'\b(20\d{2})\b', text_content)
                    found_year = int(year_match.group(1)) if year_match else 0
                    
                    # Extract listing URL
                    link_tag = card.find('a', href=True)
                    link = link_tag['href'] if link_tag else ""
                    if link and not link.startswith('http'):
                        link = 'https://www.carwale.com' + link
                    
                    listings.append({
                        'source': 'CarWale',
                        'price': price,
                        'km': km,
                        'year': found_year,
                        'url': link,
                        'title': card.find('h3').text.strip() if card.find('h3') else "CarWale Listing"
                    })
                    
                except Exception as e:
                    continue
            
            return listings
            
        except Exception:
            return []
    
    def scrape_spinny(self, url: str, max_results: int = 12) -> List[Dict]:
        """
        Scrape multiple listings from Spinny with filters
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code != 200:
                return []
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            listings = []
            # Spinny listing cards
            cards = soup.select('a[class*="styles_carCard"]')[:max_results]
            if not cards:
                cards = soup.find_all('div', {'data-testid': 'car-card'})[:max_results]
            
            for card in cards:
                try:
                    text_content = card.get_text(" ", strip=True)
                    
                    price = self._parse_price(text_content)
                    if not price: continue
                    
                    # Extract KM and Year from Spinny format
                    km_match = re.search(r'(\d+(?:,\d+)*)\s*km', text_content, re.IGNORECASE)
                    km = int(km_match.group(1).replace(',', '')) if km_match else 0
                    
                    year_match = re.search(r'\b(20\d{2})\b', text_content)
                    found_year = int(year_match.group(1)) if year_match else 0
                    
                    link = card['href'] if card.has_attr('href') else ""
                    if link and not link.startswith('http'):
                        link = 'https://www.spinny.com' + link
                    
                    listings.append({
                        'source': 'Spinny',
                        'price': price,
                        'km': km,
                        'year': found_year,
                        'url': link,
                        'title': text_content[:50] + "..."
                    })
                    
                except Exception:
                    continue
            
            return listings
            
        except Exception:
            return []
    
    def _parse_price(self, text: str) -> float:
        """Extract price in lakhs from mixed text"""
        # Match ₹8.5 Lakh or ₹8,50,000
        price_pattern = re.compile(r"(?:₹|Rs\.?)\s*(\d+(?:\.\d+)?)\s*(?:Lakh|Lakhs|L)?", re.IGNORECASE)
        match = price_pattern.search(text)
        if not match:
            # Try plain number matches for larger values
            full_num_match = re.search(r'(?:₹|Rs\.?)\s*(\d+(?:,\d+)*)', text)
            if full_num_match:
                val = float(full_num_match.group(1).replace(',', ''))
                if val > 100000:
                    return round(val / 100000, 2)
            return 0.0
            
        val = float(match.group(1))
        # If the number is small (e.g. 8.5), it's likely already in Lakhs
        # If it's large (e.g. 850000), it's absolute
        if val < 500:
            return val
        else:
            return round(val / 100000, 2)
    
    def get_market_data(self, make: str, model: str, year: int, 
                       fuel: str, city: str, km_driven: int) -> Dict:
        """
        Main function: Get 15-20 listings from multiple sources
        """
        all_listings = []
        
        # Scrape CarWale
        carwale_url = self.build_carwale_url(make, model, year, fuel, city, km_driven)
        carwale_listings = self.scrape_carwale(carwale_url)
        all_listings.extend(carwale_listings)
        
        # Scrape Spinny
        spinny_url = self.build_spinny_url(make, model, year, fuel, city)
        spinny_listings = self.scrape_spinny(spinny_url)
        all_listings.extend(spinny_listings)
        
        # Clean and analyze data
        cleaned = self._remove_outliers(all_listings, km_driven)
        
        if not cleaned:
            return {
                'success': False,
                'message': 'No valid listings found',
                'search_urls': [carwale_url, spinny_url]
            }
        
        prices = [l['price'] for l in cleaned]
        
        return {
            'success': True,
            'count': len(cleaned),
            'listings': cleaned,
            'statistics': {
                'median': round(statistics.median(prices), 2),
                'mean': round(statistics.mean(prices), 2),
                'min': min(prices),
                'max': max(prices),
                'std_dev': round(statistics.stdev(prices), 2) if len(prices) > 1 else 0
            },
            'search_urls': [carwale_url, spinny_url]
        }
    
    def _remove_outliers(self, listings: List[Dict], target_km: int) -> List[Dict]:
        """
        Remove outliers and sort by relevance
        """
        if not listings:
            return []
        
        # Basic filter: Year within range
        # (Already handled by build_url but good for robustness)
        
        # Remove price outliers using IQR method
        prices = [l['price'] for l in listings]
        if len(prices) < 4:
            return listings
        
        q1, q2, q3 = statistics.quantiles(prices, n=4)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        cleaned = [l for l in listings if lower_bound <= l['price'] <= upper_bound]
        
        # Sort by KM proximity to target
        cleaned.sort(key=lambda x: abs(x['km'] - target_km))
        
        return cleaned

if __name__ == "__main__":
    scraper = SmartCarScraper()
    print(scraper.get_market_data("Hyundai", "Creta", 2020, "Petrol", "Mumbai", 35000))
