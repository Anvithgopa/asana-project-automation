"""
Asana Multi-Threaded Workspace Exporter
Extracts projects, custom fields, enum options, tasks, subtasks, and dependency graphs.
"""

import sys
import os

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ASANA_ACCESS_TOKEN, WORKSPACE_GID, DATA_DIR

import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import asana
from asana.rest import ApiException

if not ASANA_ACCESS_TOKEN:
    print("⚠️ Error: ASANA_ACCESS_TOKEN is not configured. Please set it in your .env file.")
    sys.exit(1)

# Asana SDK Setup
configuration = asana.Configuration()
configuration.access_token = ASANA_ACCESS_TOKEN
api_client = asana.ApiClient(configuration)
projects_api = asana.ProjectsApi(api_client)
tasks_api = asana.TasksApi(api_client)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_SUMMARY = os.path.join(DATA_DIR, f"asana_summary_{timestamp}.json")
OUTPUT_FULLDATA = os.path.join(DATA_DIR, f"asana_fullData_{timestamp}.json")

def paginate(api_method, opts):
    """Generic pagination handler for Asana SDK methods."""
    results = []
    response = api_method(opts)
    while True:
        results.extend(response)
        if not getattr(response, 'next_page', None):
            break
        opts["offset"] = response.next_page["offset"]
        response = api_method(opts)
    return results

def get_all_projects(workspace_gid):
    try:
        print(f"📦 Fetching projects for workspace {workspace_gid}...")
        opts = {
            "workspace": workspace_gid,
            "archived": False,
            "limit": 100,
            "opt_fields": "name,archived,color,completed,created_at,due_on,start_on,owner,custom_fields,members"
        }
        return paginate(projects_api.get_projects, opts)
    except ApiException as e:
        print(f"❌ Error fetching projects: {e}")
        return []

def get_tasks_for_project(project_gid):
    try:
        opts = {
            "limit": 100,
            "opt_fields": "name,start_on,due_on,completed,completed_at,assignee,assignee.name,custom_fields,dependencies,dependents,parent,parent.gid,num_subtasks"
        }
        return paginate(lambda o: tasks_api.get_tasks_for_project(project_gid, o), opts)
    except ApiException as e:
        print(f"❌ Error fetching tasks for project {project_gid}: {e}")
        return []

def get_subtasks(task_gid):
    try:
        opts = {
            "opt_fields": "name,start_on,due_on,completed,assignee,custom_fields,parent"
        }
        return list(tasks_api.get_subtasks_for_task(task_gid, opts))
    except ApiException as e:
        print(f"❌ Error fetching subtasks for task {task_gid}: {e}")
        return []

def export_workspace():
    if not WORKSPACE_GID:
        print("❌ Error: WORKSPACE_GID is required. Please set ASANA_WORKSPACE_GID in .env.")
        return

    projects = get_all_projects(WORKSPACE_GID)
    print(f"✅ Found {len(projects)} active projects.")

    full_export = []
    summary_export = []

    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_project = {executor.submit(get_tasks_for_project, p["gid"]): p for p in projects}
        for future in as_completed(future_to_project):
            project = future_to_project[future]
            tasks = future.result()
            print(f"  -> Project '{project.get('name')}' contains {len(tasks)} tasks.")

            project_record = {
                "gid": project.get("gid"),
                "name": project.get("name"),
                "task_count": len(tasks),
                "tasks": tasks
            }
            full_export.append(project_record)
            summary_export.append({
                "gid": project.get("gid"),
                "name": project.get("name"),
                "task_count": len(tasks)
            })

    with open(OUTPUT_SUMMARY, "w", encoding="utf-8") as f:
        json.dump(summary_export, f, indent=2)
    print(f"📄 Summary saved to: {OUTPUT_SUMMARY}")

    with open(OUTPUT_FULLDATA, "w", encoding="utf-8") as f:
        json.dump(full_export, f, indent=2)
    print(f"💾 Full backup saved to: {OUTPUT_FULLDATA}")

if __name__ == "__main__":
    export_workspace()
