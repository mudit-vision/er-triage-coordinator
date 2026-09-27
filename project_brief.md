# My agent: ER Triage Coordinator

One-liner: A conversational agent that helps ER triage nurses and hospital coordinators prioritize arriving patients based on injury severity, track bed/staff availability in real time, and visualize department wait times.

Tool coverage:
- Memory: Triage shift notes, facility protocols, and patient queue history across sessions.
- Tools: `recommend_triage_level` (calculates ESI 1-5 priority level), `check_bed_and_staff_availability` (fetches real-time ER bed/staff counts), and `update_bed_status` (updates bed state).
- Catalog/UI: ER Department Queue & Bed Inventory rendered as A2UI rich cards and status tables.
- Image gen: Emergency department layout heatmaps and patient priority breakdown infographics.
- Sandbox: Queue length trend projections, wait-time calculations, and peak-hour load simulations.

Recommended for every project: memory, storage, tools, image generation, A2UI
Agent-specific / stretch (pick what fits): Code sandbox for wait-time analytics, Cloud Trace for latency tracking, and real-time alert triggers.
