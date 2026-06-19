import os
import json
import sys

def main():
    version_json_path = os.path.join(os.path.dirname(__file__), "version.json")
    version_txt_path = os.path.join(os.path.dirname(__file__), "version.txt")

    # Read base version
    if not os.path.exists(version_json_path):
        print(f"Error: {version_json_path} not found.")
        sys.exit(1)

    with open(version_json_path, "r") as f:
        version_data = json.load(f)

    major = version_data.get("major", 0)
    minor = version_data.get("minor", 5)
    patch = version_data.get("patch", 1)

    # Determine branch / context
    # GitHub actions sets GITHUB_REF (e.g. refs/heads/main or refs/pull/123/merge)
    github_ref = os.environ.get("GITHUB_REF", "")
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    
    print(f"Base version: {major}.{minor}.{patch}")
    print(f"GITHUB_REF: '{github_ref}', GITHUB_EVENT_NAME: '{event_name}'")

    is_main = (github_ref == "refs/heads/main" or github_ref == "main")
    
    # Support command line overrides for testing/manual builds
    if len(sys.argv) > 1:
        branch_arg = sys.argv[1].lower()
        if branch_arg in ["main", "refs/heads/main"]:
            is_main = True
        else:
            is_main = False

    if is_main:
        # Bump minor, reset patch
        minor += 1
        patch = 0
        print("Bumping minor version (production build).")
    else:
        # Bump patch
        patch += 1
        print("Bumping patch version (test/feature build).")

    version_str = f"{major}.{minor}.{patch}"
    print(f"Calculated version: {version_str}")

    # Write to version.txt
    with open(version_txt_path, "w") as f:
        f.write(version_str.strip() + "\n")
    print(f"Successfully wrote {version_str} to {version_txt_path}")

if __name__ == "__main__":
    main()
