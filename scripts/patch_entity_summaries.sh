#!/bin/bash
# =============================================================
# HAMMERFALL BA5 — Entity Summary + Name Fix Patch Script
#
# Two-in-one patch: fixes trailing newlines on all 64 entity names
# (introduced by <<< heredoc on Windows/Git Bash in the original seed run)
# AND adds a one-sentence summary to each entity row.
#
# Run from repo root: bash scripts/patch_entity_summaries.sh
#
# Safe to re-run — PATCH is idempotent (overwrites same values).
# =============================================================

set -e

COUNT=0
TOTAL=64

CONFIG_FILE="$(dirname "$0")/../hammerfall-config.md"
BRAIN_URL=$(grep "supabase_brain_url:" "$CONFIG_FILE" | awk '{print $2}')
SERVICE_KEY_ENV=$(grep "supabase_brain_service_key_env:" "$CONFIG_FILE" | awk '{print $2}')
SERVICE_KEY="${!SERVICE_KEY_ENV}"

if [ -z "$BRAIN_URL" ] || [ -z "$SERVICE_KEY" ]; then
  echo "ERROR: Brain URL or service key not configured."
  exit 1
fi

# Resolve UUID by exact name (including trailing newline variant)
# Queries both clean name and newline-suffixed name to handle either state
get_uuid() {
  local name="$1"
  local ENCODED
  ENCODED=$(node -e "process.stdout.write(encodeURIComponent('${name}\n'))")
  local UUID
  UUID=$(curl -s --ssl-no-revoke \
    "$BRAIN_URL/rest/v1/helm_entities?name=eq.$ENCODED&select=id" \
    -H "apikey: $SERVICE_KEY" \
    -H "Authorization: Bearer $SERVICE_KEY" | \
    node -e "let d=''; process.stdin.on('data',c=>d+=c); process.stdin.on('end',()=>{ const r=JSON.parse(d); process.stdout.write(r[0]?.id || ''); });")
  if [ -z "$UUID" ]; then
    echo "ERROR: UUID not found for entity: $name" >&2
    exit 1
  fi
  echo "$UUID"
}

