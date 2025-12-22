import requests
from bs4 import BeautifulSoup
import re

def fetch_closest_match(make, model, year, variant, km, city, api_key_search, search_cx):
    """
    Engine D: Direct Match (Multi-Source)
    Targets CarWale and Spinny via Direct URL Scraping + Google Search Fallback.
    Returns: (best_price, sources_dict, match_details_string)
    
    sources_dict format: {"carwale": {"price": int, "url": str}, "spinny": {"price": int, "url": str}}
    """
    
    # Clean inputs
    city_slug = city.lower().replace(" ", "-") if city else "mumbai"
    
    # Robust Slug Mapping for CarWale
    CARWALE_SLUG_MAP = {
        "maruti": "maruti-suzuki",
        "mercedes": "mercedes-benz",
        "mercedes-benz": "mercedes-benz",
        "land rover": "land-rover",
        "mg": "mg",
        "bmw": "bmw",
        "audi": "audi",
        "windsor": "windsor-ev"
    }
    
    safe_make = make.lower().strip()
    make_slug = CARWALE_SLUG_MAP.get(safe_make, safe_make.replace(" ", "-"))
    model_slug = model.lower().strip().replace(" ", "-")
    
    debug_log = []
    sources = {}
    all_candidates = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }
    
    year_pattern = re.compile(r"\b(20\d{2})\b")
    
    # ==================== CARWALE SCRAPING ====================
    carwale_candidates = []
    carwale_url = f"https://www.carwale.com/used/{city_slug}/{make_slug}-{model_slug}/"
    debug_log.append(f"CarWale: Attempting {carwale_url}")
    
    try:
        response = requests.get(carwale_url, headers=headers, timeout=5)
        if response.history:
            debug_log.append(f"CarWale: Redirected to {response.url}")
            
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link['href']
                text = link.get_text(" ", strip=True)
                
                if "/used/" in href and (make_slug in href or model_slug in href):
                    full_text = text
                    parent = link.find_parent('div')
                    if parent:
                        full_text += " " + parent.get_text(" ", strip=True)
                    
                    title_years = year_pattern.findall(full_text)
                    if not title_years:
                        continue
                        
                    listing_year = int(title_years[0])
                    if abs(listing_year - year) > 1:
                        continue

                    price_matches = re.findall(r"(?:₹|Rs\.?)\s*(\d+(\.\d+)?)\s*(?:Lakh|Lakhs|L)", full_text, re.IGNORECASE)
                    
                    found_price = 0
                    if price_matches:
                        val = float(price_matches[0][0])
                        if 1.0 < val < 200.0:
                            found_price = int(val * 100000)
                    
                    if found_price > 0:
                        carwale_candidates.append({
                            "price": found_price, 
                            "title": text, 
                            "url": "https://www.carwale.com" + href if not href.startswith("http") else href,
                            "source": "CarWale"
                        })
            debug_log.append(f"CarWale: Found {len(carwale_candidates)} matches")
        else:
            debug_log.append(f"CarWale: Status {response.status_code}")
            
    except Exception as e:
        debug_log.append(f"CarWale Error: {str(e)}")
    
    # ==================== SPINNY SCRAPING ====================
    spinny_candidates = []
    # Spinny URL pattern: https://www.spinny.com/used-{model}-cars-in-{city}/s/
    spinny_url = f"https://www.spinny.com/used-{model_slug}-cars-in-{city_slug}/s/"
    debug_log.append(f"Spinny: Attempting {spinny_url}")
    
    try:
        response = requests.get(spinny_url, headers=headers, timeout=5)
        if response.history:
            debug_log.append(f"Spinny: Redirected to {response.url}")
            
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Spinny uses different HTML structure - look for car cards
            # Try multiple selectors
            car_cards = soup.find_all('a', href=True)
            
            for card in car_cards:
                href = card['href']
                text = card.get_text(" ", strip=True)
                
                # Spinny listing URLs contain /buy-used-cars/
                if "/buy-used-cars/" in href and model_slug in href.lower():
                    full_text = text
                    parent = card.find_parent('div')
                    if parent:
                        full_text += " " + parent.get_text(" ", strip=True)
                    
                    title_years = year_pattern.findall(full_text)
                    if not title_years:
                        # Also check the URL for year
                        url_years = year_pattern.findall(href)
                        if url_years:
                            title_years = url_years
                        else:
                            continue
                        
                    listing_year = int(title_years[0])
                    if abs(listing_year - year) > 1:
                        continue

                    # Spinny prices may be in different formats
                    price_matches = re.findall(r"(?:₹|Rs\.?)\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:Lakh|Lakhs|L)?", full_text, re.IGNORECASE)
                    
                    found_price = 0
                    for match in price_matches:
                        try:
                            val_str = match.replace(",", "")
                            val = float(val_str)
                            # Check if it's in lakhs or actual value
                            if 1.0 < val < 200.0:
                                found_price = int(val * 100000)
                                break
                            elif 100000 < val < 20000000:
                                found_price = int(val)
                                break
                        except:
                            continue
                    
                    if found_price > 0:
                        full_url = "https://www.spinny.com" + href if not href.startswith("http") else href
                        spinny_candidates.append({
                            "price": found_price, 
                            "title": text[:100] if text else f"{year} {make} {model}", 
                            "url": full_url,
                            "source": "Spinny"
                        })
            debug_log.append(f"Spinny: Found {len(spinny_candidates)} matches")
        else:
            debug_log.append(f"Spinny: Status {response.status_code}")
            
    except Exception as e:
        debug_log.append(f"Spinny Error: {str(e)}")

    # ==================== GOOGLE FALLBACK ====================
    # If no direct results, use Google to search both sites
    if not carwale_candidates and not spinny_candidates and api_key_search:
        debug_log.append("Falling back to Google Search...")
        
        for site, site_candidates in [("carwale.com/used", carwale_candidates), ("spinny.com/buy-used-cars", spinny_candidates)]:
            query = f"site:{site} {make} {model} {city} {year} {variant}"
            
            url = "https://www.googleapis.com/customsearch/v1"
            params = {"key": api_key_search, "cx": search_cx, "q": query, "num": 3}
            
            try:
                resp = requests.get(url, params=params)
                data = resp.json()
                if "items" in data:
                    price_pattern_google = re.compile(r"(\d+(\.\d+)?)\s*(?:Lakh|Lakhs|L)", re.IGNORECASE)
                    for item in data["items"]:
                        title = item.get("title", "")
                        snippet = item.get("snippet", "")
                        full_text = f"{title} {snippet}"
                        
                        title_years = year_pattern.findall(title)
                        if not title_years:
                            title_years = year_pattern.findall(snippet)
                        
                        if title_years:
                            listing_year = int(title_years[0])
                            if abs(listing_year - year) > 1:
                                continue
                        else:
                            continue
                        
                        matches = price_pattern_google.findall(full_text)
                        for match in matches:
                            try:
                                val = float(match[0])
                                if 1.0 < val < 200.0:
                                    source_name = "CarWale" if "carwale" in site else "Spinny"
                                    site_candidates.append({
                                        "price": int(val * 100000),
                                        "title": title,
                                        "url": item.get("link"),
                                        "source": source_name
                                    })
                                    break
                            except: 
                                continue
            except Exception as e:
                debug_log.append(f"Google Search Error ({site}): {str(e)}")

    # ==================== SCORING & SELECTION ====================
    all_candidates = carwale_candidates + spinny_candidates
    
    if not all_candidates:
        # Return fallback URLs even if no prices found
        sources["carwale"] = {"price": None, "url": carwale_url}
        sources["spinny"] = {"price": None, "url": spinny_url}
        return None, sources, "\n".join(debug_log)
    
    variant_lower = variant.lower()
    
    # Score and find best for each source
    def score_candidate(cand):
        score = 0
        details = []
        title_lower = cand["title"].lower()
        
        # 1. Model Match (Basic filtering)
        model_tokens = model.lower().split()
        match_count = sum(1 for token in model_tokens if token in title_lower)
        if len(model_tokens) > 0 and (match_count / len(model_tokens) < 0.5):
            return -1, "Model Mismatch"
        
        # 2. Year Match (Strong preference for exact)
        if str(year) in title_lower:
            score += 100
            details.append("Year:Exact(+100)")
        elif str(year-1) in title_lower or str(year+1) in title_lower:
            score += 30
            details.append("Year:Near(+30)")
        else:
            # Fallback if year not in title but passed filter (shouldn't happen with current Scraping logic)
            score += 10
            details.append("Year:Match(+10)")
             
        # 3. Variant Match (Improved overlap scoring)
        # We want to match search variant words to title words
        # but also penalize if the title has many extra model-specific words
        var_words = set(variant_lower.split())
        title_words = set(title_lower.split())
        
        # Intersection
        matches = var_words.intersection(title_words)
        match_ratio = len(matches) / len(var_words) if var_words else 1.0
        
        # Penalty for extra descriptive words that aren't in search variant
        # (Exclude brand/model/year tokens from penalty)
        noise_words = {"pro", "plus", "new", "all", "the", "automatic", "manual", "petrol", "diesel", "cng"}
        exclude_penalty = set(make.lower().split()) | set(model.lower().split()) | {str(year), str(year-1), str(year+1)} | noise_words
        extra_words = title_words - var_words - exclude_penalty
        penalty = min(len(extra_words) * 5, 20) # Max penalty 20
        
        variant_score = int(match_ratio * 50) - penalty
        score += variant_score
        details.append(f"Var:{variant_score}({len(matches)}/{len(var_words)})")
            
        return score, ", ".join(details)
    
    # Find best CarWale match
    best_carwale = None
    best_carwale_score = -1
    for cand in carwale_candidates:
        score, scoring_debug = score_candidate(cand)
        cand["scoring_debug"] = scoring_debug
        if score > best_carwale_score:
            best_carwale_score = score
            best_carwale = cand
    
    # Find best Spinny match
    best_spinny = None
    best_spinny_score = -1
    for cand in spinny_candidates:
        score, scoring_debug = score_candidate(cand)
        cand["scoring_debug"] = scoring_debug
        if score > best_spinny_score:
            best_spinny_score = score
            best_spinny = cand
    
    # Build sources dict
    if best_carwale:
        sources["carwale"] = {"price": best_carwale["price"], "url": best_carwale["url"]}
    else:
        sources["carwale"] = {"price": None, "url": carwale_url}
        
    if best_spinny:
        sources["spinny"] = {"price": best_spinny["price"], "url": best_spinny["url"]}
    else:
        sources["spinny"] = {"price": None, "url": spinny_url}
    
    # Find overall best for the main price
    best_overall = None
    if best_carwale and best_spinny:
        best_overall = best_carwale if best_carwale_score >= best_spinny_score else best_spinny
    elif best_carwale:
        best_overall = best_carwale
    elif best_spinny:
        best_overall = best_spinny
    
    if best_overall:
        debug_log.append(f"Best Match: {best_overall['title']} ({best_overall['source']})")
        debug_log.append(f"Scoring: {best_overall.get('scoring_debug', 'N/A')}")
        return best_overall["price"], sources, "\n".join(debug_log)
    
    return None, sources, "\n".join(debug_log)

