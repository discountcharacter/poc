
import re

def test_regex():
    # Problematic snippet: number followed by a word starting with L ("Location")
    snippet1 = "Used Creta 96000 km Location: Hyderabad. Single owner."
    # Valid price snippet
    snippet2 = "Used Creta 2017 Model. Price is 8.5 Lakh. 1.6 SX variant."
    # Standalone 'L' match
    snippet3 = "Creta Petrol 2017, 8.5L price, excellent condition."
    
    # NEW STRICTOR REGEX
    price_pattern = re.compile(r"\b(\d{1,3}(?:\.\d{1,2})?)\s*(?:Lakh|Lakhs|L)\b", re.IGNORECASE)
    
    for i, text in enumerate([snippet1, snippet2, snippet3]):
        matches = price_pattern.findall(text)
        print(f"Test {i+1}: {text}")
        print(f"Matches: {matches}")
        if i == 0 and not matches:
            print("  SUCCESS: Correctly ignored false match with '96000 km Location'")
        elif i == 0 and matches:
            print("  FAILURE: Incorrectly matched")
    
    for match in matches:
        val = float(match[0])
        print(f"Found value: {val}")

if __name__ == "__main__":
    test_regex()
