"""
projectionist.py — Projectionist agent handler.

TODO: BA7b — Wire Projectionist to Qwen2.5 3B via Ollama.

Responsibilities:
  - Receive turn request (session_id, turn_number, user_message, helm_response)
  - Build frame JSON matching the schema in agents/helm/projectionist/projectionist.md
  - Use Ollama JSON mode ("format": "json") to constrain model output
  - Validate output via output_validator middleware (required fields, frame_status enum)
  - Write valid frame to helm_frames via supabase_client.py
  - Return the frame JSON as the response body

Frame schema: see agents/helm/projectionist/projectionist.md
Write path: supabase_client.py → Supabase REST → helm_frames table
"""