patch_entity() {
  local name="$1"
  local summary="$2"
  local UUID
  UUID=$(get_uuid "$name")
  local OUTPUT
  # PATCH: fix name (strip newline) + add summary in one call via direct curl
  # brain.sh --patch-id can only send one field at a time per current design,
  # so we use a direct curl for this combined name+summary fix patch.
  local ESCAPED_NAME
  ESCAPED_NAME=$(node -e "process.stdout.write(JSON.stringify('$name'.replace(/[\\r\\n]+\$/, '')))")
  local ESCAPED_SUMMARY
  ESCAPED_SUMMARY=$(node -e "
    let d = '';
    process.stdin.on('data', c => d += c);
    process.stdin.on('end', () => process.stdout.write(JSON.stringify(d.replace(/[\\r\\n]+\$/, ''))));
  " <<< "$summary")

  TMPFILE=$(mktemp /tmp/patch_entity_XXXXXX.json)
  printf '{"name":%s,"summary":%s}' "$ESCAPED_NAME" "$ESCAPED_SUMMARY" > "$TMPFILE"

  RESPONSE=$(curl -s --ssl-no-revoke -X PATCH \
    "$BRAIN_URL/rest/v1/helm_entities?id=eq.$UUID" \
    -H "apikey: $SERVICE_KEY" \
    -H "Authorization: Bearer $SERVICE_KEY" \
    -H "Content-Type: application/json" \
    -H "Prefer: return=representation" \
    -d @"$TMPFILE")
  rm -f "$TMPFILE"

  if echo "$RESPONSE" | grep -q '"code"'; then
    echo "  FAILED [$name]: $(echo "$RESPONSE" | grep -o '"message":"[^"]*"')"
    exit 1
  fi
  COUNT=$((COUNT + 1))
  echo "  ($COUNT/$TOTAL) patched: $name"
}

echo "== BA5 Entity Patch — Name Fix + Summaries — $(date '+%Y-%m-%d %H:%M') =="
echo "   Patching $TOTAL entities: stripping trailing newlines from names, adding summaries."
echo ""

# ---------------------------------------------------------------
# SECTION 1 — Maxwell Connolly
# ---------------------------------------------------------------
echo "-- Section 1: Maxwell --"
patch_entity "Maxwell Connolly" \
  "Founder of Hammerfall Solutions, Senior Director of Product Management at Labcorp, US Army Reserves PSYOP veteran, building toward AI sector pivot and financial freedom."

# ---------------------------------------------------------------
# SECTION 2 — Major Placeholders
# ---------------------------------------------------------------
echo "-- Section 2: Major Placeholders --"
patch_entity "Kimberly Connolly" \
  "Maxwells wife of 13 years and high school sweetheart. Manages the home front while Max drives the work."

patch_entity "Jack Connolly" \
  "Maxwells father and role model. Taught Max his values and honor code. Lives in Riegelsville PA with Jennifer."

patch_entity "Emma Connolly" \
  "Maxwells first daughter, born March 2019. His best friend and primary motivation. Bright, growing into a gamer."

patch_entity "Jennifer Connolly" \
  "Maxwells stepmother on his fathers side. Rock and anchor of the Connolly family, always willing to help."

patch_entity "Ian Connolly" \
  "Maxwells younger brother and one of the Core Four. Fiercely loyal, loves his family."

patch_entity "Amy Connolly" \
  "Maxwells biological mother. Hard worker, loves the grandchildren. She and Max butt heads but love is never lost."

patch_entity "Wesley Green" \
  "Maxwells best friend since high school and one of the Core Four. The Spock to Maxs Kirk — blunt, analytical, loyal."

patch_entity "Logan Whitaker" \
  "One of Maxwells Core Four best friends. Outdoorsy DIY tinkerer, plays Star Citizen nightly with Max and Wes."

patch_entity "Chris Wright" \
  "Maxwells colleague and close friend at Labcorp. Product management expert and mentor who keeps Max sane at work."

# ---------------------------------------------------------------
# SECTION 3 — Minor People and Pets
# ---------------------------------------------------------------
echo "-- Section 3: Minor People and Pets --"
patch_entity "Lily Connolly" \
  "Maxwells second daughter, born May 2025. Strongly bonded with Kim, observant and quick."

patch_entity "Sanchez" \
  "Maxwells first dog, a terrier-chihuahua mix originally Ians. Passed away March 2026."

patch_entity "Krieger" \
  "The Connolly family yellow lab, acquired 2013. Family protector and Maxs best bud. Aging at 13."

patch_entity "Keeley" \
  "The Connolly family golden retriever, 2 years old. Sweet and gentle companion who loves pillows."

patch_entity "Carrie Sayers" \
  "Amys long-term partner. Lives in Toms River NJ. Sweet, loving, honest — QA Auditor for Hilton."

patch_entity "Michelle Connolly" \
  "Ians wife and Maxs sister-in-law. Working class background, voracious reader, old school punker."

patch_entity "Mia Connolly" \
  "Ian and Michelles daughter, born May 2025, just weeks after Lily."

patch_entity "Mackenzie Connolly" \
  "Jacks daughter and Maxs half-sister. Old soul, mature beyond her years. Recently engaged to Anthony Flora, moving to Florida July 2026."

patch_entity "Owen Connolly" \
  "Jacks son and Maxs half-brother. Content and simple, lives with Jack and Jen. Emma loves him."

patch_entity "Donna Sharkey" \
  "Kims mother and Maxs mother-in-law. Teacher in Lancaster PA. Sweet and proper, notoriously allergic to technology."

patch_entity "Gregory Sharkey" \
  "Kims father, passed November 2016 from a heart attack. Career detective, FEMA responder, legendary cook and host."

patch_entity "Victor M" \
  "Donnas fiance and longtime Sharkey family friend. Former owner of Venture Jets. Dotes on Donna and travels extensively."

patch_entity "Michael Sharkey" \
  "Kims twin brother and Maxs brother-in-law. Army veteran with Afghanistan deployment, now civilian weapons tester at Picatinny Arsenal."

patch_entity "Marissa Sharkey" \
  "Mikes wife and Maxs sister-in-law. Nutritionist with her own business, fitness enthusiast, loves cats."

patch_entity "Mary Jane Norman" \
  "Connolly family matriarch on Jacks side. Tough old school firecracker who raised 4 children. Called Grandma or Gma."

patch_entity "Ed Norman" \
  "Mary Janes husband and Maxs paternal grandfather. Retired general contractor, pro-level photographer, avid cyclist. Called Pops or Pop-pop."

patch_entity "Jordan Whitaker" \
  "Logans wife and close friend to Max and Kim. High school therapist, loves board games and gossip."

patch_entity "Brody Whitaker" \
  "Logan and Jordans 2-year-old son. Loves the Connolly house, outdoorsy like his dad."

patch_entity "Nicole Green" \
  "Wes Greens wife and one of Maxs oldest friends. Extended kindness when Max was near his lowest — likely saved his life."

patch_entity "Addison Green" \
  "Wes and Nicoles teenage daughter. Loves drawing, writing, and basketball."

patch_entity "Isaac Green" \
  "Wes and Nicoles son with genius-level intellect. Recently moved to homeschooling to find material that actually challenges him."

patch_entity "Giovanni Macrina" \
  "Max and Chris Wrights VP supervisor at Labcorp. Model executive — fair, poised, and professional."

patch_entity "Anthony Flora" \
  "Mackenzies fiance and future brother-in-law to Max. Went to high school with Max. Former modeling agency owner."

patch_entity "Earl Clark" \
  "Maxs maternal step-grandfather, a US Marine Korean War veteran called Sarge. Max was his caretaker through end of life — a pivotal healing period. Passed around 2010."

patch_entity "Robin Clark" \
  "Maxs maternal grandmother, Amys mother. Social butterfly struck with aphasia in her final years. Called Nana."

patch_entity "Joel Williams" \
  "Maxs maternal grandfather, Robins first husband. Old school Italian type with a complicated but loving character."

# ---------------------------------------------------------------
# SECTION 4 — Places
# ---------------------------------------------------------------
echo "-- Section 4: Places --"
patch_entity "Alexandria Township NJ" \
  "Rural township in western NJ along the Delaware River where Max and Kim currently live."

patch_entity "Alexandria Township School" \
  "Public school in Alexandria Township NJ where Emma is enrolled and where Ian attended 7th and 8th grade."

patch_entity "Milford New Jersey" \
  "Small Delaware River borough in Hunterdon County NJ where Max and Kims current address is registered."

patch_entity "3 Hartley Court, Milford NJ 08848" \
  "Max and Kims current home, purchased June 2022. Their dream home and primary residence."

patch_entity "Riegelsville PA" \
  "Small Delaware River borough in Bucks County PA where Max and Ian grew up with Jack and Jen."

patch_entity "118 Maplewood Road, Riegelsville PA" \
  "Jack and Jens home and the house where Max, Ian, Mackenzie and Owen grew up."

patch_entity "Holland Township NJ" \
  "Rural township in Hunterdon County NJ where Max and Ian grew up with Amy."

patch_entity "Holland Township School" \
  "Public school in Holland Township NJ where Max attended grades 2-8."

patch_entity "Bellis Road, Milford NJ" \
  "The road where Max, Amy and Ian lived in Holland Township during his grammar school years."

patch_entity "266 Pittstown Road, Pittstown NJ" \
  "The home Amy moved to at the end of Maxs 8th grade year. He and Ian lived here with Amy from 2003."

patch_entity "Pittstown NJ" \
  "Small rural community in Alexandria Township NJ where Max and Ian lived with Amy from 2003."

patch_entity "Glen Gardner NJ" \
  "Small Hunterdon County borough and Kims childhood hometown. Max and Kim lived here 2020-2022."

patch_entity "13 Carol Court, Glen Gardner NJ" \
  "The Sharkey family home. Max and Kim lived here 2020-2022. Mike and Marissa currently reside here."

patch_entity "Clinton New Jersey" \
  "Historic Hunterdon County borough where Max proposed to Kim on the bridge. Central location in Connolly and Sharkey family history."

patch_entity "New York City" \
  "Global city and primary work destination for Max and Kim 2014-2022. Enabling period for their financial growth."

patch_entity "Jersey City NJ" \
  "Hudson County city across from Manhattan where Max and Kim lived twice between 2014 and 2019. First real quality of life step up."

patch_entity "Dudley Street, Jersey City" \
  "Street of Max and Kims first Jersey City apartment — the move that transformed their quality of life."

patch_entity "Soho Lofts, Jersey City" \
  "Max and Kims second Jersey City apartment complex and where Emma was born in 2019."

patch_entity "Meadow Valley Road, Ephrata PA" \
  "Street of Max and Kims first apartment after marrying — the first place they felt was truly their own."

patch_entity "Ephrata PA" \
  "Lancaster County borough where Max and Kim lived immediately after their 2012 wedding."

patch_entity "Lancaster PA" \
  "Lancaster County city where Max and Kim lived after Ephrata. Donna and Vic now live here."

patch_entity "652 Wyncroft Lane, Lancaster PA" \
  "Max and Kims apartment address during their Lancaster years."

# ---------------------------------------------------------------
# SECTION 5 — Organizations
# ---------------------------------------------------------------
echo "-- Section 5: Organizations --"
patch_entity "Medidata Solutions" \
  "Life sciences software company where Max got his big break in 2014-2015, breaching six figures as a full-timer in December 2015."

patch_entity "Venmo" \
  "Fintech payment platform where Max had a brief stint in 2018 — a squandered opportunity that taught him humility."

patch_entity "Labcorp Holdings" \
  "Clinical laboratory and CRO company where Max currently works as Senior Director of Product Management. A means to an end — escape is a primary motivator."

patch_entity "Grimnir Tactical" \
  "Airsoft production company founded by Max, Ian, Wes and Logan. Ran a player-influenced narrative game series for 2-3 years. Largely dormant since 2024."

patch_entity "SciMedMedia" \
  "Maxs first NYC employer in 2014-2015, a science media startup he left to join Medidata."

patch_entity "Venture Jets" \
  "Private jet charter company in Lancaster PA owned by Victor M, recently sold upon his retirement."

echo ""
echo "== Patch complete: $COUNT/$TOTAL entities updated. =="
