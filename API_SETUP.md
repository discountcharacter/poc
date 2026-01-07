# API Setup Instructions for OBV Price Fetcher

## Required: Google Custom Search API Setup

The OBV valuation system uses **HYBRID approach**: Google Custom Search API to find sources + Direct HTML scraping for accurate prices.

This is **MORE RELIABLE** than Gemini API which had JSON parsing errors and wrong year prices.

---

## Step 1: Get Google Custom Search API Key

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable **Custom Search API**
4. Go to **Credentials** → **Create Credentials** → **API Key**
5. Copy the API key

**API Key:** `AIzaSyCA0D2Rx1luO5uWK6JHiqo-il_iyFV12KM` (already provided)

---

## Step 2: Create Custom Search Engine

1. Go to [Google Custom Search Engine](https://programmablesearchengine.google.com/controlpanel/all)
2. Click **Add** to create new search engine
3. **What to search:** Select "Search the entire web"
4. Click **Create**
5. Copy your **Search Engine ID**

**Search Engine ID:** `9070febfd2f5b494c` (already provided)

---

## Step 3: Set Environment Variables

Create or edit `.env` file in the project root:

```bash
# Google Custom Search API (REQUIRED)
GOOGLE_SEARCH_API_KEY=AIzaSyCA0D2Rx1luO5uWK6JHiqo-il_iyFV12KM
SEARCH_ENGINE_ID=9070febfd2f5b494c

# Optional: Gemini API (not used anymore, but kept for compatibility)
GOOGLE_API_KEY=AIzaSyCxlVJbyYFLYnx2_PVTUyGf3td6bUJKqpM
GEMINI_API_KEY=AIzaSyCxlVJbyYFLYnx2_PVTUyGf3td6bUJKqpM
```

---

## Step 4: Deploy to Streamlit Cloud

1. Go to your Streamlit Cloud app settings
2. Navigate to **Secrets**
3. Add these secrets:

```toml
GOOGLE_SEARCH_API_KEY = "AIzaSyCA0D2Rx1luO5uWK6JHiqo-il_iyFV12KM"
SEARCH_ENGINE_ID = "9070febfd2f5b494c"
```

---

## How It Works

### **HYBRID APPROACH** (Current - Most Reliable)

```
1. User requests price for "Maruti Suzuki Swift VXI Petrol"
   ↓
2. Google Custom Search API finds relevant pages
   Query: "Maruti Suzuki Swift VXI Petrol ex-showroom price Hyderabad"
   Results: CarDekho, CarWale, ZigWheels pages
   ↓
3. Fetch HTML from top results (prioritize CarDekho/CarWale)
   ↓
4. Extract price using proven regex patterns:
   - Look for "Ex-Showroom Price" labels
   - Match variant + price patterns
   - Validate against other variants
   ↓
5. Return minimum price found (ex-showroom < on-road)
   Result: ₹659,000 (6.59 Lakhs)
```

### **Why Not Gemini API?**

❌ **Gemini API Issues:**
- Returns malformed JSON with triple backticks
- Inconsistent output format
- Returns wrong year prices (2024 instead of variant-specific)
- JSON parsing errors: `Expecting ',' delimiter`

✅ **Hybrid Approach Benefits:**
- No JSON parsing - direct HTML extraction
- Proven regex patterns (same as old scraper)
- Variant-specific prices
- Fallback through multiple search results
- More reliable and accurate

---

## Testing

Test the setup:

```bash
cd /home/user/poc
export GOOGLE_SEARCH_API_KEY="AIzaSyCA0D2Rx1luO5uWK6JHiqo-il_iyFV12KM"
export SEARCH_ENGINE_ID="9070febfd2f5b494c"
python -c "from src.price_fetcher_hybrid import test_price_fetcher; test_price_fetcher()"
```

Expected output:
```
🔍 Google Search: Maruti Suzuki Swift VXI Petrol ex-showroom price Hyderabad
   📄 Found: Maruti Suzuki Swift Price in Hyderabad...
   📥 Fetching: https://www.cardekho.com/maruti-suzuki/swift/price...
   ✅ Found ex-showroom label: ₹659,000
✅ Price: ₹659,000 (6.59 Lakhs)
   Source: hybrid_search_scrape
```

---

## Error Messages

### Missing API Key
```
⚠️ Google Custom Search API not configured
ValueError: No valid price found in search results
```
**Fix:** Add `GOOGLE_SEARCH_API_KEY` and `SEARCH_ENGINE_ID` to environment

### No Search Results
```
⚠️ No search results found
```
**Fix:** Check API quota (100 queries/day free tier)

### Scraping Failed
```
⚠️ Scrape error: HTTPSConnectionPool...
```
**Fix:** Network issue or rate limiting - will try next search result

---

## API Quotas & Costs

### Google Custom Search API

**Free Tier:**
- 100 queries per day
- Perfect for development and testing

**Paid:**
- $5 per 1000 queries
- For production use

Check usage: [Google Cloud Console - APIs & Services](https://console.cloud.google.com/apis/dashboard)

---

## Comparison: Hybrid vs Gemini

| Feature | Hybrid (Google Search + Scraping) | Gemini API |
|---------|-----------------------------------|------------|
| **Accuracy** | ✅ Very High (direct HTML) | ⚠️ Medium (AI interpretation) |
| **Reliability** | ✅ Consistent regex patterns | ❌ Malformed JSON errors |
| **Speed** | ✅ Fast (1-2 seconds) | ⚠️ Slower (3-5 seconds) |
| **Cost** | ✅ Free (100/day) | ⚠️ Paid per request |
| **Variant Specificity** | ✅ Exact variant matching | ❌ Sometimes wrong variant |
| **Parsing Issues** | ✅ None (regex) | ❌ JSON parse errors |
| **Year Accuracy** | ✅ Current prices | ❌ Returns 2024 prices |

---

## Troubleshooting

### 1. "No valid price found"
- Check if search engine ID is correct
- Verify API key has Custom Search API enabled
- Try different variant names (LXI vs Lxi)

### 2. "Quota exceeded"
- Free tier: 100 queries/day
- Wait 24 hours or upgrade to paid tier

### 3. "No search results"
- Check internet connectivity
- Verify GOOGLE_SEARCH_API_KEY is correct
- Ensure search engine ID is valid

---

## Migration from Gemini API

If you previously used Gemini API:

**Old (Gemini):**
```bash
GEMINI_API_KEY=your_key  # Not needed anymore
```

**New (Hybrid):**
```bash
GOOGLE_SEARCH_API_KEY=your_key  # Required
SEARCH_ENGINE_ID=your_id        # Required
```

**Code Changes:**
- ✅ Automatically handled
- ✅ No code changes needed
- ✅ OBV engine imports `price_fetcher_hybrid` automatically

---

**Last Updated:** January 2026
**Approach:** Hybrid (Google Search + HTML Scraping)
**Status:** Production Ready ✅
