"""
One-time GCS bucket setup script.
Run from the backend venv:
  source backend/.venv/bin/activate
  python setup_bucket.py
"""

import os
from dotenv import load_dotenv
load_dotenv("backend/.env")

from google.cloud import storage

PROJECT  = os.environ["GOOGLE_CLOUD_PROJECT"]
BUCKET   = os.environ["GCS_BUCKET_NAME"]
REGION   = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")

client = storage.Client(project=PROJECT)

# 1 — Create bucket (skip if already exists)
try:
    bucket = client.create_bucket(BUCKET, location=REGION)
    print(f"✓ Created bucket: gs://{BUCKET}")
except Exception as e:
    if "already own" in str(e) or "conflict" in str(e).lower() or "409" in str(e):
        bucket = client.bucket(BUCKET)
        print(f"✓ Bucket already exists: gs://{BUCKET}")
    else:
        raise

# 2 — Enable uniform bucket-level access
bucket.iam_configuration.uniform_bucket_level_access_enabled = True
bucket.patch()
print("✓ Uniform bucket-level access enabled")

# 3 — Add allUsers:objectViewer (public reads)
policy = bucket.get_iam_policy(requested_policy_version=3)
policy.bindings.append({
    "role":    "roles/storage.objectViewer",
    "members": {"allUsers"},
})
bucket.set_iam_policy(policy)
print("✓ allUsers:objectViewer IAM binding added — objects are publicly readable")

# 4 — Add service account as objectAdmin
SA = f"storyteller-agent@{PROJECT}.iam.gserviceaccount.com"
policy = bucket.get_iam_policy(requested_policy_version=3)
policy.bindings.append({
    "role":    "roles/storage.objectAdmin",
    "members": {f"serviceAccount:{SA}"},
})
bucket.set_iam_policy(policy)
print(f"✓ {SA} granted objectAdmin")

print("\n✅ Bucket setup complete. You're ready to generate scenes with real images.")
