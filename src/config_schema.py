"""Configuration schema definition for the add-on dialog."""

# Configuration schema defining fields for the dialog
CONFIG_SCHEMA = {
    "api_token": {
        "type": "text",
        "label": "API Token",
        "description": "Your Toggl Track API token",
    },
    "workspace_id": {
        "type": "text",
        "label": "Workspace ID",
        "description": "Your Toggl Track workspace ID (numeric)",
    },
    "project_id": {
        "type": "text",
        "label": "Project ID",
        "description": "Your Toggl Track project ID (numeric)",
    },
    "description": {
        "type": "text",
        "label": "Description",
        "description": "Description for time entries (optional)",
    },
    "auto_sync": {
        "type": "checkbox",
        "label": "Auto-sync on Anki sync",
        "description": "Automatically sync review time when Anki syncs",
    },
    "timezone": {
        "type": "dropdown",
        "label": "Timezone",
        "description": "Timezone for time entries",
    },
}
