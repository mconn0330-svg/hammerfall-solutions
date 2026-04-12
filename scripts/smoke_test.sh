#!/bin/bash
# =============================================================
# Helm Runtime Service — End-to-End Smoke Test
#
# Validates the full path: Claude Code → Runtime → Supabase
# All 6 checks must pass. No partial passes.
#
# Required env vars:
#   SUPABASE_BRAIN_URL         — Supabase REST endpoint
#   SUPABASE_BRAIN_SERVICE_KEY — Read/write access to helm_frames + helm_memory
#   ANTHROPIC_API_KEY          — Required for /health to report helm_prime as reachable
#
# Optional:
#   HELM_RUNTIME_URL           — Override runtime URL (default: http://localhost:8000)
#
# Usage:
#   bash scripts/smoke_test.sh
#
# After a passing run, clean up test rows from Supabase dashboard:
#   helm_memory WHERE content LIKE '%Smoke test%'
# =============================================================

set -e

BASE_URL="${HELM_RUNTIME_URL:-http://localhost:8000}"
BRAIN_URL="${SUPABASE_BRAIN_URL}"
SERVICE_KEY="${SUPABASE_BRAIN_SERVICE_KEY}"
TEST_SESSION="smoke-test-$(date +%s)"
TEST_TURN=1

PASS=0
FAIL=0

pass() { echo "  PASS: $1"; PASS=$((PASS + 1)); }
fail() { echo "  FAIL: $1"; FAIL=$((FAIL + 1)); }

echo ""
echo "== Helm Runtime Smoke Test =="
echo "Runtime:  $BASE_URL"
echo "Session:  $TEST_SESSION"
echo "Date:     $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# ------------------------------------------------------------------
# Pre-flight: confirm required env vars are set
# ------------------------------------------------------------------
if [ -z "$BRAIN_URL" ]; then
  echo "ERROR: SUPABASE_BRAIN_URL is not set."
  exit 1
fi
if [ -z "$SERVICE_KEY" ]; then
  echo "ERROR: SUPABASE_BRAIN_SERVICE_KEY is not set."
  exit 1
fi

# ------------------------------------------------------------------
# Check 1: /health — service up, all configured endpoints reachable,
#          Supabase queryable
# ------------------------------------------------------------------
echo "Check 1: /health"
HEALTH_RESPONSE=$(curl -sf "$BASE_URL/health" 2>&1) || {
  fail "Runtime unreachable at $BASE_URL"
  echo ""
  echo "== Smoke test failed at Check 1 — runtime not running =="
  exit 1
}

