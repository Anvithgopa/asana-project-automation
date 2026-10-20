"""
Asana Webhook & Real-Time Event Listener
Listens for resource update events (task modifications, date changes) to trigger DAG schedule cascades.
"""

import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ASANA_ACCESS_TOKEN, WORKSPACE_GID

import asana
from asana.rest import ApiException

def listen_to_events(resource_gid):
    if not ASANA_ACCESS_TOKEN:
        print("❌ Error: ASANA_ACCESS_TOKEN is required.")
        return

    configuration = asana.Configuration()
    configuration.access_token = ASANA_ACCESS_TOKEN
    client = asana.ApiClient(configuration)
    events_api = asana.EventsApi(client)

    print(f"👂 Polling events for resource GID: {resource_gid}...")

    try:
        # Initial call establishes sync token
        response = events_api.get_events({"resource": resource_gid})
        sync_token = response.get("sync")
        print(f"🔄 Initialized sync token: {sync_token}")

        # Polling subsequent events
        events_response = events_api.get_events({"resource": resource_gid, "sync": sync_token})
        events = events_response.get("data", [])
        print(f"⚡ Received {len(events)} new events.")

        for event in events:
            action = event.get("action")
            user = event.get("user", {}).get("name", "Unknown")
            print(f"  -> Event: {action} on resource {event.get('resource', {}).get('gid')} by {user}")

    except ApiException as e:
        print(f"❌ Error polling events: {e}")

if __name__ == "__main__":
    target_resource = sys.argv[1] if len(sys.argv) > 1 else WORKSPACE_GID
    if not target_resource:
        print("Usage: python event_listener.py <RESOURCE_GID>")
        sys.exit(1)
    listen_to_events(target_resource)
