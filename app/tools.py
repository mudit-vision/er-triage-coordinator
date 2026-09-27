# app/tools.py
import base64
import datetime
import json
import os
import urllib.parse
import urllib.request
import uuid
import google.auth
from google import genai
from google.genai import types
from google.cloud import firestore, storage
from google.adk.tools import ToolContext

# Hardcode GCP Project ID & Storage Bucket explicitly as strings
FIRESTORE_PROJECT_ID = "qwiklabs-gcp-03-cc7caa2edc63"
GCS_BUCKET_NAME = "er-triage-assets-qwiklabs-gcp-03-cc7caa2edc63"

# Initialize credentials and Firestore client
credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
db = firestore.Client(project=FIRESTORE_PROJECT_ID, credentials=credentials)


def recommend_triage_level(chief_complaint: str, pain_scale: int, vital_signs: str) -> str:
    """Recommends an Emergency Severity Index (ESI 1-5) priority level based on complaint, pain, and vitals.

    Args:
        chief_complaint: Primary reason for ER visit (e.g. chest pain, fracture, fever).
        pain_scale: Self-reported pain score from 0 to 10.
        vital_signs: Vitals summary (e.g. 'BP 120/80, HR 72, SpO2 98%').

    Returns:
        A string recommending the ESI Level (1-5) and clinical priority category.
    """
    complaint_lower = chief_complaint.lower()
    if any(k in complaint_lower for k in ["chest pain", "unresponsive", "cardiac", "stroke", "severe dyspnea"]):
        desc = "ESI Level 1 (Immediate - Life-threatening)"
    elif pain_scale >= 8 or any(k in complaint_lower for k in ["fracture", "high fever", "severe pain", "bleeding"]):
        desc = "ESI Level 2 (Emergency - High risk / severe distress)"
    elif pain_scale >= 5 or "fever" in complaint_lower or "cramps" in complaint_lower:
        desc = "ESI Level 3 (Urgent - Requires multiple resources)"
    elif pain_scale >= 2:
        desc = "ESI Level 4 (Less Urgent - Requires one resource)"
    else:
        desc = "ESI Level 5 (Non-Urgent - Routine / minimal resources)"

    return f"Recommended Priority: {desc}. Chief complaint: '{chief_complaint}', Pain score: {pain_scale}/10, Vitals: '{vital_signs}'."


def get_bed_status(department: str = "") -> str:
    """Queries current ER bed availability and occupancy status across departments.

    Args:
        department: Optional filter for department name (e.g. 'Trauma', 'General ER', 'Pediatrics', 'Cardiac').

    Returns:
        A formatted summary string listing matching ER beds and their availability status.
    """
    try:
        beds_ref = db.collection("er_beds")
        docs = list(beds_ref.stream())
        if not docs:
            return "No bed records found in Firestore."

        results = []
        for doc in docs:
            data = doc.to_dict()
            dept = data.get("department", "General")
            if department and department.lower() not in dept.lower():
                continue
            bed_id = data.get("bed_id", doc.id)
            status = data.get("status", "Unknown")
            patient = data.get("patient_id") or "None"
            staff = data.get("assigned_staff", "Unassigned")
            results.append(f"• {bed_id} ({dept}): Status='{status}', Patient={patient}, Staff='{staff}'")

        if not results:
            return f"No ER beds found matching department filter '{department}'."

        return "Current ER Bed Status:\n" + "\n".join(results)
    except Exception as e:
        return f"Error fetching bed status from Firestore: {str(e)}"