STATUS=$(echo "$HEALTH_RESPONSE" | python3 -c "
import sys, json
h = json.load(sys.stdin)
print(h.get('status', 'unknown'))
")

if [ "$STATUS" = "healthy" ]; then
  pass "status=healthy"
else
  fail "/health returned status=$STATUS"
  echo "$HEALTH_RESPONSE" | python3 -m json.tool
  echo ""
  echo "== Smoke test failed at Check 1 =="
  exit 1
fi

# ------------------------------------------------------------------
# Check 2: /invoke/projectionist — valid frame JSON returned
# ------------------------------------------------------------------
echo "Check 2: /invoke/projectionist — frame JSON"

PROJ_TMPFILE=$(mktemp /tmp/smoke_proj_XXXXXX.json)
export USER_MSG="Smoke test user message — BA7 validation $(date +%s)"
export HELM_MSG="Smoke test Helm response — BA7 validation $(date +%s)"
node -e "
  const body = {
    session_id: process.env.TEST_SESSION || 'smoke-test',
    turn_number: 1,
    user_message: process.env.USER_MSG,
    helm_response: process.env.HELM_MSG,
    context: { project: 'hammerfall-solutions', agent: 'helm' }
  };
  process.stdout.write(JSON.stringify(body));
" TEST_SESSION="$TEST_SESSION" > "$PROJ_TMPFILE"

FRAME_RESPONSE=$(curl -sf -X POST "$BASE_URL/invoke/projectionist" \
  -H "Content-Type: application/json" \
  -d @"$PROJ_TMPFILE" 2>&1) || {
  fail "/invoke/projectionist call failed"
  rm -f "$PROJ_TMPFILE"
  FAIL=$((FAIL + 1))
}
rm -f "$PROJ_TMPFILE"

if [ $FAIL -eq 0 ]; then
  FRAME_VALID=$(echo "$FRAME_RESPONSE" | python3 -c "
import sys, json
try:
    r = json.load(sys.stdin)
    # Response is InvokeResponse — output field contains the frame JSON string
    frame = json.loads(r.get('output', '{}'))
    assert 'session_id' in frame, 'Missing session_id'
    assert 'frame_status' in frame, 'Missing frame_status'
    assert frame['frame_status'] == 'active', f'Expected active, got {frame[\"frame_status\"]}'
    assert isinstance(frame.get('entities_mentioned'), list), 'entities_mentioned not array'
    assert isinstance(frame.get('belief_links'), list), 'belief_links not array'
    print('ok')
except Exception as e:
    print(f'error: {e}')
" 2>&1)

  if [ "$FRAME_VALID" = "ok" ]; then
    pass "frame JSON valid, frame_status=active, arrays present"
  else
    fail "frame JSON invalid: $FRAME_VALID"
  fi
fi

# ------------------------------------------------------------------
# Check 3: helm_frames row written to Supabase
# ------------------------------------------------------------------
echo "Check 3: helm_frames row exists in Supabase"

FRAMES=$(curl -sf \
  "$BRAIN_URL/rest/v1/helm_frames?session_id=eq.$TEST_SESSION&select=id,frame_status,layer" \
  -H "apikey: $SERVICE_KEY" \
  -H "Authorization: Bearer $SERVICE_KEY" 2>&1) || {
  fail "Supabase helm_frames query failed"
  FAIL=$((FAIL + 1))
}

if [ $FAIL -le 1 ]; then
  FRAME_COUNT=$(echo "$FRAMES" | python3 -c "
import sys, json
rows = json.load(sys.stdin)
print(len(rows))
" 2>/dev/null || echo "0")

  if [ "$FRAME_COUNT" -ge 1 ]; then
    pass "$FRAME_COUNT frame row(s) found in helm_frames for session $TEST_SESSION"
  else
    fail "No helm_frames row found for session $TEST_SESSION"
  fi
fi

# ------------------------------------------------------------------
# Prep: PATCH the warm frame to cold so Archivist can migrate it
# ------------------------------------------------------------------
FRAME_ID=$(echo "$FRAMES" | python3 -c "
import sys, json
rows = json.load(sys.stdin)
print(rows[0]['id'] if rows else '')
" 2>/dev/null || echo "")

if [ -n "$FRAME_ID" ]; then
  curl -sf -X PATCH \
    "$BRAIN_URL/rest/v1/helm_frames?id=eq.$FRAME_ID" \
    -H "apikey: $SERVICE_KEY" \
    -H "Authorization: Bearer $SERVICE_KEY" \
    -H "Content-Type: application/json" \
    -H "Prefer: return=representation" \
    -d '{"layer":"cold"}' > /dev/null
fi

# ------------------------------------------------------------------
# Check 4+5: /invoke/archivist — migrates cold frame, deletes row
# ------------------------------------------------------------------
echo "Check 4+5: /invoke/archivist — migration and delete"

ARCH_TMPFILE=$(mktemp /tmp/smoke_arch_XXXXXX.json)
node -e "
  const body = {
    session_id: process.env.TEST_SESSION || 'smoke-test',
    turn_number: 1,
    user_message: '',
    helm_response: '',
    context: { project: 'hammerfall-solutions', agent: 'helm' }
  };
  process.stdout.write(JSON.stringify(body));
" TEST_SESSION="$TEST_SESSION" > "$ARCH_TMPFILE"

curl -sf -X POST "$BASE_URL/invoke/archivist" \
  -H "Content-Type: application/json" \
  -d @"$ARCH_TMPFILE" > /dev/null 2>&1 || {
  fail "/invoke/archivist call failed"
  FAIL=$((FAIL + 1))
}
rm -f "$ARCH_TMPFILE"

# Check 4: helm_frames row deleted
REMAINING=$(curl -sf \
  "$BRAIN_URL/rest/v1/helm_frames?session_id=eq.$TEST_SESSION&select=id" \
  -H "apikey: $SERVICE_KEY" \
  -H "Authorization: Bearer $SERVICE_KEY" 2>/dev/null || echo "[]")

REMAINING_COUNT=$(echo "$REMAINING" | python3 -c "
import sys, json
print(len(json.load(sys.stdin)))
" 2>/dev/null || echo "1")

if [ "$REMAINING_COUNT" -eq 0 ]; then
  pass "helm_frames row deleted after Archivist migration"
else
  fail "helm_frames row not deleted ($REMAINING_COUNT row(s) remain)"
fi

# Check 5: helm_memory row exists
MEMORY=$(curl -sf \
  "$BRAIN_URL/rest/v1/helm_memory?project=eq.hammerfall-solutions&agent=eq.helm&memory_type=eq.frame&order=created_at.desc&limit=1" \
  -H "apikey: $SERVICE_KEY" \
  -H "Authorization: Bearer $SERVICE_KEY" 2>/dev/null || echo "[]")

MEMORY_COUNT=$(echo "$MEMORY" | python3 -c "
import sys, json
print(len(json.load(sys.stdin)))
" 2>/dev/null || echo "0")

if [ "$MEMORY_COUNT" -ge 1 ]; then
  pass "helm_memory frame row exists"
else
  fail "No helm_memory frame row found after Archivist migration"
fi

# ------------------------------------------------------------------
# Check 6: BYO model swap — one config line, no code changes
# Validate by confirming model is read from config at runtime
# ------------------------------------------------------------------
echo "Check 6: /config/agents — model config readable, no secrets exposed"

CONFIG_RESPONSE=$(curl -sf "$BASE_URL/config/agents" 2>&1) || {
  fail "/config/agents endpoint unreachable"
  FAIL=$((FAIL + 1))
}

if [ $FAIL -le $((PASS < 5 ? 99 : 1)) ]; then
  CONFIG_VALID=$(echo "$CONFIG_RESPONSE" | python3 -c "
import sys, json
try:
    r = json.load(sys.stdin)
    agents = r.get('agents', {})
    assert 'projectionist' in agents, 'Missing projectionist'
    assert 'archivist' in agents, 'Missing archivist'
    # Confirm no api_key fields exposed
    for role, cfg in agents.items():
        assert 'api_key' not in cfg, f'api_key exposed for role: {role}'
    print('ok')
except Exception as e:
    print(f'error: {e}')
" 2>&1)

  if [ "$CONFIG_VALID" = "ok" ]; then
    pass "agent config readable, no secrets exposed"
  else
    fail "config endpoint issue: $CONFIG_VALID"
  fi
fi

# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------
echo ""
echo "=================================================="
TOTAL=$((PASS + FAIL))
echo "Results: $PASS/$TOTAL checks passed"

if [ $FAIL -eq 0 ]; then
  echo "== All checks passed. BA7 smoke test complete. =="
  echo ""
  echo "NOTE: Clean up test rows from Supabase dashboard:"
  echo "  helm_memory WHERE content LIKE '%Smoke test%'"
  echo "  (or run: DELETE FROM helm_memory WHERE content LIKE '%Smoke test%')"
  echo ""
  exit 0
else
  echo "== $FAIL check(s) FAILED. See output above. =="
  echo ""
  exit 1
fi
