# Local Setup Guide - Car Valuation Portal

## Prerequisites

- **Python 3.9 or higher** (recommended: 3.10)
- **Git** installed
- **API Keys** (see API Configuration section)

---

## Step-by-Step Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd spectral-blazar
```

### 2. Create Python Virtual Environment

**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**On Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Note:** If you encounter errors with `scikit-learn==1.3.2`, try:
```bash
pip install scikit-learn==1.3.2 --no-cache-dir
```

### 4. Configure Environment Variables

Create a `.env` file in the project root directory:

```bash
# Copy the example file
cp .env.example .env
```

Edit `.env` with your actual API keys:

```
GOOGLE_API_KEY=your_actual_gemini_api_key
GOOGLE_SEARCH_API_KEY=your_actual_google_search_key
SEARCH_ENGINE_ID=your_search_engine_cx_id
```

**Getting API Keys:**
- **Gemini API Key**: Get from [Google AI Studio](https://makersuite.google.com/app/apikey)
- **Google Search API Key**: Get from [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
- **Search Engine ID**: Create at [Programmable Search Engine](https://programmablesearchengine.google.com/)

### 5. Verify Data & Model Files

Ensure these directories exist with files:
```
data/
  ├── real_sales_data.csv
  └── procurement_history.csv

models/
  └── ensemble/
      ├── (trained model files)
```

If `models/ensemble/` is empty, you need to train the models first:

```bash
python src/train_ensemble.py
```

### 6. Run the Application

```bash
streamlit run main.py
```

The app should open in your browser at `http://localhost:8501`

---

## Common Errors & Fixes

### Error: "ModuleNotFoundError: No module named 'streamlit'"
**Fix:** Ensure virtual environment is activated and packages are installed
```bash
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### Error: "FileNotFoundError: [Errno 2] No such file or directory: 'models/ensemble/...'"
**Fix:** Train the models first
```bash
python src/train_ensemble.py
```

### Error: "google.api_core.exceptions.PermissionDenied: API key not valid"
**Fix:** 
1. Double-check your API keys in `.env`
2. Ensure no extra spaces or quotes
3. Verify API is enabled in Google Cloud Console

### Error: "ImportError: DLL load failed" (Windows)
**Fix:** Install Visual C++ Redistributable
- Download from [Microsoft](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist)

### Error: Agent Portal shows "Missing Google Search API Key/CX"
**Fix:** 
1. Verify `.env` has all three keys
2. Restart Streamlit after modifying `.env`

---

## Testing the Setup

### 1. Test Main App
```bash
streamlit run main.py
```
Navigate to "Intelligent Pricing Engine" and try a sample valuation.

### 2. Test Agent Portal
- Go to sidebar → "🤖 Agent-1: Intelligent Valuation"
- Try valuing: **2020 Hyundai Creta SX Petrol, 50000 KM**

### 3. Test Procurement Algorithm (Optional)
```bash
python test_algo_dynamic.py
```

---

## Project Structure

```
spectral-blazar/
├── main.py                    # Main Streamlit app
├── pages/
│   └── 1_Agent_Valuation.py   # Agent Portal
├── src/
│   ├── agent_graph.py         # Valuation Agent
│   ├── procurement_algo.py    # Procurement pricing
│   ├── ensemble_predictor.py  # ML ensemble
│   └── train_ensemble.py      # Model training
├── data/                      # CSV datasets
├── models/                    # Trained ML models
├── requirements.txt           # Python dependencies
└── .env                       # API keys (you create this)
```

---

## Troubleshooting Checklist

- [ ] Python 3.9+ installed (`python --version`)
- [ ] Virtual environment activated (see `(venv)` in terminal)
- [ ] All packages installed (`pip list | grep streamlit`)
- [ ] `.env` file exists with valid API keys
- [ ] Models trained (check `models/ensemble/` has files)
- [ ] Port 8501 not in use by another app

---

## Need Help?

If errors persist:
1. Share the **exact error message** (full traceback)
2. Share your **Python version** (`python --version`)
3. Check if running on **Windows/Mac/Linux**

Common log location: Terminal output when running `streamlit run main.py`
