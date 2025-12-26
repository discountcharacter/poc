import os
import time
import requests
import json
import re
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

class ValuationAgent:
    """
    Rescue-v2.0: The Oracle Agent
    Browses live markets via Playwright and uses LLM (Gemini REST API) to verify data.
    """
    def __init__(self, gemini_key, search_key=None, cx=None):
        self.gemini_key = gemini_key or os.getenv("GOOGLE_API_KEY")
        self.search_key = search_key or os.getenv("GOOGLE_SEARCH_API_KEY")
        self.cx = cx or os.getenv("SEARCH_ENGINE_ID")

    def search_market(self, make, model, year, variant, location):
        """
        Orchestrates the browsing and reasoning process using APIs.
        """
        if not self.gemini_key: return {"error": "Missing Gemini API Key"}
        if not self.search_key or not self.cx: return {"error": "Missing Google Search API Key/CX"}

        print(f"🤖 Agent: Searching for {year} {make} {model} {variant} in {location}...")
        
        # 1. Browse (Google Custom Search API)
        queries = [
            f"{year} {make} {model} {variant} price {location} site:carwale.com",
            f"{year} {make} {model} {variant} price {location} site:spinny.com",
            f"{year} {make} {model} {variant} price {location} site:cardekho.com"
        ]
        
        raw_listings = []
        
        for q in queries:
            try:
                print(f"   API Search: {q}")
                url = "https://www.googleapis.com/customsearch/v1"
                params = {
                    "key": self.search_key,
                    "cx": self.cx,
                    "q": q,
                    "num": 5 # Top 5 results
                }
                resp = requests.get(url, params=params, timeout=10)
                data = resp.json()
                
                if "items" in data:
                    for item in data["items"]:
                        title = item.get("title", "")
                        snippet = item.get("snippet", "")
                        # Combine for context
                        raw_listings.append(f"Title: {title}\nSnippet: {snippet}")
                
                time.sleep(0.5) 
            except Exception as e:
                print(f"   Search API Error: {e}")
            
        print(f"🔎 Agent: Found {len(raw_listings)} raw snippets. Reasoning...")
        
        # 2. Reason (LLM Filtering)
        if not raw_listings:
             return {"error": "No listings found on Google Search."}
             
        analysis = self._filter_with_llm(raw_listings, make, model, year, variant, location)
        return analysis

    def _filter_with_llm(self, raw_data, make, model, year, variant, location):
        """
        Sends raw scraped text to Gemini REST API to extract TRUE listings.
        """
        prompt_text = f"""
        You are an Expert Car Valuator. I have browsed Google for used car listings.
        
        Target Vehicle:
        Make: {make}
        Model: {model}
        Year: {year}
        Variant: {variant}
        Location: {location}
        
        Raw Search Results (Scraped Text):
        {raw_listings_str(raw_data)}
        
        YOUR TASK:
        1. Identify listings that match the Target Vehicle REASONABLY WELL. 
           - Match Year within +/- 1 year if price is reasonable.
           - Match Model (Must be {model}).
           - Match Variant logic (e.g. "SX" matches "SX 1.5", "SX Manual").
           - Allow "Petrol" to match generic listings if not explicitly "Diesel".
        2. IGNORE completely irrelevant results (e.g. "Aura", "Venue", "Review", "Compare", "New Car Price").
        3. Extract the price for each valid listing.
        4. Calculate the median price of valid listings.
        
        OUTPUT FORMAT (JSON ONLY):
        {{
            "valid_listings": [
                {{"title": "...", "price": 1050000, "source": "CarWale", "reason": "Strong Match"}}
            ],
            "rejected_count": 5,
            "estimated_price": 1050000,
            "reasoning": "Found 3 matches. Accepted 'SX 1.5' as valid variant."
        }}
        """
        
        result_text = self._call_gemini_rest(prompt_text)
        if not result_text:
            return {"error": "LLM returned empty response", "raw_listings": len(raw_data)}
            
        try:
            # Clean json block
            txt = result_text
            match = re.search(r"```json\n(.*?)\n```", txt, re.DOTALL)
            if match:
                txt = match.group(1)
            elif "```" in txt:
                 match = re.search(r"```(.*?)```", txt, re.DOTALL)
                 if match: txt = match.group(1)
            
            data = json.loads(txt)
            return data
        except Exception as e:
            return {"error": f"LLM Parsing Failed: {e}", "raw_response": result_text}

    def _call_gemini_rest(self, prompt):
        """
        Raw REST API call to Gemini Pro.
        """
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-latest:generateContent?key={self.gemini_key}"
        headers = {'Content-Type': 'application/json'}
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code != 200:
                print(f"Gemini API Error {response.status_code}: {response.text}")
                return None
                
            data = response.json()
            # Extract text: candidates[0].content.parts[0].text
            return data['candidates'][0]['content']['parts'][0]['text']
        except Exception as e:
            print(f"Gemini REST Error: {e}")
            return None

def raw_listings_str(listings):
    return "\n---\n".join([f"Item {i+1}: {t.replace(chr(10), ' ')}" for i, t in enumerate(listings)])

if __name__ == "__main__":
    # Test
    key = os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_SEARCH_API_KEY") # Try both
    # Load from main.py env if possible
    if not key:
        print("Set GOOGLE_API_KEY to run test.")
        exit()
        
    agent = ValuationAgent(key)
    res = agent.search_market("Hyundai", "Creta", 2020, "SX Petrol", "Hyderabad")
    print(json.dumps(res, indent=2))