def update_bed_status(bed_id: str, status: str, patient_id: str = "", assigned_staff: str = "") -> str:
    """Updates the status and assignment details for a specific ER bed document in Firestore.

    Args:
        bed_id: ID of the bed to update (e.g. 'BED-101', 'BED-201').
        status: New status ('Available', 'Occupied', 'Cleaning', 'Reserved').
        patient_id: Optional patient ID assigned to this bed (e.g. 'P-901').
        assigned_staff: Optional staff assigned to this bed (e.g. 'Nurse Sarah').

    Returns:
        Confirmation string indicating the update result.
    """
    try:
        doc_ref = db.collection("er_beds").document(bed_id)
        doc = doc_ref.get()
        if not doc.exists:
            return f"Bed ID '{bed_id}' not found in Firestore."

        update_data = {
            "status": status,
            "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        if patient_id:
            update_data["patient_id"] = patient_id
        elif status.lower() == "available":
            update_data["patient_id"] = None

        if assigned_staff:
            update_data["assigned_staff"] = assigned_staff

        doc_ref.update(update_data)
        return f"Successfully updated bed '{bed_id}' to status '{status}' in Firestore."
    except Exception as e:
        return f"Error updating bed status in Firestore: {str(e)}"


def get_patient_queue(status: str = "") -> str:
    """Queries the patient triage queue in Firestore.

    Args:
        status: Optional filter by patient queue status (e.g. 'Waiting', 'In Triage', 'Treated').

    Returns:
        A formatted list string of patients in the ER queue with ESI priority levels.
    """
    try:
        queue_ref = db.collection("patient_queue")
        docs = list(queue_ref.stream())
        if not docs:
            return "No patient queue records found in Firestore."

        results = []
        for doc in docs:
            data = doc.to_dict()
            p_status = data.get("status", "Waiting")
            if status and status.lower() not in p_status.lower():
                continue
            p_id = data.get("patient_id", doc.id)
            name = data.get("patient_name", "Unknown")
            complaint = data.get("chief_complaint", "N/A")
            esi = data.get("esi_level", "N/A")
            wait = data.get("wait_time_minutes", 0)
            results.append(f"• [{p_id}] {name} (ESI {esi}) - Complaint: '{complaint}', Wait: {wait} mins, Status: '{p_status}'")

        if not results:
            return f"No patients found matching queue status filter '{status}'."

        return "Current Patient Triage Queue:\n" + "\n".join(results)
    except Exception as e:
        return f"Error fetching patient queue from Firestore: {str(e)}"


def add_patient_to_queue(patient_name: str, chief_complaint: str, esi_level: int) -> str:
    """Adds a new patient to the ER triage queue document collection in Firestore.

    Args:
        patient_name: Full name of the patient.
        chief_complaint: Reason for ER visit / chief complaint.
        esi_level: Emergency Severity Index priority level (1 = Critical/Immediate, 5 = Non-Urgent).

    Returns:
        Confirmation message with assigned Patient ID.
    """
    try:
        new_id = f"P-{uuid.uuid4().hex[:4].upper()}"
        patient_doc = {
            "patient_id": new_id,
            "patient_name": patient_name,
            "chief_complaint": chief_complaint,
            "esi_level": esi_level,
            "wait_time_minutes": 0,
            "status": "Waiting",
            "registered_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        db.collection("patient_queue").document(new_id).set(patient_doc)
        return f"Successfully added patient '{patient_name}' (ID: {new_id}, ESI Level: {esi_level}) to Firestore triage queue."
    except Exception as e:
        return f"Error adding patient to queue in Firestore: {str(e)}"


def calculate_department_wait_times(department: str = "") -> str:
    """Calculates estimated wait times and queue metrics across ER departments based on Firestore data.

    Args:
        department: Optional filter for department name (e.g. 'Trauma', 'General ER', 'Pediatrics', 'Cardiac').

    Returns:
        A formatted summary string of estimated wait times, bed availability, and queued patients per department.
    """
    try:
        queue_docs = list(db.collection("patient_queue").stream())
        bed_docs = list(db.collection("er_beds").stream())

        dept_queues = {}
        for doc in queue_docs:
            data = doc.to_dict()
            if data.get("status") == "Waiting":
                esi = data.get("esi_level", 3)
                wait = data.get("wait_time_minutes", 15)
                dept = "Trauma" if esi <= 2 else "General ER"

                if department and department.lower() not in dept.lower():
                    continue

                if dept not in dept_queues:
                    dept_queues[dept] = []
                dept_queues[dept].append((esi, wait))

        dept_beds = {}
        for doc in bed_docs:
            data = doc.to_dict()
            dept = data.get("department", "General ER")
            if department and department.lower() not in dept.lower():
                continue
            if dept not in dept_beds:
                dept_beds[dept] = {"available": 0, "occupied": 0}
            if data.get("status") == "Available":
                dept_beds[dept]["available"] += 1
            else:
                dept_beds[dept]["occupied"] += 1

        all_depts = set(dept_queues.keys()).union(set(dept_beds.keys()))
        if not all_depts:
            return "No department queue or bed data found in Firestore."

        summary = []
        for d in sorted(all_depts):
            q = dept_queues.get(d, [])
            b = dept_beds.get(d, {"available": 0, "occupied": 0})
            q_count = len(q)
            avg_wait = round(sum(w for _, w in q) / q_count) if q_count > 0 else 0
            avail = b["available"]
            occupied = b["occupied"]

            est_wait = max(avg_wait, q_count * 20 if avail == 0 else q_count * 10)
            summary.append(
                f"• {d}: {q_count} waiting patients, {avail} beds available, {occupied} occupied. "
                f"Est. Wait Time: ~{est_wait} mins."
            )

        return "Emergency Department Estimated Wait Times:\n" + "\n".join(summary)
    except Exception as e:
        return f"Error calculating wait times from Firestore: {str(e)}"


def get_drug_safety_info(drug_name: str) -> str:
    """Queries official US FDA drug safety label information including uses, purpose, and warnings.

    Args:
        drug_name: Name of the drug or active ingredient (e.g. 'ibuprofen', 'acetaminophen', 'aspirin', 'epinephrine').

    Returns:
        Formatted summary string of official FDA warnings, indications, and clinical purpose.
    """
    try:
        api_key = os.getenv("OPENFDA_API_KEY", "")
        query = f'openfda.generic_name:"{drug_name}"'
        params = {"search": query, "limit": 1}
        if api_key:
            params["api_key"] = api_key

        url = "https://api.fda.gov/drug/label.json?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        if not data.get("results"):
            return f"No official FDA drug label found for '{drug_name}'."

        res = data["results"][0]
        purpose = res.get("purpose", ["N/A"])[0] if res.get("purpose") else "N/A"
        uses = res.get("indications_and_usage", ["N/A"])[0] if res.get("indications_and_usage") else "N/A"
        warnings = res.get("warnings", ["N/A"])[0] if res.get("warnings") else "N/A"

        if len(warnings) > 350:
            warnings = warnings[:350] + "..."

        return (
            f"Official FDA Drug Safety Information for '{drug_name}':\n"
            f"• Purpose: {purpose}\n"
            f"• Indications/Uses: {uses}\n"
            f"• Warnings & Risk Summary: {warnings}"
        )
    except Exception as e:
        return f"Error fetching FDA drug safety info for '{drug_name}': {str(e)}"


def generate_er_floorplan_image(prompt: str, tool_context: ToolContext = None) -> str:
    """Generates a visual floor plan or layout diagram for the ER department using gemini-3.1-flash-lite-image model in global region.

    Saves the image as an artifact in Playground and uploads image bytes directly to public Cloud Storage.

    Args:
        prompt: Detailed description of the ER floorplan image to generate (e.g. 'Color-coded ER floorplan diagram showing occupied trauma beds and available pediatric beds').

    Returns:
        The public HTTPS URL of the uploaded image in Cloud Storage.
    """
    try:
        genai_client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT_ID, location="global")
        response = genai_client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"]
            )
        )

        if not response.candidates or not response.candidates[0].content.parts:
            return "Failed to generate image: no candidate image parts returned."

        image_part = response.candidates[0].content.parts[0]
        image_bytes = image_part.inline_data.data
        mime_type = image_part.inline_data.mime_type or "image/png"
        ext = "jpg" if "jpeg" in mime_type.lower() else "png"
        filename = f"er_floorplan_{uuid.uuid4().hex[:6]}.{ext}"

        # 1. Save artifact to Playground ToolContext
        if tool_context:
            tool_context.save_artifact(filename=filename, artifact=image_part)

        # 2. Upload image bytes directly to public Cloud Storage bucket
        storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"
        return f"Successfully generated ER floorplan & departmental wait times dashboard image!\n\n![ER Floorplan & Wait Times Dashboard]({public_url})\n\nPublic Storage URL: {public_url}"
    except Exception as e:
        return f"Error generating or uploading ER floorplan image: {str(e)}"


