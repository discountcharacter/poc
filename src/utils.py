def calculate_final_price(logic_price, scout_price, oracle_price):
    """
    Weighted Average Calculation.
    Rules:
    trio: Logic(0.3) + Scout(0.4) + AI(0.3)
    duo (No Scout): Logic(0.5) + AI(0.5)
    
    Extended defaults:
    duo (No AI): Logic(0.4) + Scout(0.6)
    duo (No Logic - unlikely): Scout(0.5) + AI(0.5)
    solo: 100% whichever is available
    """
    
    # Check what we have
    has_logic = logic_price is not None and logic_price > 0
    has_scout = scout_price is not None and scout_price > 0
    has_oracle = oracle_price is not None and oracle_price > 0
    
    # 1. All Three
    if has_logic and has_scout and has_oracle:
        final = (logic_price * 0.30) + (scout_price * 0.40) + (oracle_price * 0.30)
        return int(final)
        
    # 2. Logic + Oracle (Scout Failed)
    if has_logic and has_oracle and not has_scout:
        final = (logic_price * 0.50) + (oracle_price * 0.50)
        return int(final)
        
    # 3. Logic + Scout (Oracle Failed)
    if has_logic and has_scout and not has_oracle:
        final = (logic_price * 0.40) + (scout_price * 0.60)
        return int(final)
        
    # 4. Scout + Oracle (Logic Failed - Unlikely)
    if has_scout and has_oracle and not has_logic:
        final = (scout_price * 0.50) + (oracle_price * 0.50)
        return int(final)
        
    # 5. Solo Fallbacks
    if has_logic: return int(logic_price)
    if has_scout: return int(scout_price)
    if has_oracle: return int(oracle_price)
    
    return 0

def format_currency(value):
    """
    Format INR: ₹ 10,50,000
    """
    if not value: return "N/A"
    s, *d = str(value).partition(".")
    r = ",".join([s[x-2:x] for x in range(-3, -len(s), -2)][::-1] + [s[-3:]])
    return f"₹ {r}"
