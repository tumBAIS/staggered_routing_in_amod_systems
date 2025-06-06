import shutil
from pathlib import Path

# Set base paths
base_dir = Path(__file__).resolve().parent
source_root = base_dir / "0506_1050_CHECK_INSTANCES_COLLECTING_INSTANCES/results"
target_root = base_dir / "0406_1815_ALGO_PERFORMANCE_FUTURE_PAPER_TESTING_SMALL_SHORTCUTS/results"

for source_folder in source_root.glob("MAN100*"):
    instance_file = source_folder / "instance.json"
    routes_file = source_folder / "routes.json"

    if not instance_file.exists() and not routes_file.exists():
        print(f"⚠️  Skipping {source_folder.name}: Neither instance.json nor routes.json found.")
        continue

    # Extract prefix up to and including '_OFFLINE'
    name = source_folder.name
    offline_idx = name.find("_OFFLINE")
    if offline_idx == -1:
        print(f"⚠️  Skipping {name}: '_OFFLINE' not found.")
        continue

    prefix = name[:offline_idx + len("_OFFLINE")]

    # Match any folder in the target that starts with this prefix
    matching_folders = [f for f in target_root.iterdir()
                        if f.is_dir() and f.name.startswith(prefix)]

    if not matching_folders:
        print(f"❌ No matching target for prefix: {prefix}")
        continue
    if len(matching_folders) > 1:
        print(f"⚠️  Multiple matches for prefix: {prefix}, skipping to avoid ambiguity.")
        continue

    target_folder = matching_folders[0]

    # Copy instance.json if it exists
    if instance_file.exists():
        shutil.copy(instance_file, target_folder / "instance.json")
        print(f"✅ Copied {instance_file} → {target_folder / 'instance.json'}")

    # Copy routes.json if it exists
    if routes_file.exists():
        shutil.copy(routes_file, target_folder / "routes.json")
        print(f"✅ Copied {routes_file} → {target_folder / 'routes.json'}")
