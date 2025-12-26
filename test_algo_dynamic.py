from src.procurement_algo import ProcurementAlgo

print("=== Case 1: Magnite 2024 (New Car) ===")
# Market 7,80,000. Target Buy ~6,30,000 (~80%). Age = 1.
res1 = ProcurementAlgo.calculate_procurement_price(780000, "Nissan", "Magnite", 2024, 11087, 1, "Good")
price1 = res1['final_procurement_price']
print(f"Magnite 2024: Market 7.8L -> Algo {price1} (Target ~6.30L)")
print(f"Details: {res1['details']}\n")

print("=== Case 2: Wagon R 2019 (Old Car) ===")
# Market 5,35,000. Target Buy ~3,45,000 (~65%). Age = 6.
res2 = ProcurementAlgo.calculate_procurement_price(535000, "Maruti", "Wagon R", 2019, 18537, 1, "Good")
price2 = res2['final_procurement_price']
print(f"Wagon R 2019: Market 5.35L -> Algo {price2} (Target ~3.45L)")
