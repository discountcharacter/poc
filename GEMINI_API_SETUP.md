# Gemini API Setup Instructions

## Required: Set up your API Key

The OBV valuation system now uses **ONLY** Gemini API with Google Search grounding to fetch current vehicle prices.

### Step 1: Get your Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Click "Get API Key"
3. Create a new API key or use an existing one
4. Copy the API key

### Step 2: Set up environment variable

Create or edit `.env` file in the project root:

```bash
# Either of these will work:
GEMINI_API_KEY=your_api_key_here
# OR
GOOGLE_API_KEY=your_api_key_here
```

### Step 3: Deploy to Streamlit Cloud

1. Go to your Streamlit Cloud app settings
2. Navigate to "Secrets"
3. Add your API key:
   ```toml
   GEMINI_API_KEY = "your_api_key_here"
   ```

## Important Notes

- ✅ **NO FALLBACKS**: System will fail with clear error if API key is missing
- ✅ **NO WEB SCRAPING**: Only uses Gemini API + Google Search grounding
- ✅ **NO ESTIMATES**: No fallback to historical price estimates
- ❌ **WILL NOT WORK** without valid GEMINI_API_KEY

## Testing

Test the setup:

```bash
python test_gemini_price.py
```

Expected output:
```
✅ Gemini price fetcher imported successfully

--- Testing Swift LXI price fetch ---
🔍 Fetching live price using Gemini API for Maruti Suzuki Swift LXI Petrol...
   📊 Response: {"price":"5.79 Lakh"...}
   ✅ Extracted price: ₹579,000

✅ SUCCESS: ₹579,000.00 (5.79 Lakhs)
   Source: gemini_grounded_search
```

## Error Messages

If you see these errors, check your API key:

```
❌ GEMINI_API_KEY or GOOGLE_API_KEY not found in environment variables.
   Set your API key in .env file:
   GEMINI_API_KEY=your_key_here
```

```
ValueError: Failed to fetch price for Maruti Suzuki Swift LXI: ...
```

## API Costs

- **Model**: gemini-2.0-flash-exp
- **Free Tier**: 15 requests per minute, 1500 requests per day
- **Paid**: Very low cost per request
- Check current pricing at [Google AI Pricing](https://ai.google.dev/pricing)

## What Changed

Before (Web Scraping):
- ❌ CarDekho/CarWale HTML parsing
- ❌ BeautifulSoup dependency
- ❌ Fallback to estimates if scraping failed

After (Gemini API):
- ✅ Gemini 2.0 Flash with Google Search grounding
- ✅ AI finds and extracts prices from best sources
- ✅ Fails loudly if API key missing (no silent fallbacks)
