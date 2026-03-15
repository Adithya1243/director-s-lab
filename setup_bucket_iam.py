"""
Run this AFTER creating the bucket manually in GCP Console.
Sets public read + service-account admin IAM on the existing bucket.

  source backend/.venv/bin/activate
  python setup_bucket_iam.py
"""

import os
from dotenv import load_dotenv
load_dotenv("backend/.env")

from google.cloud import storage

PROJECT = os.environ["GOOGLE_CLOUD_PROJECT"]
BUCKET  = os.environ["GCS_BUCKET_NAME"]

client = storage.Client(project=PROJECT)
bucket = client.bucket(BUCKET)

# 1 — Enable uniform bucket-level access
bucket.reload()
bucket.iam_configuration.uniform_bucket_level_access_enabled = True
bucket.patch()
print("✓ Uniform bucket-level access enabled")

# 2 — Add allUsers:objectViewer (public reads)
policy = bucket.get_iam_policy(requested_policy_version=3)
policy.version = 3
members_viewer = set()
for b in policy.bindings:
    if b["role"] == "roles/storage.objectViewer":
        members_viewer = b["members"]
        break

if "allUsers" not in members_viewer:
    policy.bindings.append({
        "role":    "roles/storage.objectViewer",
        "members": {"allUsers"},
    })
    bucket.set_iam_policy(policy)
    print("✓ allUsers:objectViewer IAM binding added — objects are publicly readable")
else:
    print("✓ allUsers:objectViewer already present")

# 3 — Add service account as objectAdmin
SA = f"storyteller-agent@{PROJECT}.iam.gserviceaccount.com"
policy = bucket.get_iam_policy(requested_policy_version=3)
policy.version = 3
members_admin = set()
for b in policy.bindings:
    if b["role"] == "roles/storage.objectAdmin":
        members_admin = b["members"]
        break

sa_member = f"serviceAccount:{SA}"
if sa_member not in members_admin:
    policy.bindings.append({
        "role":    "roles/storage.objectAdmin",
        "members": {sa_member},
    })
    bucket.set_iam_policy(policy)
    print(f"✓ {SA} granted objectAdmin")
else:
    print(f"✓ {SA} already has objectAdmin")

print(f"\n✅ IAM setup complete on gs://{BUCKET}. Ready to generate scenes.")
