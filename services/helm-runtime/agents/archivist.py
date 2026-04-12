"""
archivist.py — Archivist agent handler.

TODO: BA7c — Wire Archivist to Qwen2.5 3B via Ollama.

Responsibilities:
  - Query helm_frames WHERE layer = 'cold' via supabase_client.py
  - For each cold frame: generate a 1-3 sentence summary via the model
  - Write to helm_memory at full fidelity via supabase_client.py
    (full_content = complete frame JSON, content = generated summary)
  - Delete helm_frames row only after confirming helm_memory write succeeded
    (HTTP 201, no error in response — leave frame in cold on failure)
  - frame_status is read from the helm_frames column (authoritative),
    written into full_content JSONB in helm_memory

Write path: supabase_client.py → Supabase REST → helm_memory table
Safety net: frame stays in helm_frames (layer='cold') on any write failure
"""
