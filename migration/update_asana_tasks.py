"""
Batch Asana Task Updater & Synchronizer
Updates task assignees, custom fields, and properties in bulk across target projects.
"""

import sys
import os
import json
import time
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ASANA_ACCESS_TOKEN, LOG_DIR

import asana
from asana.rest import ApiException

configuration = asana.Configuration()
configuration.access_token = ASANA_ACCESS_TOKEN
api_client = asana.ApiClient(configuration) if ASANA_ACCESS_TOKEN else None
tasks_api = asana.TasksApi(api_client) if api_client else None

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = os.path.join(LOG_DIR, f"update_log_{timestamp}.txt")
FAILED_FILE = os.path.join(LOG_DIR, f"failed_updates_{timestamp}.json")

failed_updates = []

def log(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
    print(msg)

def update_task_properties(task_gid, update_dict):
    if not tasks_api:
        log("❌ Error: Asana API is not initialized.")
        return False

    body = {"data": update_dict}
    for attempt in range(4):
        try:
            tasks_api.update_task(body, task_gid)
            log(f"✅ Successfully updated task: {task_gid}")
            return True
        except ApiException as e:
            if e.status == 429:
                wait_time = int(e.headers.get("Retry-After", 60))
                log(f"⏳ Rate limit reached. Sleeping for {wait_time}s...")
                time.sleep(wait_time)
            else:
                log(f"❌ Error updating task {task_gid}: {e}")
                time.sleep(2 ** attempt)

    failed_updates.append({"task_gid": task_gid, "payload": update_dict})
    return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python update_asana_tasks.py <TASK_GID> [KEY=VALUE ...]")
        sys.exit(1)

    target_gid = sys.argv[1]
    properties = {}
    for arg in sys.argv[2:]:
        if "=" in arg:
            k, v = arg.split("=", 1)
            properties[k] = v

    if properties:
        update_task_properties(target_gid, properties)
    else:
        print("No properties provided to update.")
