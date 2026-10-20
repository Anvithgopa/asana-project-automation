"""
Asana User Directory & Cross-Workspace GID Mapper
Retrieves workspace users and generates translation dictionaries between old and new GIDs.
"""

import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ASANA_ACCESS_TOKEN, WORKSPACE_GID, DATA_DIR

import asana
from asana.rest import ApiException

def extract_workspace_users(output_path=None):
    if not ASANA_ACCESS_TOKEN or not WORKSPACE_GID:
        print("❌ Error: ASANA_ACCESS_TOKEN and ASANA_WORKSPACE_GID are required.")
        return []

    configuration = asana.Configuration()
    configuration.access_token = ASANA_ACCESS_TOKEN
    client = asana.ApiClient(configuration)
    users_api = asana.UsersApi(client)

    try:
        users = list(users_api.get_users_for_workspace(WORKSPACE_GID, {"opt_fields": "gid,name,email"}))
        print(f"✅ Extracted {len(users)} users from workspace {WORKSPACE_GID}.")

        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(users, f, indent=2)
            print(f"📄 Saved user directory to: {output_path}")

        return users
    except ApiException as e:
        print(f"❌ Error extracting users: {e}")
        return []

if __name__ == "__main__":
    out_file = os.path.join(DATA_DIR, "workspace_users_export.json")
    extract_workspace_users(out_file)