def generate_departmental_wait_times_dashboard_image(prompt: str = "Real time ER departmental wait times dashboard displaying Trauma, Cardiac, Pediatrics, and General ER metrics", tool_context: ToolContext = None) -> str:
    """Generates a visual real-time departmental wait times dashboard image displaying queue metrics, bed occupancy, and wait times per department using gemini-3.1-flash-lite-image model in global region.

    Saves the image as an artifact in Playground and uploads image bytes directly to public Cloud Storage.

    Args:
        prompt: Detailed description of the departmental wait times dashboard image to generate.

    Returns:
        The Markdown image tag and public HTTPS URL of the uploaded image in Cloud Storage.
    """
    try:
        genai_client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT_ID, location="global")
        full_prompt = f"Infographic dashboard displaying emergency department real time wait times, queue metrics, and bed capacity for Trauma Unit, Cardiac Care, Pediatrics, and General ER. Clean hospital UI metrics card layout: {prompt}"
        response = genai_client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=full_prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"]
            )
        )

        if not response.candidates or not response.candidates[0].content.parts:
            return "Failed to generate wait times dashboard image: no candidate image parts returned."

        image_part = response.candidates[0].content.parts[0]
        image_bytes = image_part.inline_data.data
        mime_type = image_part.inline_data.mime_type or "image/png"
        ext = "jpg" if "jpeg" in mime_type.lower() else "png"
        filename = f"wait_times_dashboard_{uuid.uuid4().hex[:6]}.{ext}"

        if tool_context:
            tool_context.save_artifact(filename=filename, artifact=image_part)

        storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"
        return f"Successfully generated real-time departmental wait times dashboard image!\n\n![Departmental Wait Times Dashboard Image]({public_url})\n\nPublic Storage URL: {public_url}"
    except Exception as e:
        return f"Error generating wait times dashboard image: {str(e)}"


