# app/agent.py
import json
import os
from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from app.a2ui_utils import a2ui_callback
from app.tools import (
    recommend_triage_level,
    get_bed_status,
    update_bed_status,
    get_patient_queue,
    add_patient_to_queue,
    calculate_department_wait_times,
    get_drug_safety_info,
    generate_er_floorplan_image,
    generate_departmental_wait_times_dashboard_image,
    generate_triage_instruction_video,
)


# WRITE: after each turn, send the session to Memory Bank for fact and allergy extraction.
async def generate_memories_callback(callback_context: CallbackContext):
    try:
        await callback_context.add_session_to_memory()
    except Exception as e:
        print(f"Warning: memory service callback skipped: {e}")
    return None


# Build A2UI System Prompt using A2uiSchemaManager v0.8 & BasicCatalog
schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description="You are an intelligent ER Triage Coordinator assistant for hospital emergency departments.",
    workflow_description=(
        "Help triage staff prioritize arriving patients based on injury severity (ESI Level 1-5), "
        "track ER bed availability and occupancy in real time, calculate department wait times, check FDA drug safety data, "
        "generate visual ER floorplan diagrams, execute Python code for clinical calculations in an Agent Engine sandbox, "
        "and manage the patient queue in Firestore. Return structured UI when appropriate."
    ),
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects.\n\n"
        "MEMORY & ALLERGY MANAGEMENT INSTRUCTIONS:\n"
        "• Automatically remember and store all stated user and patient allergies (medications, latex, food, iodine, etc.) across sessions.\n"
        "• Retrieve preloaded memories at the beginning of each conversation and proactively highlight any relevant allergy warnings."
    ),
    include_schema=True,
    include_examples=True,
)

# Load Agent Engine resource name from deployment_metadata.json if available
agent_engine_resource_name = "projects/4722205683/locations/us-east1/reasoningEngines/8384495242396565504"
sandbox_resource_name = "projects/4722205683/locations/us-east1/reasoningEngines/8384495242396565504/sandboxEnvironments/4362870935108190208"

metadata_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "deployment_metadata.json")
if os.path.exists(metadata_file):
    try:
        with open(metadata_file, "r") as f:
            meta = json.load(f)
            if "remote_agent_runtime_id" in meta:
                agent_engine_resource_name = meta["remote_agent_runtime_id"]
    except Exception as e:
        print(f"Warning loading deployment_metadata.json: {e}")

code_executor = AgentEngineSandboxCodeExecutor(
    sandbox_resource_name=sandbox_resource_name,
    agent_engine_resource_name=agent_engine_resource_name,
)

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    code_executor=code_executor,
    instruction=instruction,
    tools=[
        PreloadMemoryTool(),
        recommend_triage_level,
        get_bed_status,
        update_bed_status,
        get_patient_queue,
        add_patient_to_queue,
        calculate_department_wait_times,
        get_drug_safety_info,
        generate_er_floorplan_image,
        generate_departmental_wait_times_dashboard_image,
        generate_triage_instruction_video,
    ],
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
