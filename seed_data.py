# seed_data.py
import datetime
import google.auth
from google.cloud import firestore

# Hardcode the GCP Project ID as a string explicitly
FIRESTORE_PROJECT_ID = "qwiklabs-gcp-03-cc7caa2edc63"

def seed_database():
    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    db = firestore.Client(project=FIRESTORE_PROJECT_ID, credentials=credentials)
    print(f"Connecting to Firestore for project: {FIRESTORE_PROJECT_ID}")

    # Seed ER Beds collection
    beds_ref = db.collection("er_beds")
    beds_data = [
        {
            "bed_id": "BED-101",
            "department": "Trauma",
            "status": "Occupied",
            "patient_id": "P-801",
            "assigned_staff": "Dr. Miller / Nurse Sarah",
            "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat()
        },
        {
            "bed_id": "BED-102",
            "department": "Trauma",
            "status": "Available",
            "patient_id": None,
            "assigned_staff": "Unassigned",
            "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat()
        },
        {
            "bed_id": "BED-201",
            "department": "General ER",
            "status": "Occupied",
            "patient_id": "P-802",
            "assigned_staff": "Dr. Davis / Nurse Carlos",
            "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat()
        },
        {
            "bed_id": "BED-202",
            "department": "General ER",
            "status": "Available",
            "patient_id": None,
            "assigned_staff": "Unassigned",
            "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat()
        },
        {
            "bed_id": "BED-301",
            "department": "Pediatrics",
            "status": "Available",
            "patient_id": None,
            "assigned_staff": "Dr. Chen / Nurse Amanda",
            "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat()
        },
        {
            "bed_id": "BED-401",
            "department": "Cardiac",
            "status": "Cleaning",
            "patient_id": None,
            "assigned_staff": "Staff On Duty",
            "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
    ]

    for bed in beds_data:
        beds_ref.document(bed["bed_id"]).set(bed)
        print(f"Seeded bed {bed['bed_id']} ({bed['department']}) - {bed['status']}")

    # Seed Patient Queue collection
    queue_ref = db.collection("patient_queue")
    queue_data = [
        {
            "patient_id": "P-901",
            "patient_name": "Jane Doe",
            "chief_complaint": "Severe chest pain & shortness of breath",
            "esi_level": 1,
            "wait_time_minutes": 5,
            "status": "In Triage",
            "registered_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        },
        {
            "patient_id": "P-902",
            "patient_name": "Robert Smith",
            "chief_complaint": "Open compound fracture of right forearm",
            "esi_level": 2,
            "wait_time_minutes": 15,
            "status": "Waiting",
            "registered_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        },
        {
            "patient_id": "P-903",
            "patient_name": "Alice Johnson",
            "chief_complaint": "Persistent high fever 103F & abdominal cramps",
            "esi_level": 3,
            "wait_time_minutes": 35,
            "status": "Waiting",
            "registered_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        },
        {
            "patient_id": "P-904",
            "patient_name": "Michael Brown",
            "chief_complaint": "Minor laceration on left thumb",
            "esi_level": 4,
            "wait_time_minutes": 60,
            "status": "Waiting",
            "registered_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
    ]

    for patient in queue_data:
        queue_ref.document(patient["patient_id"]).set(patient)
        print(f"Seeded patient {patient['patient_id']} ({patient['patient_name']}) - ESI Level {patient['esi_level']}")

    print("Firestore database seeding completed successfully!")

if __name__ == "__main__":
    seed_database()
