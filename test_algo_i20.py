from src.procurement_algo import ProcurementAlgo

# User Case: i20 2019, 33k KM, Top Model
# Market Price from Agent was 765,000 (High Range)
res = ProcurementAlgo.calculate_procurement_price(
    market_price=765000, 
    make="Hyundai", 
    model="i20", 
    year=2019, 
    km=33471, 
    owners=1, 
    condition="Good"
)
print(res)
