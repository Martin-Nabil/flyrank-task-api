import json
import requests

with open("evals/cases.json", "r", encoding="utf-8") as f:
    cases = json.load(f)

results = []
for case in cases:
    response = requests.post(
        "http://localhost:8001/enrich",
        json={"title": case["title"], "description": case["description"]}
    )

    if response.status_code == 200:
        data = response.json()
        actual = data["category"]
        matched = actual == case["expected_category"]
    else:
        actual = f"ERROR {response.status_code}"
        matched = False

    results.append({
        "id": case["id"],
        "title": case["title"],
        "expected": case["expected_category"],
        "actual": actual,
        "matched": matched
    })

num_matched = sum(1 for r in results if r["matched"])
total = len(results)

print(f"\n{num_matched} out of {total} matched ({num_matched/total*100:.0f}%)\n")

for r in results:
    status = "OK" if r["matched"] else "FAIL"
    print(f"[{status}] #{r['id']} \"{r['title']}\" expected={r['expected']} actual={r['actual']}")