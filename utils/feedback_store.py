import csv
import os
from datetime import datetime

FEEDBACK_FILE = "data/feedback_store.csv"

FIELDS = [
    "timestamp",
    "vehicle_id",
    "rating",
    "sentiment",
    "service_quality",
    "services_done",
    "service_cost",
    "raw_comments",
]

def save_feedback(record: dict):
    os.makedirs("data", exist_ok=True)
    file_exists = os.path.isfile(FEEDBACK_FILE)

    with open(FEEDBACK_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)

        if not file_exists:
            writer.writeheader()

        writer.writerow({
            "timestamp": datetime.now().isoformat(),
            "vehicle_id": record["vehicle_id"],
            "rating": record["rating"],
            "sentiment": record["sentiment"],
            "service_quality": record["service_quality"],
            "services_done": ", ".join(record["services_done"]),
            "service_cost": record["service_cost"],
            "raw_comments": record["raw_comments"],
        })
