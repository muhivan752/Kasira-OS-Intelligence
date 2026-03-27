import asyncio
import httpx
import uuid
import time
import random
from datetime import datetime, timezone

# Configuration
API_URL = "http://localhost:8000"
NUM_CLIENTS = 5
NUM_ITERATIONS = 10
SYNC_INTERVAL = 0.5 # seconds

# Mock Data
BRAND_ID = "00000000-0000-0000-0000-000000000000" # Replace with actual brand ID if needed
OUTLET_ID = "00000000-0000-0000-0000-000000000000" # Replace with actual outlet ID if needed
USER_TOKEN = "your_test_token_here" # Replace with a valid token

def generate_hlc(node_id):
    timestamp = int(time.time() * 1000)
    return f"{timestamp}:0:{node_id}"

async def simulate_client(client_id: int):
    node_id = f"client_{client_id}"
    last_sync_hlc = None
    
    # We will simulate creating products and orders
    local_products = {}
    
    async with httpx.AsyncClient(base_url=API_URL, headers={"Authorization": f"Bearer {USER_TOKEN}"}) as client:
        for i in range(NUM_ITERATIONS):
            print(f"[Client {client_id}] Iteration {i+1}/{NUM_ITERATIONS}")
            
            # 1. Generate some local changes
            changes = {
                "products": [],
                "orders": [],
                "order_items": []
            }
            
            # Create a new product occasionally
            if random.random() < 0.3:
                prod_id = str(uuid.uuid4())
                prod = {
                    "id": prod_id,
                    "brand_id": BRAND_ID,
                    "name": f"Product {client_id}-{i}",
                    "price": random.randint(10000, 50000),
                    "is_active": True,
                    "hlc": generate_hlc(node_id)
                }
                local_products[prod_id] = prod
                changes["products"].append(prod)
                
            # Update an existing product occasionally
            if local_products and random.random() < 0.5:
                prod_id = random.choice(list(local_products.keys()))
                local_products[prod_id]["price"] += 1000
                local_products[prod_id]["hlc"] = generate_hlc(node_id)
                changes["products"].append(local_products[prod_id])
                
            # 2. Sync with server
            payload = {
                "node_id": node_id,
                "last_sync_hlc": last_sync_hlc,
                "changes": changes
            }
            
            try:
                response = await client.post("/api/sync", json=payload)
                if response.status_code == 200:
                    data = response.json()
                    last_sync_hlc = data.get("last_sync_hlc")
                    
                    # Apply pulled changes to local state (simplified)
                    pulled_products = data.get("changes", {}).get("products", [])
                    for p in pulled_products:
                        local_products[p["id"]] = p
                        
                    print(f"[Client {client_id}] Sync successful. Pulled {len(pulled_products)} products.")
                else:
                    print(f"[Client {client_id}] Sync failed: {response.status_code} - {response.text}")
            except Exception as e:
                print(f"[Client {client_id}] Error during sync: {e}")
                
            await asyncio.sleep(SYNC_INTERVAL)

async def main():
    print("Starting CRDT Sync Stress Test...")
    tasks = [simulate_client(i) for i in range(NUM_CLIENTS)]
    await asyncio.gather(*tasks)
    print("Stress Test Completed.")

if __name__ == "__main__":
    asyncio.run(main())
