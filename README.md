Voice Tool
Personal Gmail writing tool. Two modes: My Voice / CEO Archetype.
Two controls: De-AI slider + Voice slider.
Setup

Copy .env.example to .env and fill in Azure credentials
pip install -r requirements.txt
Run pipeline (see /pipeline)
Start sidecar: uvicorn sidecar.main:app --port 8433
Load /extension in Chrome (developer mode)

Build order
Phase 1 → Phase 2A + 2B (parallel) → Phase 3 → Phase 4 → Phase 5
See architecture doc for full phase breakdown.
