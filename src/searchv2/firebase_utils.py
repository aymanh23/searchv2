import os
import json
from pathlib import Path
from datetime import datetime

import firebase_admin
from firebase_admin import credentials, storage, firestore

# Initialize Firebase when module is imported
if not firebase_admin._apps:
    cred_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
    cred_file = os.getenv("FIREBASE_CREDENTIALS_FILE")
    if cred_json:
        cred = credentials.Certificate(json.loads(cred_json))
    elif cred_file:
        cred = credentials.Certificate(cred_file)
    else:
        raise RuntimeError("Firebase credentials not provided. Set FIREBASE_CREDENTIALS_JSON or FIREBASE_CREDENTIALS_FILE.")

    firebase_admin.initialize_app(cred, {
        "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET")
    })

def upload_report(file_path: Path, patient_uuid: str) -> str:
    """Upload a PDF report to Firebase Storage and return its storage path."""
    bucket = storage.bucket()
    blob_path = f"patients/{patient_uuid}/reports/{file_path.name}"
    blob = bucket.blob(blob_path)
    blob.upload_from_filename(str(file_path))
    return blob_path

def log_report(patient_uuid: str, storage_path: str) -> None:
    """Log the uploaded report in Firestore under the patient's record."""
    db = firestore.client()
    doc_ref = db.collection("patients").document(patient_uuid).collection("reports").document()
    doc_ref.set({
        "path": storage_path,
        "timestamp": firestore.SERVER_TIMESTAMP,
    })
