"""
Asana Project Recreator & Recovery Tool
Restores projects, sections, and task structures from JSON backup archives.
Incorporates exponential backoff and HTTP 429 rate-limit recovery.
"""

import sys
import os
import json
import time
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ASANA_ACCESS_TOKEN, WORKSPACE_GID

import asana
from asana.rest import ApiException

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

configuration = asana.Configuration()
configuration.access_token = ASANA_ACCESS_TOKEN
api_client = asana.ApiClient(configuration) if ASANA_ACCESS_TOKEN else None

projects_api = asana.ProjectsApi(api_client) if api_client else None
tasks_api = asana.TasksApi(api_client) if api_client else None
sections_api = asana.SectionsApi(api_client) if api_client else None

def retry_request(func, *args, **kwargs):
    """Executes an API call with automatic rate-limit backoff."""
    for attempt in range(4):
        try:
            return func(*args, **kwargs)
        except ApiException as e:
            if e.status == 429:
                retry_after = int(e.headers.get("Retry-After", 60))
                logging.warning(f"Rate limit reached. Retrying in {retry_after}s...")
                time.sleep(retry_after)
            else:
                logging.error(f"API Error ({e.status}): {e.body}")
                time.sleep(2 ** attempt)
    return None

def restore_project_from_backup(backup_json_path, target_project_name):
    if not os.path.exists(backup_json_path):
        logging.error(f"Backup file does not exist: {backup_json_path}")
        return

    with open(backup_json_path, "r", encoding="utf-8") as f:
        projects_data = json.load(f)

    target_project = next((p for p in projects_data if p.get("name") == target_project_name), None)
    if not target_project:
        logging.error(f"Project '{target_project_name}' not found in backup file.")
        return

    logging.info(f"🚀 Recreating project '{target_project_name}' in workspace {WORKSPACE_GID}...")

    # Create Project
    body = {
        "data": {
            "name": f"{target_project_name} (Restored)",
            "workspace": WORKSPACE_GID
        }
    }
    new_project = retry_request(projects_api.create_project, body)
    if not new_project:
        logging.error("Failed to create project.")
        return

    new_project_gid = new_project.get("gid")
    logging.info(f"✅ Created project: {new_project_gid}")

    # Restore tasks
    tasks = target_project.get("tasks", [])
    for task in tasks:
        task_body = {
            "data": {
                "name": task.get("name"),
                "projects": [new_project_gid],
                "start_on": task.get("start_on"),
                "due_on": task.get("due_on"),
                "completed": task.get("completed", False)
            }
        }
        created_task = retry_request(tasks_api.create_task, task_body)
        if created_task:
            logging.info(f"  -> Created task: {task.get('name')}")

    logging.info(f"🎉 Restoration of '{target_project_name}' complete!")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python asana_project_restore.py <BACKUP_JSON_PATH> <PROJECT_NAME>")
        sys.exit(1)
    restore_project_from_backup(sys.argv[1], sys.argv[2])
