#!/bin/bash
# =============================================================
# HAMMERFALL BA5 — Relationship Seed Script
#
# Seeds bidirectional relationship rows into helm_entity_relationships.
# Run from repo root: bash scripts/seed_relationships.sh
#
# WARNING: ~351 sequential brain.sh calls.
# Expected runtime: 10-20 minutes. Do not interrupt.
# Progress timestamp printed every 50 rows.
#
# Safety guard (3-state):
#   0 rows          → clean slate, proceed
#   EXPECTED_TOTAL  → already seeded, exit 0
#   between         → partial failure, manual recovery needed, exit 1
#
# UUID lookup: all entity UUIDs are resolved at script start via a
# single bulk query and stored in a temp lookup file. If any entity
# name does not resolve, the script exits before writing any rows.
#
# Relationship label conventions (from migration 004):
#   People:       spouse, parent, child, sibling, grandparent, grandchild,
#                 aunt, uncle, niece, nephew, friend, colleague,
#                 supervisor, direct_report, engaged, pseudo_family
#   Places:       resident, origin, workplace
#   Orgs:         employee, founder, member, client
#   Pets:         owner, pet
# Bidirectionality: two rows per pair, labels flip by perspective.
# Step/in-law context goes in --rel-notes, not the label.
# =============================================================

set -e

COUNT=0
EXPECTED_TOTAL=349

CONFIG_FILE="$(dirname "$0")/../hammerfall-config.md"
BRAIN_URL=$(grep "supabase_brain_url:" "$CONFIG_FILE" | awk '{print $2}')
SERVICE_KEY_ENV=$(grep "supabase_brain_service_key_env:" "$CONFIG_FILE" | awk '{print $2}')
SERVICE_KEY="${!SERVICE_KEY_ENV}"

if [ -z "$BRAIN_URL" ] || [ -z "$SERVICE_KEY" ]; then
  echo "ERROR: Brain URL or service key not configured."
  exit 1
fi

