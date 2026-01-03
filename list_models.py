import requests
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
response = requests.get(url)

if response.status_code == 200:
    for model in response.json().get('models', []):
        print(f"Name: {model['name']}")
        print(f"Supported Generation Methods: {model.get('supportedGenerationMethods')}")
        print("-" * 20)
else:
    print(f"Error: {response.status_code} - {response.text}")
