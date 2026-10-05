import requests, sys

BASE = "http://localhost:8000/api"

# Clean up and create a test fact
r = requests.get(f"{BASE}/facts")
for f in r.json():
    requests.delete(f"{BASE}/facts/{f['id']}")

# Create a fact
fact_data = {
    "name": "test_fact_run",
    "source_table": "stg_vendas",
    "target_table": "fato_test_run",
    "grain": "test",
    "measures": ["quantidade", "total"],
    "mode": "visual",
    "custom_sql": None,
    "status": "pending"
}
r = requests.post(f"{BASE}/facts", json=fact_data)
print(f"Create: {r.status_code}")
fact_id = r.json()["id"]

# Run the fact - this is where the 500 occurs
r = requests.post(f"{BASE}/facts/{fact_id}/run")
print(f"Run: {r.status_code}")
print(f"Response: {r.text}")

# Check if error is about ExecutionLog
r2 = requests.get(f"{BASE}/facts/{fact_id}")
print(f"Fact status: {r2.json().get('status')}")
