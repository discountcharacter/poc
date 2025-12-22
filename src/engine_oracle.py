import requests
import json
import re

def get_gemini_estimate(make, model, year, variant, km, condition, location, remarks, context_data, api_key):
    """
    Engine C: The Oracle
    Uses Google Gemini REST API directly to estimate price.
    Returns: (price, debug_data)
    """
    if not api_key:
        print("Oracle Engine: Missing API Key")
        return None, {"error": "Missing API Key"}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    prompt_text = f"""
    Act as a highly experienced Used Car Valuation Expert in India. 
    Perform a comprehensive market analysis to estimate the fair selling price for a used car.
    
    Vehicle Details:
    - Year: {year}
    - Make: {make}
    - Model: {model}
    - Variant: {variant}
    - Location: {location}
    - Odometer: {km} km
    - Condition: {condition}
    - Additional Remarks: "{remarks}"

    REAL-TIME MARKET CONTEXT (Treat this data as SUGGESTIONS, not absolute facts):
    {context_data}

    CRITICAL INSTRUCTIONS:
    1. **Don't Blindly Copy**: If the "ML Model Prediction" or "Depreciation Logic" seems wrong based on your expert knowledge of the Indian car market (e.g., a 2025 car being valued too low), you MUST override it.
    2. **Ground Truth**: A 2024/2025 car with low mileage (<5000 km) is essentially NEW. It should be valued at its "Ex-Showroom Price - 10-15%" plus taxes/registration value, unless there is specific market evidence otherwise.
    3. **Context Sensitivity**: If "Sniper" or "Scout" found direct matches, they are your best source. If they found nothing, use your internal knowledge of current ex-showroom prices for this specific model in India.
    4. **ML Anchoring**: Do not simply repeat the ML prediction. Evaluate if the ML score (trained on historical data) is accurate for a current-year or next-year model.

    Step 1: Market Research Analysis
    - Analyze the provided "Real-Time Market Context". 
    - Verify if the "Sniper" or "Scout" found specific listings. If so, use them as a strong baseline.
    - Check the "Real Base Price" if provided.

    Step 2: Depreciation Analysis
    - Apply standard depreciation curves.
    - Adjust for mileage (High/Low) and condition.

    Step 3: Comparative Analysis
    - Compare with similar models using your internal knowledge.

    Step 4: Final Valuation
    - Provide a specific estimated fair market value in INR.

    OUTPUT FORMAT:
    First, provide a brief (2-3 bullet points) "Market Analysis" explaining your reasoning. Be explicit about why you accepted or REJECTED the provided context data.
    Then, on the very last line, provide ONLY the numeric value in INR.
    
    Example Output:
    Market Analysis:
    - Context showed an ML prediction of 8L, but this is a 2025 top-spec variant which currently retails at 10L; thus I am adjusting upwards.
    - Very low mileage justifies a smaller depreciation than the standard 15%.
    Final Price: 910000
    """
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt_text}]
        }]
    }
    
    headers = {'Content-Type': 'application/json'}
    
    debug_data = {"prompt": prompt_text, "response": None}

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        
        if response.status_code != 200:
            err = f"API Error: {response.status_code} - {response.text}"
            print(f"Oracle Engine API Error: {err}")
            debug_data["response"] = err
            return None, debug_data
            
        result = response.json()
        
        # Extract text from response
        try:
            text_response = result['candidates'][0]['content']['parts'][0]['text']
            debug_data["response"] = text_response
        except (KeyError, IndexError):
            debug_data["response"] = "Unexpected JSON structure"
            return None, debug_data
            
        # Parse the final line for the price
        # We look for the last sequence of digits in the text
        clean_val = re.findall(r"\d+", text_response.replace(",", ""))
        
        if clean_val:
            # Take the last found number as it is likely the "Final Price" requested
            estimated_price = int(clean_val[-1])
            return estimated_price, debug_data
        else:
            return None, debug_data
            
    except Exception as e:
        print(f"Oracle Engine Error: {e}")
        debug_data["error"] = str(e)
        return None, debug_data
