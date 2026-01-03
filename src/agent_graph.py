import os
import time
import requests
import json
import re

from dotenv import load_dotenv

load_dotenv()

class ValuationAgent:
    """
    Rescue-v2.0: Automated Market Analysis
    Browses live markets via Custom Search and uses LLM (Gemini REST API) to verify data.
    """
    def __init__(self, gemini_key, search_key=None, cx=None):
        self.gemini_key = gemini_key or os.getenv("GOOGLE_API_KEY")
        self.search_key = search_key or os.getenv("GOOGLE_SEARCH_API_KEY")
        self.cx = cx or os.getenv("SEARCH_ENGINE_ID")

    def search_market(self, make, model, year, variant, location, km=None, fuel=None, owners=None, condition=None, remarks=None):
        """
        Orchestrates the browsing and reasoning process using APIs.
        """
        if not self.gemini_key: return {"error": "Missing Gemini API Key"}
        if not self.search_key or not self.cx: return {"error": "Missing Google Search API Key/CX"}

        details = f"{year} {make} {model} {variant}"
        if fuel: details += f" {fuel}"
        print(f"🤖 Agent: Searching for {details} in {location}...")
        
        # 1. Browse (Google Custom Search API)
        queries = [
            f"used {year} {make} {model} {variant} price in {location} site:carwale.com",
            f"used {year} {make} {model} {variant} price in {location} site:spinny.com",
            f"used {year} {make} {model} {variant} price in {location} site:cardekho.com"
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
                    "num": 10 # Increase to 10 to find prices
                }
                resp = requests.get(url, params=params, timeout=10)
                json_data = resp.json() # Renamed to json_data to avoid conflict
                
                if "items" in json_data:
                    for item in json_data["items"]:
                        title = item.get("title", "")
                        link = item.get("link", "")
                        snippet = item.get("snippet", "")
                        # Combine for context with Link
                        raw_listings.append(f"Title: {title}\nLink: {link}\nSnippet: {snippet}")
                
                time.sleep(0.5) 
            except Exception as e:
                print(f"   Search API Error: {e}")
            
        print(f"🔎 Agent: Found {len(raw_listings)} raw snippets. Reasoning...")
        
        # 2. Reason (LLM Filtering)
        if not raw_listings:
             return {"error": "No listings found on Google Search."}
             
        analysis = self._filter_with_llm(raw_listings, make, model, year, variant, location, km, fuel, owners, condition, remarks)
        return analysis

    def _filter_with_llm(self, raw_data, make, model, year, variant, location, km, fuel, owners, condition, remarks):
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
        Fuel: {fuel}
        Odometer: {km} km
        Owners: {owners}
        Condition: {condition}
        Remarks: {remarks}
        
        Raw Search Results (Scraped Text):
        {raw_listings_str(raw_data)}
        
        YOUR TASK:
        1. Identify listings that match the Target Vehicle REASONABLY WELL. 
           - Match Year within +/- 1 year.
           - Match Model (Must be {model}).
           - Match Variant logic (e.g. "SX" matches "SX 1.5").
           - IGNORE completely irrelevant results.
        
        2. Extract the PRICE and LINK (URL) for each valid listing.
        
        3. CALCULATE THE "MARKET RETAIL PRICE" (What dealers sell for).
           - Median of valid listings.
           - Adjust for Odometer/Condition (High KM = Lower Value).
           - CRITICAL: If no exact prices found in snippets, USE YOUR INTELLIGENCE to PREDICT/ESTIMATE the price based on the car details and Indian Market context. DO NOT return 0 or Null if you can estimate it.
        
        OUTPUT FORMAT (JSON ONLY):
        {{
            "valid_listings": [
                {{"title": "...", "price": 1050000, "link": "https://...", "source": "CarWale", "reason": "Strong Match"}}
            ],
            "rejected_count": 5,
            "market_price": 1050000,
            "reasoning": "Detailed analysis. Mention specific listings (e.g. 'Found 2010 City at 2.75L'). Explain adjustments for mileage/condition (e.g. '330k km is exceptionally high, reducing value by 50%'). Be professional and analytical."
        }}
        """
        
        result_text = self._call_gemini_rest(prompt_text)
        if not result_text:
            return {"error": "LLM returned empty response", "raw_listings": len(raw_data)}
            
        if result_text.startswith("Error"):
             return {"error": result_text, "reasoning": "LLM failed to generate a response."}

        try:
            # Clean json block - find the first outer { }
            txt = result_text.strip()
            
            # Remove markdown if present
            if "```" in txt:
                match = re.search(r"```(?:json)?\n?(.*?)```", txt, re.DOTALL)
                if match:
                    txt = match.group(1).strip()
            
            # Fallback: Find first { and last }
            start = txt.find("{")
            end = txt.rfind("}")
            if start != -1 and end != -1:
                txt = txt[start:end+1]
            
            data = json.loads(txt)
            return data
        except Exception as e:
            print(f"Parsing FAILED on: {result_text}")
            return {
                "error": f"LLM Parsing Failed: {str(e)}", 
                "raw_response": result_text,
                "reasoning": "The AI Agent could not format the valuation data correctly. Please try again."
            }

    def _call_gemini_rest(self, prompt):
        """
        Raw REST API call to Gemini Pro with Retry logic.
        """
        # Using gemini-2.0-flash as it is the currently available stable model
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.gemini_key}"
        headers = {'Content-Type': 'application/json'}
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        
        for attempt in range(3):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    # Check if candidates exist (Safety filters can block response)
                    if not data.get('candidates'):
                        print(f"Gemini Safety/Block Error: {data}")
                        return f"Error: Model blocked response. Safety/Other reason. Raw: {json.dumps(data)}"
                    return data['candidates'][0]['content']['parts'][0]['text']
                else:
                    print(f"Gemini API Error {response.status_code}: {response.text}")
                    if response.status_code >= 500:
                        time.sleep(1) # Retry on server error
                        continue
                    return f"Error: API {response.status_code} - {response.text}"
            except Exception as e:
                print(f"Gemini REST Exception: {e}")
                time.sleep(1)
        
        return "Error: Failed after 3 attempts."

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