def generate_triage_instruction_video(prompt: str, tool_context: ToolContext = None) -> str:
    """Generates a short educational or instructional video for emergency triage procedures using Google's Omni model (gemini-omni-flash-preview) in the global region.

    Saves the generated video artifact with tool_context.save_artifact for Playground visibility, and uploads the video bytes directly to public Cloud Storage.

    Args:
        prompt: Detailed description of the triage video to generate (e.g. 'Short instructional video demonstrating ESI-1 trauma intake workflow and CPR hand placement').

    Returns:
        The public HTTPS URL of the uploaded video in Cloud Storage.
    """
    try:
        genai_client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT_ID, location="global")
        resp = genai_client.interactions.create(
            model="gemini-omni-flash-preview",
            input=prompt,
            generation_config={
                "response_modalities": ["VIDEO"]
            }
        )

        video_bytes = None
        mime_type = "video/mp4"

        # 1. Try direct attribute access
        if hasattr(resp, "outputs") and resp.outputs:
            for out in resp.outputs:
                parts = getattr(out, "parts", []) or []
                for p in parts:
                    if hasattr(p, "inline_data") and p.inline_data and getattr(p.inline_data, "data", None):
                        d = p.inline_data.data
                        mime_type = getattr(p.inline_data, "mime_type", "video/mp4") or "video/mp4"
                        video_bytes = base64.b64decode(d) if isinstance(d, str) else d
                        break
                    d = getattr(p, "data", None)
                    if d:
                        mime_type = getattr(p, "mime_type", "video/mp4") or "video/mp4"
                        video_bytes = base64.b64decode(d) if isinstance(d, str) else d
                        break
                if video_bytes:
                    break

        # 2. Try dict traversal fallback
        if not video_bytes:
            resp_dict = resp.model_dump() if hasattr(resp, "model_dump") else (resp if isinstance(resp, dict) else {})
            for out in resp_dict.get("outputs", []):
                for p in out.get("parts", []):
                    inline = p.get("inline_data", {})
                    d = inline.get("data") or p.get("data")
                    if d:
                        mime_type = inline.get("mime_type") or p.get("mime_type", "video/mp4") or "video/mp4"
                        video_bytes = base64.b64decode(d) if isinstance(d, str) else d
                        break
                if video_bytes:
                    break

        if not video_bytes:
            return "Failed to generate video: no video bytes returned from gemini-omni-flash-preview."

        filename = f"triage_video_{uuid.uuid4().hex[:6]}.mp4"
        video_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)

        # 1. Save artifact with tool_context.save_artifact
        if tool_context:
            tool_context.save_artifact(filename=filename, artifact=video_part)

        # 2. Upload video bytes directly to public Cloud Storage bucket
        storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(video_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"
        return f"Successfully generated ER triage instructional video!\nPublic Storage URL: {public_url}"
    except Exception as e:
        return f"Error generating or uploading ER triage video: {str(e)}"


