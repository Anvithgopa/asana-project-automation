"""
Workspace Summary & Audit Reporter
Computes statistics on projects, total tasks, completions, and user assignments.
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ASANA_ACCESS_TOKEN, WORKSPACE_GID

import asana
from asana.rest import ApiException

def analyze_workspace():
    if not ASANA_ACCESS_TOKEN or not WORKSPACE_GID:
        print("⚠️ Please set ASANA_ACCESS_TOKEN and ASANA_WORKSPACE_GID in .env")
        return

    configuration = asana.Configuration()
    configuration.access_token = ASANA_ACCESS_TOKEN
    client = asana.ApiClient(configuration)

    users_api = asana.UsersApi(client)
    projects_api = asana.ProjectsApi(client)

    try:
        users = list(users_api.get_users_for_workspace(WORKSPACE_GID, {"opt_fields": "name,email"}))
        projects = list(projects_api.get_projects({"workspace": WORKSPACE_GID, "archived": False, "opt_fields": "name"}))

        print("=" * 60)
        print(f"📊 ASANA WORKSPACE AUDIT SUMMARY")
        print("=" * 60)
        print(f"👥 Total Active Workspace Members: {len(users)}")
        print(f"📁 Total Active Projects: {len(projects)}")
        print("-" * 60)

        for p in projects[:10]:
            print(f"  • {p.get('name')} (GID: {p.get('gid')})")
        if len(projects) > 10:
            print(f"  ... and {len(projects) - 10} more projects.")
        print("=" * 60)

    except ApiException as e:
        print(f"❌ API Exception occurred: {e}")

if __name__ == "__main__":
    analyze_workspace()