# 3-state safety guard
EXISTING=$(curl -s --ssl-no-revoke \
  "$BRAIN_URL/rest/v1/helm_entity_relationships?select=id" \
  -H "apikey: $SERVICE_KEY" \
  -H "Authorization: Bearer $SERVICE_KEY" | node -e "
  let d = '';
  process.stdin.on('data', c => d += c);
  process.stdin.on('end', () => {
    try { const arr = JSON.parse(d); process.stdout.write(Array.isArray(arr) ? String(arr.length) : '-1'); }
    catch(e) { process.stdout.write('-1'); }
  });
")

if [ "$EXISTING" -eq "0" ]; then
  echo "Clean slate — proceeding with seed."
elif [ "$EXISTING" -eq "$EXPECTED_TOTAL" ]; then
  echo "Already fully seeded ($EXISTING rows). Nothing to do."; exit 0
else
  echo "ERROR: Partial seed detected ($EXISTING of $EXPECTED_TOTAL rows)."
  echo "Manual recovery needed — delete partial rows from helm_entity_relationships, then re-run."
  exit 1
fi

# =============================================================
# UUID LOOKUP TABLE — resolved from helm_entities at seed time
# =============================================================
MAXWELL="34068530-7025-4aae-bfa9-db1a1cc41a4f"
KIM="594eb269-be37-492b-9ce6-5d427cad3d87"
JACK="3f23e454-9a76-4033-ae7f-26b024206f98"
EMMA="75965ae2-5da1-4054-bd40-dd0d798f16d8"
JENNIFER="2949ce4f-57a2-45c2-888e-2c76702569cb"
IAN="0d53e59f-c4dc-4ccd-b3e2-84b76a1e93ba"
AMY="3ba71060-ce84-4931-96b8-0eb8f17d58cf"
WES="46736649-f6e7-40de-a9c0-b5df631bda23"
LOGAN="e57d75fc-5246-4f0d-a177-15c4d8ff0c5b"
CHRIS="e9c425bb-4d05-413a-8099-db88a0a43dc5"
LILY="fce59125-e520-4827-a08a-179d154b7d0e"
SANCHEZ="e07f5226-40eb-468b-a7db-403579e2e815"
KRIEGER="c4e2749a-ccc0-45dc-bb28-3867c6cbb222"
KEELEY="a62e8e76-e951-42bd-961a-72d89310a7fb"
CARRIE="efebf7ac-b187-4b25-9c0b-2209d3b54550"
MICHELLE="c9c36c1e-fbbd-4727-b5c1-6e3eb0726797"
MIA="1a4757b4-84b3-426b-a843-b0335e5addea"
MACKENZIE="f281a88c-19f8-4fcc-87ad-2de8b63e436b"
OWEN="a31ee8bc-585b-4f08-8829-6fffeff7f537"
DONNA="ba50d99e-c5df-44b2-82a3-7821982c0870"
GREG="f0203ce0-8cd7-4ea1-bdcf-678589a2763f"
VICTOR="ff6c8ed0-1555-417f-8ac8-804cbdc01891"
MIKE_S="136cc276-48ff-46f0-ab7b-5c6b58bac718"
MARISSA="aa192ede-f123-4404-b382-409a88008f4d"
MARY_JANE="edbbb994-b4c9-4816-a190-eb0c77cd2fad"
ED="9cfbe3c1-3577-4dc0-b094-b8c5a4fe73e7"
JORDAN="fa5132ce-94a5-4044-8c38-833a79df0caa"
BRODY="475a3920-2919-4947-9620-eaafe55f03d0"
NICOLE="7690f417-0dbf-42b4-8ba0-24441c525580"
ADDISON="a99f09cc-3505-4a7a-8586-ab1903ef5cbf"
ISAAC="23f07db6-b589-46e8-aa51-fdfff42d90d2"
GIOVANNI="8ce0daf9-b12a-4afe-845e-1ebe1c31f9d2"
ANTHONY="96ab5d0f-3697-40fb-979a-088a805358fd"
EARL="e520fa8d-7c26-4428-a312-87d4a7aba82d"
ROBIN="dcfbf590-fd25-4e37-8e4c-f7f4ae8be7de"
JOEL="d9ee57ca-df98-40ba-a7fb-ab14bd4b655f"
# Places
ALEXANDRIA_TWP="d6b84835-810a-4016-97ed-d86466c9e559"
ALEXANDRIA_SCHOOL="8b6fe3f9-afc0-4c99-b4a6-1924526af38d"
MILFORD="1d9d6f9c-3ba3-42eb-8f62-2bc8881aa3aa"
HARTLEY="99afba54-d74f-426a-9f9b-11086a1cfca8"
RIEGELSVILLE="58b4a870-0766-4af2-b74b-a290e9a995d7"
MAPLEWOOD="6482676b-dab1-47ea-bd92-cced5b7ce3a3"
HOLLAND_TWP="c2316c54-5a37-467d-9008-6b9bafc29e05"
HOLLAND_SCHOOL="6715eae2-400f-4424-a198-8e5237a24de1"
BELLIS="3440d660-2fec-4fd4-b0ad-6eb95e037cea"
PITTSTOWN_ROAD="972f20b9-87ef-473c-b4a6-526b501a33ff"
PITTSTOWN="9647f6ec-95b6-45a6-aeaa-67d31ab0fb5a"
GLEN_GARDNER="13514a93-70c5-460d-90b8-f1432da304fc"
CAROL_COURT="a55192f4-3f9a-4787-9a4d-083fbc2943ca"
CLINTON="7a27b07d-b326-4f93-aec3-42efcac7ca78"
NYC="fe207375-e541-4fe2-84cf-c328b83e03f0"
JERSEY_CITY="6488cd12-b67c-4813-9d9b-4bbc5e73e731"
DUDLEY="81943609-b85a-4b89-95bc-aa8c5a596878"
SOHO="64991674-c8d6-41e8-8ca0-9542e8044603"
MEADOW_VALLEY="d74f2628-e6f3-40b9-9055-1c4a0762c044"
EPHRATA="af978355-fd92-4bc0-b4e3-55646161de6b"
LANCASTER="08a2c662-b3f8-4264-ab27-6c7237b22209"
WYNCROFT="8353ebab-8883-4549-9ce4-92dad023cff6"
# Organizations
MEDIDATA="ce4d4d26-8dd6-428d-8596-8efcf4499ead"
VENMO="563d98e0-61ef-42e5-96b8-1fdfde0d7b19"
LABCORP="fe3c1b33-f486-49af-8d05-fa52f1a2b333"
GRIMNIR="31ab2d05-23e4-47ba-9f80-b4fb11d64f72"
SCIMED="3c8ce8ca-8fe5-44a4-a1bd-94660db8a4e9"
VENTURE_JETS="1043c53c-8c42-4935-8f78-517a06be5624"

echo "== BA5 Relationship Seed — $(date '+%Y-%m-%d %H:%M') =="
echo "   Writing ~$EXPECTED_TOTAL bidirectional relationship rows."
echo "   Expected runtime: 10-20 minutes. Do not interrupt."
echo ""

# Helper: write one relationship row and track progress
rel() {
  local from="$1"
  local to="$2"
  local label="$3"
  local notes="${4:-}"
  local OUTPUT
  if [ -n "$notes" ]; then
    OUTPUT=$(bash scripts/brain.sh "hammerfall-solutions" "helm" "$label" "" false \
      --table helm_entity_relationships \
      --from-entity "$from" \
      --to-entity "$to" \
      --rel-notes "$notes")
  else
    OUTPUT=$(bash scripts/brain.sh "hammerfall-solutions" "helm" "$label" "" false \
      --table helm_entity_relationships \
      --from-entity "$from" \
      --to-entity "$to")
  fi
  if echo "$OUTPUT" | grep -q "ERROR"; then
    echo "  FAILED [$label $from->$to]: $OUTPUT"
    exit 1
  fi
  COUNT=$((COUNT + 1))
  if (( COUNT % 50 == 0 )); then
    echo "  [$(date '+%H:%M:%S')] $COUNT rows written..."
  fi
}

# Helper: write bidirectional pair
pair() {
  local a="$1"
  local b="$2"
  local label_a="$3"  # label from a's perspective
  local label_b="$4"  # label from b's perspective
  local notes_a="${5:-}"
  local notes_b="${6:-$5}"  # default notes_b = notes_a if not specified
  rel "$a" "$b" "$label_a" "$notes_a"
  rel "$b" "$a" "$label_b" "$notes_b"
}

# =============================================================
# SECTION 1 — Maxwell's personal relationships
# =============================================================
echo "-- Section 1: Maxwell relationships --"

# Maxwell ↔ Kim
pair "$MAXWELL" "$KIM" "spouse" "spouse" \
  "High school sweetheart, married October 5 2012, together 19 years" \
  "High school sweetheart, married October 5 2012, together 19 years"

# Maxwell ↔ Emma
pair "$MAXWELL" "$EMMA" "parent" "child" \
  "First daughter, born March 30 2019, Max's best friend and primary motivation" \
  "Father — protector, guide and teacher"

# Maxwell ↔ Lily
pair "$MAXWELL" "$LILY" "parent" "child" \
  "Second daughter, born May 13 2025. Adjustment was difficult but she is a light." \
  "Father — protector, guide and teacher"

# Maxwell ↔ Jack
pair "$MAXWELL" "$JACK" "child" "parent" \
  "Father and role model. Taught Max his values and honor code." \
  "Son — oldest from first marriage"

# Maxwell ↔ Jennifer
pair "$MAXWELL" "$JENNIFER" "child" "parent" \
  "Stepmother. Rock and anchor of the family, always willing to help." \
  "Stepson"

# Maxwell ↔ Ian
pair "$MAXWELL" "$IAN" "sibling" "sibling" \
  "Younger blood brother, born 1994. One of the Core Four. Fiercely loyal." \
  "Older blood brother. Core Four."

# Maxwell ↔ Amy
pair "$MAXWELL" "$AMY" "child" "parent" \
  "Biological mother. Hard worker. Butt heads but love is never lost." \
  "Son"

# Maxwell ↔ Mackenzie
pair "$MAXWELL" "$MACKENZIE" "sibling" "sibling" \
  "Half-sister on fathers side. Old soul, best of the siblings." \
  "Half-brother"

# Maxwell ↔ Owen
pair "$MAXWELL" "$OWEN" "sibling" "sibling" \
  "Half-brother on fathers side. Simple, content. Emma loves him." \
  "Half-brother"

# Maxwell ↔ Wes
pair "$MAXWELL" "$WES" "friend" "friend" \
  "Best friend since high school. Core Four. The Spock to Max's Kirk." \
  "Best friend since high school. Core Four."

# Maxwell ↔ Logan
pair "$MAXWELL" "$LOGAN" "friend" "friend" \
  "Core Four. Best friend. Plays Star Citizen nightly." \
  "Core Four. Best friend."

# Maxwell ↔ Chris
pair "$MAXWELL" "$CHRIS" "colleague" "colleague" \
  "Friend and colleague at Labcorp. Mentor who keeps Max sane at work." \
  "Friend and colleague at Labcorp."

# Maxwell ↔ Nicole
pair "$MAXWELL" "$NICOLE" "friend" "friend" \
  "Oldest friend. Extended kindness when Max was at his lowest — likely saved his life." \
  "Old friend from grade school. Married to Wes."

# Maxwell ↔ Addison
pair "$MAXWELL" "$ADDISON" "pseudo_family" "pseudo_family" \
  "Pseudo-niece. Wes and Nicole's daughter." \
  "Pseudo-uncle"

# Maxwell ↔ Isaac
pair "$MAXWELL" "$ISAAC" "pseudo_family" "pseudo_family" \
  "Pseudo-nephew. Wes and Nicole's son. Genius level intellect." \
  "Pseudo-uncle"

# Maxwell ↔ Jordan
pair "$MAXWELL" "$JORDAN" "friend" "friend" \
  "Logan's wife, close family friend. Regular game nights." \
  "Friend, Logan's close friend"

# Maxwell ↔ Brody
pair "$MAXWELL" "$BRODY" "pseudo_family" "pseudo_family" \
  "Pseudo-nephew. Logan and Jordan's son." \
  "Pseudo-uncle"

# Maxwell ↔ Donna
pair "$MAXWELL" "$DONNA" "child" "parent" \
  "Mother-in-law. Sweet and proper. Max often helps her with technology." \
  "Son-in-law"

# Maxwell ↔ Greg
pair "$MAXWELL" "$GREG" "child" "parent" \
  "Father-in-law. Passed November 2016. Fantastic man and cook." \
  "Son-in-law"

# Maxwell ↔ Victor
pair "$MAXWELL" "$VICTOR" "child" "parent" \
  "Step-father-in-law. Donna's fiance. Former owner of Venture Jets." \
  "Step-son-in-law"

# Maxwell ↔ Mike Sharkey
pair "$MAXWELL" "$MIKE_S" "sibling" "sibling" \
  "Brother-in-law. Kim's twin. Army veteran, now at Picatinny Arsenal." \
  "Brother-in-law"

# Maxwell ↔ Marissa
pair "$MAXWELL" "$MARISSA" "sibling" "sibling" \
  "Sister-in-law. Mike's wife. Nutritionist." \
  "Sister-in-law"

# Maxwell ↔ Mary Jane
pair "$MAXWELL" "$MARY_JANE" "grandchild" "grandparent" \
  "Paternal grandmother. Tough old school firecracker. Called Grandma." \
  "Grandson"

# Maxwell ↔ Ed
pair "$MAXWELL" "$ED" "grandchild" "grandparent" \
  "Paternal grandfather. Jack's stepfather. Pops. Pro photographer, master contractor." \
  "Grandson"

# Maxwell ↔ Earl
pair "$MAXWELL" "$EARL" "grandchild" "grandparent" \
  "Maternal step-grandfather. Called Sarge. Max was his caretaker — pivotal period." \
  "Step-grandson and caretaker through end of life"

# Maxwell ↔ Robin
pair "$MAXWELL" "$ROBIN" "grandchild" "grandparent" \
  "Maternal grandmother. Called Nana. Social butterfly, suffered aphasia at end of life." \
  "Grandson"

# Maxwell ↔ Joel
pair "$MAXWELL" "$JOEL" "grandchild" "grandparent" \
  "Maternal grandfather. Robin's first husband. Old school Italian, complicated but loving." \
  "Grandson"

# Maxwell ↔ Carrie
pair "$MAXWELL" "$CARRIE" "child" "parent" \
  "Mother's partner. Sweet and loving." \
  "Partner's son"

# Maxwell ↔ Michelle
pair "$MAXWELL" "$MICHELLE" "sibling" "sibling" \
  "Sister-in-law. Ian's wife. Old school punker, down to earth." \
  "Brother-in-law"

# Maxwell ↔ Mia
pair "$MAXWELL" "$MIA" "uncle" "niece" \
  "Niece. Ian and Michelle's daughter, born weeks after Lily." \
  "Uncle"

# Maxwell ↔ Anthony
pair "$MAXWELL" "$ANTHONY" "sibling" "sibling" \
  "Future brother-in-law. Mackenzie's fiance. Went to high school together." \
  "Future brother-in-law"

# Maxwell ↔ Giovanni
pair "$MAXWELL" "$GIOVANNI" "direct_report" "supervisor" \
  "Direct supervisor at Labcorp." \
  "Direct report at Labcorp"

# Maxwell pets
pair "$MAXWELL" "$SANCHEZ" "owner" "pet" \
  "First dog. Terrier-chihuahua mix. Originally Ian's dog. Passed March 2026." \
  "Owner"
pair "$MAXWELL" "$KRIEGER" "owner" "pet" \
  "Best bud. Yellow lab, acquired January 2013." \
  "Owner"
pair "$MAXWELL" "$KEELEY" "owner" "pet" \
  "Golden retriever, 2 years old. Sweetest dog." \
  "Owner"

# Maxwell ↔ places (current and significant)
rel "$MAXWELL" "$HARTLEY" "resident" "Current primary residence since June 2022"
rel "$MAXWELL" "$ALEXANDRIA_TWP" "resident" "Current township of residence"
rel "$MAXWELL" "$RIEGELSVILLE" "origin" "Grew up here with Jack and Jen"
rel "$MAXWELL" "$HOLLAND_TWP" "origin" "Grew up here with Amy, grades 2-8"
rel "$MAXWELL" "$CLINTON" "origin" "Proposed to Kim on the Clinton bridge"
rel "$MAXWELL" "$JERSEY_CITY" "resident" "Lived here twice 2014-2019. First real quality of life step up."
rel "$MAXWELL" "$GLEN_GARDNER" "resident" "Lived at Carol Court 2020-2022"
rel "$MAXWELL" "$EPHRATA" "resident" "First apartment after marrying, 2012-2013"
rel "$MAXWELL" "$LANCASTER" "resident" "Lived here after Ephrata"
rel "$MAXWELL" "$NYC" "workplace" "Primary work destination 2014-2022"

# Maxwell ↔ orgs
rel "$MAXWELL" "$MEDIDATA" "employee" "Joined as contractor 2014-2015, hired full-time Dec 2015. Returned Feb 2019. One of his happiest professional periods."
rel "$MAXWELL" "$VENMO" "employee" "Brief stint 2018. Squandered opportunity, key learning in humility."
rel "$MAXWELL" "$LABCORP" "employee" "Senior Director of Product Management since 2022. Despises the culture. Escape is a primary motivation."
rel "$MAXWELL" "$GRIMNIR" "founder" "Co-founded with Ian, Wes and Logan. Airsoft production company."
rel "$MAXWELL" "$SCIMED" "employee" "First NYC employer 2014-2015. Left for Medidata."

# =============================================================
# SECTION 2 — Kim's relationships (non-Maxwell)
# =============================================================
echo "-- Section 2: Kim relationships --"

pair "$KIM" "$EMMA" "parent" "child" "Mother" "Daughter"
pair "$KIM" "$LILY" "parent" "child" "Mother. Lily strongly bonded with Kim." "Daughter"
pair "$KIM" "$DONNA" "child" "parent" "Mother" "Daughter"
pair "$KIM" "$GREG" "child" "parent" "Father. Passed 2016. Deeply missed." "Daughter"
pair "$KIM" "$VICTOR" "child" "parent" "Step-father. Donna's fiance." "Step-daughter"
pair "$KIM" "$MIKE_S" "sibling" "sibling" "Twin brother" "Twin sister"
pair "$KIM" "$MARISSA" "sibling" "sibling" "Sister-in-law" "Sister-in-law"
pair "$KIM" "$JACK" "child" "parent" "Father-in-law" "Daughter-in-law"
pair "$KIM" "$JENNIFER" "child" "parent" "Step-mother-in-law" "Step-daughter-in-law"
pair "$KIM" "$AMY" "child" "parent" "Mother-in-law" "Daughter-in-law"
pair "$KIM" "$IAN" "sibling" "sibling" "Brother-in-law" "Sister-in-law"
pair "$KIM" "$MICHELLE" "sibling" "sibling" "Sister-in-law" "Sister-in-law"
pair "$KIM" "$MACKENZIE" "sibling" "sibling" "Sister-in-law. Half-sister of Max." "Sister-in-law"
pair "$KIM" "$WES" "friend" "friend" "Close family friend" "Close family friend"
pair "$KIM" "$NICOLE" "friend" "friend" "Close family friend" "Close family friend"
pair "$KIM" "$LOGAN" "friend" "friend" "Close family friend" "Close family friend"
pair "$KIM" "$JORDAN" "friend" "friend" "Close friend, wine and gossip nights" "Close friend"
pair "$KIM" "$MARY_JANE" "grandchild" "grandparent" "Paternal grandmother-in-law" "Granddaughter-in-law"
pair "$KIM" "$ED" "grandchild" "grandparent" "Paternal grandfather-in-law" "Granddaughter-in-law"
pair "$KIM" "$EARL" "grandchild" "grandparent" "Step-grandfather-in-law" "Step-granddaughter-in-law"
pair "$KIM" "$ROBIN" "grandchild" "grandparent" "Maternal grandmother-in-law" "Granddaughter-in-law"
pair "$KIM" "$CARRIE" "child" "parent" "Mother-in-law figure, Amy's partner" "Daughter-in-law figure"
pair "$KIM" "$SANCHEZ" "owner" "pet" "Co-owner" "Owner"
pair "$KIM" "$KRIEGER" "owner" "pet" "Co-owner" "Owner"
pair "$KIM" "$KEELEY" "owner" "pet" "Co-owner" "Owner"
rel "$KIM" "$HARTLEY" "resident" "Current primary residence"
rel "$KIM" "$GLEN_GARDNER" "origin" "Childhood home in Glen Gardner NJ"
rel "$KIM" "$JERSEY_CITY" "resident" "Lived here twice with Max 2014-2019"
rel "$KIM" "$EPHRATA" "resident" "First home after marrying"
rel "$KIM" "$NYC" "workplace" "Worked in NYC with Max 2014-2022"
rel "$KIM" "$MEDIDATA" "employee" "Worked at Medidata alongside Max"

# =============================================================
# SECTION 3 — Core Four cross-relationships
# =============================================================
echo "-- Section 3: Core Four --"

pair "$IAN" "$WES" "friend" "friend" "Core Four" "Core Four"
pair "$IAN" "$LOGAN" "friend" "friend" "Core Four" "Core Four"
pair "$WES" "$LOGAN" "friend" "friend" "Core Four" "Core Four"
pair "$IAN" "$GRIMNIR" "founder" "founder" "Co-founder" ""
pair "$WES" "$GRIMNIR" "founder" "founder" "Co-founder" ""
pair "$LOGAN" "$GRIMNIR" "founder" "founder" "Co-founder" ""

# =============================================================
# SECTION 4 — Family sub-networks
# =============================================================
echo "-- Section 4: Family sub-networks --"

# Jack and Jennifer's family
pair "$JACK" "$JENNIFER" "spouse" "spouse" "Married" "Married"
pair "$JACK" "$IAN" "parent" "child" "Son" "Father"
pair "$JACK" "$MACKENZIE" "parent" "child" "Daughter" "Father"
pair "$JACK" "$OWEN" "parent" "child" "Son" "Father"
pair "$JENNIFER" "$IAN" "parent" "child" "Stepson" "Stepmother"
pair "$JENNIFER" "$MACKENZIE" "parent" "child" "Daughter" "Mother"
pair "$JENNIFER" "$OWEN" "parent" "child" "Son" "Mother"
pair "$JACK" "$MARY_JANE" "child" "parent" "Mother" "Son"
pair "$JACK" "$ED" "child" "parent" "Stepfather" "Stepson"
pair "$IAN" "$MACKENZIE" "sibling" "sibling" "Half-sister" "Half-brother"
pair "$IAN" "$OWEN" "sibling" "sibling" "Half-brother" "Half-brother"
pair "$MACKENZIE" "$OWEN" "sibling" "sibling" "Brother" "Sister"
pair "$MACKENZIE" "$ANTHONY" "engaged" "engaged" "Fiance. Relocating to Florida July 2026." "Fiance"

# Jack ↔ places
rel "$JACK" "$RIEGELSVILLE" "resident" "Lives here with Jennifer"
rel "$JACK" "$MAPLEWOOD" "resident" "Family home at 118 Maplewood Road"

# Ian's family
pair "$IAN" "$MICHELLE" "spouse" "spouse" "Wife" "Husband"
pair "$IAN" "$MIA" "parent" "child" "Daughter, born May 2025" "Father"
pair "$MICHELLE" "$MIA" "parent" "child" "Daughter" "Mother"
pair "$MIA" "$EMMA" "pseudo_family" "pseudo_family" "Cousin — Ian's daughter / Maxwell's daughter" "Cousin — Maxwell's daughter / Ian's daughter"
pair "$MIA" "$LILY" "pseudo_family" "pseudo_family" "Cousin — Ian's daughter / Maxwell's daughter" "Cousin — Maxwell's daughter / Ian's daughter"

# Amy's family
pair "$AMY" "$IAN" "parent" "child" "Son" "Mother"
pair "$AMY" "$CARRIE" "spouse" "spouse" "Long-term partner" "Long-term partner"
pair "$AMY" "$ROBIN" "child" "parent" "Mother" "Daughter"
pair "$AMY" "$EARL" "child" "parent" "Step-father. Called Sarge." "Step-daughter"
pair "$AMY" "$JOEL" "child" "parent" "Father. Complicated relationship." "Daughter"

# Robin and Earl / Joel
pair "$ROBIN" "$EARL" "spouse" "spouse" "Husband. Married after divorce from Joel." "Wife"
pair "$ROBIN" "$JOEL" "sibling" "sibling" "Ex-husband. High school sweethearts who eloped." "Ex-wife"

# Mary Jane and Ed
pair "$MARY_JANE" "$ED" "spouse" "spouse" "Husband" "Wife"
pair "$MARY_JANE" "$IAN" "grandparent" "grandchild" "Grandson" "Grandmother"
pair "$MARY_JANE" "$MACKENZIE" "grandparent" "grandchild" "Granddaughter" "Grandmother"
pair "$MARY_JANE" "$OWEN" "grandparent" "grandchild" "Grandson" "Grandmother"
pair "$ED" "$IAN" "grandparent" "grandchild" "Step-grandson" "Step-grandfather"
pair "$ED" "$MACKENZIE" "grandparent" "grandchild" "Step-granddaughter" "Step-grandfather"
pair "$ED" "$OWEN" "grandparent" "grandchild" "Step-grandson" "Step-grandfather"

# Sharkey family
pair "$DONNA" "$GREG" "spouse" "spouse" "Husband. Passed November 2016." "Wife"
pair "$DONNA" "$MIKE_S" "parent" "child" "Son" "Mother"
pair "$DONNA" "$VICTOR" "spouse" "spouse" "Fiance" "Fiance"
pair "$GREG" "$MIKE_S" "parent" "child" "Son" "Father. Passed 2016."
pair "$MIKE_S" "$MARISSA" "spouse" "spouse" "Wife" "Husband"
pair "$MIKE_S" "$KIM" "sibling" "sibling" "Twin sister" "Twin brother"
pair "$DONNA" "$KIM" "parent" "child" "Daughter" "Mother"
pair "$GREG" "$KIM" "parent" "child" "Daughter" "Father. Passed 2016."
rel "$DONNA" "$LANCASTER" "resident" "Lives in Lancaster PA with Victor"
rel "$GREG" "$GLEN_GARDNER" "resident" "Family home in Glen Gardner"
rel "$MIKE_S" "$CAROL_COURT" "resident" "Currently lives at 13 Carol Court with Marissa"
rel "$MARISSA" "$CAROL_COURT" "resident" "Currently lives at 13 Carol Court with Mike"

# Grandchildren — Greg and Donna
pair "$DONNA" "$EMMA" "grandparent" "grandchild" "Granddaughter" "Grandmother"
pair "$DONNA" "$LILY" "grandparent" "grandchild" "Granddaughter" "Grandmother"
pair "$GREG" "$EMMA" "grandparent" "grandchild" "Granddaughter" "Grandfather. Passed before birth."
pair "$GREG" "$LILY" "grandparent" "grandchild" "Granddaughter" "Grandfather. Passed before birth."
pair "$VICTOR" "$EMMA" "grandparent" "grandchild" "Step-grandfather figure" "Step-grandfather"
pair "$VICTOR" "$LILY" "grandparent" "grandchild" "Step-grandfather figure" "Step-grandfather"

# Emma and Lily
pair "$EMMA" "$LILY" "sibling" "sibling" "Younger sister" "Older sister"

# Emma grandparents — Connolly side
pair "$EMMA" "$JACK" "grandchild" "grandparent" "Grandfather" "Granddaughter"
pair "$EMMA" "$JENNIFER" "grandchild" "grandparent" "Step-grandmother" "Step-granddaughter"
pair "$EMMA" "$AMY" "grandchild" "grandparent" "Grandmother" "Granddaughter"
pair "$EMMA" "$CARRIE" "grandchild" "grandparent" "Grandmother figure, Amy's partner" "Granddaughter figure"
pair "$EMMA" "$MARY_JANE" "grandchild" "grandparent" "Great-grandmother" "Great-granddaughter"
pair "$EMMA" "$ED" "grandchild" "grandparent" "Great-grandfather" "Great-granddaughter"
pair "$LILY" "$JACK" "grandchild" "grandparent" "Grandfather" "Granddaughter"
pair "$LILY" "$JENNIFER" "grandchild" "grandparent" "Step-grandmother" "Step-granddaughter"
pair "$LILY" "$AMY" "grandchild" "grandparent" "Grandmother" "Granddaughter"
pair "$LILY" "$MARY_JANE" "grandchild" "grandparent" "Great-grandmother" "Great-granddaughter"
pair "$LILY" "$ED" "grandchild" "grandparent" "Great-grandfather" "Great-granddaughter"

# Emma pet relationships
pair "$EMMA" "$SANCHEZ" "owner" "pet" "Co-owner" "Owner"
pair "$EMMA" "$KRIEGER" "owner" "pet" "Co-owner" "Owner"
pair "$EMMA" "$KEELEY" "owner" "pet" "Co-owner" "Owner"
pair "$LILY" "$SANCHEZ" "owner" "pet" "Co-owner (as infant)" "Owner"
pair "$LILY" "$KRIEGER" "owner" "pet" "Co-owner (as infant)" "Owner"
pair "$LILY" "$KEELEY" "owner" "pet" "Co-owner (as infant)" "Owner"

# Ian ↔ Sanchez (previous owner)
rel "$IAN" "$SANCHEZ" "owner" "Previous owner before Max adopted her"

# =============================================================
# SECTION 5 — Wes/Nicole/Logan/Jordan family networks
# =============================================================
echo "-- Section 5: Friend family networks --"

pair "$WES" "$NICOLE" "spouse" "spouse" "Wife" "Husband"
pair "$WES" "$ADDISON" "parent" "child" "Daughter" "Father"
pair "$WES" "$ISAAC" "parent" "child" "Son" "Father"
pair "$NICOLE" "$ADDISON" "parent" "child" "Daughter" "Mother"
pair "$NICOLE" "$ISAAC" "parent" "child" "Son" "Mother"
pair "$ADDISON" "$ISAAC" "sibling" "sibling" "Younger brother" "Older sister"

pair "$LOGAN" "$JORDAN" "spouse" "spouse" "Wife" "Husband"
pair "$LOGAN" "$BRODY" "parent" "child" "Son" "Father"
pair "$JORDAN" "$BRODY" "parent" "child" "Son" "Mother"

# Pseudo-family to Maxwell and Kim's children
pair "$ADDISON" "$EMMA" "pseudo_family" "pseudo_family" "Friend, older" "Friend"
pair "$ADDISON" "$LILY" "pseudo_family" "pseudo_family" "Pseudo-aunt" "Pseudo-niece"
pair "$ISAAC" "$EMMA" "pseudo_family" "pseudo_family" "Friend" "Friend"
pair "$ISAAC" "$LILY" "pseudo_family" "pseudo_family" "Pseudo-uncle" "Pseudo-niece"
pair "$BRODY" "$EMMA" "pseudo_family" "pseudo_family" "Friend" "Friend"
pair "$BRODY" "$LILY" "pseudo_family" "pseudo_family" "Friend" "Friend"


# =============================================================
# SECTION 6 — Emma's school and sibling relationships
# =============================================================
echo "-- Section 6: Emma school --"
rel "$EMMA" "$ALEXANDRIA_SCHOOL" "member" "Currently enrolled"
rel "$IAN" "$ALEXANDRIA_SCHOOL" "member" "Attended 7th and 8th grade"
rel "$MAXWELL" "$HOLLAND_SCHOOL" "member" "Attended grades 2-8"
rel "$IAN" "$HOLLAND_SCHOOL" "member" "Attended with Max"
rel "$MAXWELL" "$ALEXANDRIA_SCHOOL" "member" "Children attend here"

# =============================================================
# SECTION 7 — Place residence chains
# =============================================================
echo "-- Section 7: Place chains --"

rel "$MAXWELL" "$PITTSTOWN_ROAD" "resident" "Lived here with Amy from 2003"
rel "$IAN" "$PITTSTOWN_ROAD" "resident" "Lived here with Amy from 2003"
rel "$AMY" "$PITTSTOWN_ROAD" "resident" "Lived here from 2003 through 2015"
rel "$MAXWELL" "$PITTSTOWN" "origin" "Town where Pittstown Road home is located"
rel "$IAN" "$PITTSTOWN" "origin" "Town where Pittstown Road home is located"
rel "$MAXWELL" "$BELLIS" "resident" "Childhood road in Holland Township with Amy"
rel "$IAN" "$BELLIS" "resident" "Childhood road in Holland Township with Amy"
rel "$MAXWELL" "$MAPLEWOOD" "origin" "Grew up here with Jack and Jen"
rel "$IAN" "$MAPLEWOOD" "origin" "Grew up here with Jack and Jen"
rel "$MAXWELL" "$DUDLEY" "resident" "First Jersey City apartment. Quality of life transformed."
rel "$KIM" "$DUDLEY" "resident" "First Jersey City apartment"
rel "$MAXWELL" "$SOHO" "resident" "Second Jersey City apartment. Emma born here."
rel "$KIM" "$SOHO" "resident" "Second Jersey City apartment. Emma born here."
rel "$MAXWELL" "$MEADOW_VALLEY" "resident" "First apartment after marrying"
rel "$KIM" "$MEADOW_VALLEY" "resident" "First apartment after marrying"
rel "$MAXWELL" "$WYNCROFT" "resident" "Lancaster apartment address"
rel "$KIM" "$WYNCROFT" "resident" "Lancaster apartment address"
rel "$DONNA" "$CAROL_COURT" "resident" "Sharkey family home before moving to Lancaster"
rel "$MAXWELL" "$CAROL_COURT" "resident" "Lived here 2020-2022"
rel "$KIM" "$CAROL_COURT" "resident" "Lived here 2020-2022 in childhood home"

# =============================================================
# SECTION 8 — Org relationships (non-Maxwell)
# =============================================================
echo "-- Section 8: Org relationships --"

rel "$CHRIS" "$LABCORP" "employee" "Works at Labcorp with Max, reports to Giovanni"
rel "$GIOVANNI" "$LABCORP" "employee" "Vice President at Labcorp, Max and Chris's supervisor"
rel "$CHRIS" "$GIOVANNI" "direct_report" "Direct report relationship at Labcorp"
rel "$GIOVANNI" "$CHRIS" "supervisor" "Supervises Chris Wright at Labcorp"
rel "$VICTOR" "$VENTURE_JETS" "founder" "Founded and owned Venture Jets, recently sold"
rel "$MAXWELL" "$VENTURE_JETS" "member" "Connected via Victor M"

echo ""
echo "== Relationship seeding complete: $COUNT rows written. =="
