#!/bin/bash
# =============================================================
# HAMMERFALL BA5 — Entity Seed Script
#
# Seeds 64 entities across 5 sections into helm_entities.
# Run from repo root: bash scripts/seed_entities.sh
#
# Sections:
#   1. Maxwell Connolly — full portrait (1)
#   2. Major placeholders — awaiting survey (9)
#   3. Minor people and pets (26)
#   4. Places (22)
#   5. Organizations (6)
#
# Safety guard (3-state):
#   0 rows       → clean slate, proceed
#   64 rows      → already seeded, exit 0
#   1-63 rows    → partial failure, manual recovery needed, exit 1
#
# Exits on first API error. Safe to re-run from clean slate.
#
# Known gap: major placeholders seeded without aliases where first-name
# reference is not yet known (Jennifer, Ian, Amy, Logan, Chris Wright).
# Routine 4 contextual step will fire on first-name reference — this is
# expected behaviour, not a bug. Seeded alias list per entity documented
# inline below.
#
# Web augmentation: public factual data for places and orgs is included
# in attributes. Personal context (Maxwell's connection, role, history)
# comes from source documents only. No blending.
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
  echo "Check hammerfall-config.md and env vars."
  exit 1
fi

# 3-state safety guard
EXISTING=$(curl -s --ssl-no-revoke \
  "$BRAIN_URL/rest/v1/helm_entities?select=id" \
  -H "apikey: $SERVICE_KEY" \
  -H "Authorization: Bearer $SERVICE_KEY" | node -e "
  let d = '';
  process.stdin.on('data', c => d += c);
  process.stdin.on('end', () => {
    try {
      const arr = JSON.parse(d);
      process.stdout.write(Array.isArray(arr) ? String(arr.length) : '-1');
    } catch(e) { process.stdout.write('-1'); }
  });
")

if [ "$EXISTING" -eq "0" ]; then
  echo "Clean slate — proceeding with seed."
elif [ "$EXISTING" -eq "$TOTAL" ]; then
  echo "Already fully seeded ($EXISTING rows). Nothing to do."; exit 0
else
  echo "ERROR: Partial seed detected ($EXISTING of $TOTAL rows)."
  echo "Manual recovery needed — inspect helm_entities, remove partial rows, then re-run."
  exit 1
fi

seed_entity() {
  local entity_type="$1"
  local name="$2"
  local attributes="$3"
  local aliases="${4:-[]}"
  local OUTPUT
  OUTPUT=$(bash scripts/brain.sh "hammerfall-solutions" "helm" "$entity_type" "$name" false \
    --table helm_entities \
    --attributes "$attributes" \
    --aliases "$aliases")
  if echo "$OUTPUT" | grep -q "ERROR"; then
    echo "  FAILED [$entity_type/$name]: $OUTPUT"
    exit 1
  fi
  COUNT=$((COUNT + 1))
  echo "  ($COUNT/$TOTAL) $OUTPUT"
}

echo "== BA5 Entity Seed — $(date '+%Y-%m-%d %H:%M') =="
echo "   Seeding $TOTAL entities across 5 sections."
echo ""

# ---------------------------------------------------------------
# SECTION 1 — Maxwell Connolly, full portrait (1)
# ---------------------------------------------------------------
echo "-- Section 1: Maxwell Connolly (1) --"

seed_entity "person" "Maxwell Connolly" \
  '{"dob":"1988-08-23","birthplace":"San Diego, California","current_address":"3 Hartley Court, Milford NJ 08848","occupation":"Senior Director of Product Management","employer":"Labcorp Holdings","military":"US Army Reserves, Psychological Operations Specialist, enlisted 2011","education":"Kutztown University, Psychology, graduated 2013","tier":"major","profile_complete":true,"core_four":true,"notable":"Founder of Hammerfall Solutions, building in AI sector, debt-free March 2026"}' \
  '["Max"]'

# ---------------------------------------------------------------
# SECTION 2 — Major Placeholders (9)
# Awaiting full survey responses. Aliases seeded where known.
# Jennifer, Ian, Amy, Logan, Chris: no alias seeded — first-name
# reference will trigger Routine 4 contextual step (expected).
# ---------------------------------------------------------------
echo ""
echo "-- Section 2: Major Placeholders (9) --"

seed_entity "person" "Kimberly Connolly" \
  '{"tier":"major","source":"placeholder_awaiting_survey","profile_complete":false,"dob":"1989-11-10","relationship_to_maxwell":"spouse"}' \
  '["Kim"]'

seed_entity "person" "Jack Connolly" \
  '{"tier":"major","source":"placeholder_awaiting_survey","profile_complete":false,"relationship_to_maxwell":"father"}' \
  '[]'

seed_entity "person" "Emma Connolly" \
  '{"tier":"major","source":"placeholder_awaiting_survey","profile_complete":false,"dob":"2019-03-30","relationship_to_maxwell":"daughter"}' \
  '["Em","Emmy","Emma bug"]'

seed_entity "person" "Jennifer Connolly" \
  '{"tier":"major","source":"placeholder_awaiting_survey","profile_complete":false,"relationship_to_maxwell":"stepmother"}' \
  '[]'

seed_entity "person" "Ian Connolly" \
  '{"tier":"major","source":"placeholder_awaiting_survey","profile_complete":false,"relationship_to_maxwell":"brother","core_four":true}' \
  '[]'

seed_entity "person" "Amy Connolly" \
  '{"tier":"major","source":"placeholder_awaiting_survey","profile_complete":false,"relationship_to_maxwell":"mother"}' \
  '[]'

seed_entity "person" "Wesley Green" \
  '{"tier":"major","source":"placeholder_awaiting_survey","profile_complete":false,"relationship_to_maxwell":"best friend","core_four":true}' \
  '["Wes"]'

seed_entity "person" "Logan Whitaker" \
  '{"tier":"major","source":"placeholder_awaiting_survey","profile_complete":false,"relationship_to_maxwell":"best friend","core_four":true}' \
  '[]'

seed_entity "person" "Chris Wright" \
  '{"tier":"major","source":"placeholder_awaiting_survey","profile_complete":false,"relationship_to_maxwell":"friend and colleague at Labcorp"}' \
  '[]'

# ---------------------------------------------------------------
# SECTION 3 — Minor People and Pets (26)
# ---------------------------------------------------------------
echo ""
echo "-- Section 3: Minor People and Pets (26) --"

seed_entity "person" "Lily Connolly" \
  '{"dob":"2025-05-13","relationship_to_maxwell":"daughter","notes":"Second child, strongly bonded with Kim. Observant and quick — taking steps at 10 months."}' \
  '[]'

seed_entity "pet" "Sanchez" \
  '{"breed":"Terrier-Chihuahua mix","status":"deceased","deceased_date":"2026-03","notes":"First pet. Originally Ians dog. Adopted by Max when he moved to Ephrata with Kim."}' \
  '[]'

seed_entity "pet" "Krieger" \
  '{"breed":"Yellow Labrador mix","age_approx":13,"status":"living","notes":"Acquired January 2013, shortly after Max and Kim married. The family protector. Nearing end of life."}' \
  '[]'

seed_entity "pet" "Keeley" \
  '{"breed":"Golden Retriever, purebred","age_approx":2,"status":"living","notes":"Sweet and gentle. Terrible guard dog, fantastic companion. Loves pillows."}' \
  '[]'

seed_entity "person" "Carrie Sayers" \
  '{"relationship_to_maxwell":"mothers partner","occupation":"QA Auditor, Hilton","location":"Toms River NJ","notes":"Amys current partner. On and off for years before committing. Sweet, loving, honest."}' \
  '[]'

seed_entity "person" "Michelle Connolly" \
  '{"relationship_to_maxwell":"sister-in-law","notes":"Ians wife. Working class background, voracious reader, old school punker. Down to earth."}' \
  '[]'

seed_entity "person" "Mia Connolly" \
  '{"relationship_to_maxwell":"niece","dob_approx":"2025-05-30","notes":"Ian and Michelles daughter. Born about 3 weeks after Lily."}' \
  '[]'

seed_entity "person" "Mackenzie Connolly" \
  '{"relationship_to_maxwell":"half-sister","notes":"Jack and Jens daughter. Old soul, mature beyond her years. Recently engaged to Anthony Flora. Relocating to Florida July 2026."}' \
  '[]'

seed_entity "person" "Owen Connolly" \
  '{"relationship_to_maxwell":"half-brother","notes":"Jack and Jens son. Simple and content, lives with Jack and Jen. Emma loves him and they bond over Minecraft."}' \
  '[]'

seed_entity "person" "Donna Sharkey" \
  '{"relationship_to_maxwell":"mother-in-law","occupation":"Teacher","location":"Lancaster PA","notes":"Kims mother. Navigated loss of Greg. Now with Victor M. Allergic to technology — Max helps her often."}' \
  '[]'

seed_entity "person" "Gregory Sharkey" \
  '{"relationship_to_maxwell":"father-in-law","status":"deceased","deceased_date":"2016-11","occupation":"Career police officer and detective, later FEMA","notes":"Passed from sudden heart attack November 2016. Fantastic chef and host. Deeply loved by the family."}' \
  '["Greg","Papa Shark"]'

seed_entity "person" "Victor M" \
  '{"relationship_to_maxwell":"step-father-in-law","location":"Lancaster PA","notes":"Sharkey family friend for decades. Owned Venture Jets, retired after sale. Now engaged to Donna. Dotes on the family and travels extensively.","placeholder_last_name":true,"needs_alias_review":true,"encountered_as":"Victor M"}' \
  '[]'

seed_entity "person" "Michael Sharkey" \
  '{"relationship_to_maxwell":"brother-in-law","occupation":"Civilian weapons tester, Picatinny Arsenal NJ","notes":"Kims twin brother. Active duty Army veteran, deployed to Afghanistan 2013-2014. Former police officer. Simple and loyal."}' \
  '[]'

seed_entity "person" "Marissa Sharkey" \
  '{"relationship_to_maxwell":"sister-in-law","occupation":"Nutritionist, owns own business","notes":"Mikes wife. Fitness and nutrition enthusiast. Worked in hospital system during COVID. Loves cats and Nightmare Before Christmas."}' \
  '[]'

seed_entity "person" "Mary Jane Norman" \
  '{"relationship_to_maxwell":"grandmother (paternal)","notes":"Connolly family matriarch on Jacks side. Tough, old school firecracker. Raised 4 children poor and managed. Called Grandma or Gma."}' \
  '["Grandma","Gma"]'

seed_entity "person" "Ed Norman" \
  '{"relationship_to_maxwell":"grandfather (paternal)","occupation":"Retired general contractor, former Clinton YMCA director","notes":"Mary Janes husband. Professional photographer, avid cyclist, wine connoisseur, jack of all trades. The running joke is the only thing he cannot do is birth a human. Called Pops or Pop-pop."}' \
  '["Pops","Pop-pop"]'

seed_entity "person" "Jordan Whitaker" \
  '{"relationship_to_maxwell":"friend (Logans wife)","occupation":"Therapist at local high school","notes":"Focused and driven. Loves board games — regular game nights with Max, Logan, Kim. Loves gossip."}' \
  '[]'

seed_entity "person" "Brody Whitaker" \
  '{"relationship_to_maxwell":"pseudo-nephew (Logan and Jordans son)","age_approx":2,"notes":"Loves coming to the Connolly home. Outdoorsy, loves trucks, very much his fathers son."}' \
  '[]'

seed_entity "person" "Nicole Green" \
  '{"relationship_to_maxwell":"lifelong friend (Wes Green spouse)","notes":"One of Maxs oldest friends. Lost touch in teenage years but extended kindness when Max was near his lowest point. Likely saved his life. Sweet and loving."}' \
  '[]'

seed_entity "person" "Addison Green" \
  '{"relationship_to_maxwell":"pseudo-niece (Wes and Nicoles daughter)","notes":"Early teenage years. Loves drawing, writing, and playing basketball."}' \
  '[]'

seed_entity "person" "Isaac Green" \
  '{"relationship_to_maxwell":"pseudo-nephew (Wes and Nicoles son)","notes":"Genius level intellect. Recently began homeschooling to engage with material that actually challenges him. Loves gaming and Roblox."}' \
  '[]'

seed_entity "person" "Giovanni Macrina" \
  '{"relationship_to_maxwell":"direct supervisor at Labcorp","occupation":"Vice President, Labcorp Holdings","notes":"Max and Chris Wrights supervisor. Model VP — fair, poised, and professional."}' \
  '[]'

seed_entity "person" "Anthony Flora" \
  '{"relationship_to_maxwell":"future brother-in-law (Mackenzies fiance)","notes":"Same age as Max, went to high school together. Owned a successful modeling agency. Scaled back recently. Wonderful to Mackenzie."}' \
  '[]'

seed_entity "person" "Earl Clark" \
  '{"relationship_to_maxwell":"step-grandfather (maternal, Robins husband)","status":"deceased","deceased_date_approx":"2010","military":"US Marine Corps, Korean War veteran","notes":"True blue Marine who loved the Corps above all else. Hummed parade songs around the house. Called Sarge. Max was his caretaker in Arizona for the final months of his life — a pivotal period for Max."}' \
  '["Sarge"]'

seed_entity "person" "Robin Clark" \
  '{"relationship_to_maxwell":"grandmother (maternal)","status":"deceased","notes":"Amys mother. From a well-to-do family. Social butterfly who loved bridge and conversation. Had a stroke and suffered aphasia in her final years — torture for a woman who lived to communicate. Called Nana."}' \
  '["Nana"]'

seed_entity "person" "Joel Williams" \
  '{"relationship_to_maxwell":"grandfather (maternal, Robins first husband)","notes":"Wrong side of the tracks kid, old school Italian type. Loved tall tales and embellishment. Complicated man but loved his family and always tried to do right by them. Called Grandpa."}' \
  '[]'

# ---------------------------------------------------------------
# SECTION 4 — Places (22)
# Personal context from source documents.
# Public facts (population, county, geography) from public record.
# Private addresses carry personal context only.
# ---------------------------------------------------------------
echo ""
echo "-- Section 4: Places (22) --"

seed_entity "place" "Alexandria Township NJ" \
  '{"county":"Warren County, NJ","type":"township","description":"Rural, rustic township in western NJ along the Delaware River. Small population, agrarian character. Max and Kims current home township.","connection_to_maxwell":"Current residence"}' \
  '[]'

seed_entity "place" "Alexandria Township School" \
  '{"type":"public school","location":"Alexandria Township, NJ","connection_to_maxwell":"Emma currently enrolled. Ian attended 7th and 8th grade here."}' \
  '[]'

seed_entity "place" "Milford New Jersey" \
  '{"county":"Hunterdon County, NJ","type":"borough","description":"Small Delaware River borough in western NJ, population approximately 1200. Historic river town. Adjacent to Alexandria Township.","connection_to_maxwell":"Borough where Max and Kims address (Hartley Court) is registered"}' \
  '[]'

seed_entity "place" "3 Hartley Court, Milford NJ 08848" \
  '{"type":"residence","connection_to_maxwell":"Max and Kims current home, purchased June 2022. Dream home, significant financial investment."}' \
  '[]'

seed_entity "place" "Riegelsville PA" \
  '{"county":"Bucks County, PA","type":"borough","description":"Small Delaware River borough in eastern PA, directly across from Milford NJ. River town character.","connection_to_maxwell":"Where Max and Ian grew up with Jack and Jen. Max and Kim bought their first home here (127 Sycamore Road)."}' \
  '[]'

seed_entity "place" "118 Maplewood Road, Riegelsville PA" \
  '{"type":"residence","connection_to_maxwell":"Jack and Jens home. Where Max, Ian, Mackenzie and Owen grew up on their fathers side."}' \
  '[]'

seed_entity "place" "Holland Township NJ" \
  '{"county":"Hunterdon County, NJ","type":"township","description":"Rural township neighboring Alexandria Township in western NJ along the Delaware River.","connection_to_maxwell":"Where Max and Ian grew up with Amy. Max attended Holland Township School grades 2-8."}' \
  '[]'

seed_entity "place" "Holland Township School" \
  '{"type":"public school","location":"Holland Township, NJ","connection_to_maxwell":"Max attended grades 2-8 here."}' \
  '[]'

seed_entity "place" "Bellis Road, Milford NJ" \
  '{"type":"road","connection_to_maxwell":"The road where Max, Amy, and Ian lived in Holland Township during his grammar school years."}' \
  '[]'

seed_entity "place" "266 Pittstown Road, Pittstown NJ" \
  '{"type":"residence","connection_to_maxwell":"The home Amy moved to when Max finished 8th grade — the move Max resented. He and Ian lived here with Amy from 2003 through roughly 2015. Max and Kim also lived here briefly around 2014."}' \
  '[]'

seed_entity "place" "Pittstown NJ" \
  '{"county":"Hunterdon County, NJ","type":"unincorporated community","description":"Small rural community in Alexandria Township, Hunterdon County NJ.","connection_to_maxwell":"Where Max and Ian lived with Amy from 2003 onwards."}' \
  '[]'

seed_entity "place" "Glen Gardner NJ" \
  '{"county":"Hunterdon County, NJ","type":"borough","description":"Small borough in Hunterdon County NJ.","connection_to_maxwell":"Kims childhood hometown. Greg, Donna, Kim and Mike grew up here. Max and Kim lived at 13 Carol Court for roughly 1.5 years (2020-2022) before buying Hartley Court."}' \
  '[]'

seed_entity "place" "13 Carol Court, Glen Gardner NJ" \
  '{"type":"residence","connection_to_maxwell":"The Sharkey family home. Max and Kim lived here 2020-2022. Mike and Marissa currently live here."}' \
  '[]'

seed_entity "place" "Clinton New Jersey" \
  '{"county":"Hunterdon County, NJ","type":"borough","description":"Historic borough known for its red mill and waterfall. Central Hunterdon County location.","connection_to_maxwell":"Central location in Connolly and Sharkey family history. Max proposed to Kim on the Clinton bridge."}' \
  '[]'

seed_entity "place" "New York City" \
  '{"state":"New York","type":"city","description":"Most populous US city, global financial and cultural center. Five boroughs: Manhattan, Brooklyn, Queens, the Bronx, Staten Island. Population approximately 8.3 million.","connection_to_maxwell":"Primary work destination for Max and Kim 2014-2022. Enabling period for their financial growth and quality of life."}' \
  '[]'

seed_entity "place" "Jersey City NJ" \
  '{"county":"Hudson County, NJ","type":"city","description":"Second largest city in NJ, directly across the Hudson River from lower Manhattan. Major transit hub via PATH train.","connection_to_maxwell":"Where Max and Kim lived twice between 2014 and 2019. First real quality of life step up. Two apartments: Dudley Street and Soho Lofts."}' \
  '[]'

seed_entity "place" "Dudley Street, Jersey City" \
  '{"type":"street","connection_to_maxwell":"Street where Max and Kim had their first Jersey City apartment. Park nearby, walking distance to transit. One of their best decisions — quality of life increased dramatically."}' \
  '[]'

seed_entity "place" "Soho Lofts, Jersey City" \
  '{"type":"apartment complex","connection_to_maxwell":"Max and Kims second Jersey City apartment. Where Emma was born. They loved it and only left due to COVID risk assessment in March 2020."}' \
  '[]'

seed_entity "place" "Meadow Valley Road, Ephrata PA" \
  '{"type":"road","connection_to_maxwell":"Road where Max and Kim had their first apartment after marrying. The first place they felt was genuinely their own home."}' \
  '[]'

seed_entity "place" "Ephrata PA" \
  '{"county":"Lancaster County, PA","type":"borough","description":"Borough in Lancaster County PA, rural Lancaster County character.","connection_to_maxwell":"Where Max and Kim lived immediately after getting married (2012-2013). First apartment on Meadow Valley Road. Rural, first place to feel like home."}' \
  '[]'

seed_entity "place" "Lancaster PA" \
  '{"county":"Lancaster County, PA","type":"city","description":"City in Lancaster County PA, population approximately 60000. Known for proximity to Pennsylvania Dutch country.","connection_to_maxwell":"Max and Kims second move after Ephrata. Donna and Vic currently live here. Max and Kim love visiting."}' \
  '[]'

seed_entity "place" "652 Wyncroft Lane, Lancaster PA" \
  '{"type":"residence","connection_to_maxwell":"Max and Kims Lancaster apartment address."}' \
  '[]'

# ---------------------------------------------------------------
# SECTION 5 — Organizations (6)
# Public factual data from public record.
# Maxwell personal context from source documents.
# ---------------------------------------------------------------
echo ""
echo "-- Section 5: Organizations (6) --"

seed_entity "organization" "Medidata Solutions" \
  '{"industry":"Life sciences software, clinical trial management","headquarters":"New York City, NY","description":"Clinical data technology company serving pharma and biotech. Acquired by Dassault Systemes in 2019 for approximately 5.8 billion USD.","connection_to_maxwell":"Where Max got his big break. Joined as contractor 2014-2015, hired full-time December 2015, breached 6 figures. Later returned February 2019 after Venmo. One of his happiest professional periods."}' \
  '[]'

seed_entity "organization" "Venmo" \
  '{"industry":"Fintech, peer-to-peer payments","headquarters":"New York City, NY","description":"P2P payment platform, PayPal subsidiary. Launched 2009, acquired by PayPal 2013.","connection_to_maxwell":"Max joined in 2018. A squandered opportunity and key learning — taught him humility and to listen first. Left to return to Medidata February 2019."}' \
  '[]'

seed_entity "organization" "Labcorp Holdings" \
  '{"industry":"Clinical laboratory services, life sciences CRO","headquarters":"Burlington, NC","description":"One of the largest clinical laboratory and drug development services companies in the world. Revenue approximately 14 billion USD annually.","connection_to_maxwell":"Max joined 2022 as Senior Director of Product Management. Significant pay increase but Max despises the company culture. Escape from Labcorp is a primary motivation for Hammerfall and the AI sector pivot."}' \
  '[]'

seed_entity "organization" "Grimnir Tactical" \
  '{"industry":"Airsoft production, narrative gaming","type":"small business, largely dormant","connection_to_maxwell":"Started by Max, Ian, Wes and Logan. Ran interconnected narrative airsoft games over 2-3 years of operations. Player actions influenced the story. Ceased regular operations around 2024. Games held in high regard by players. One Hammerfall pipeline project (IBIS) is related to the airsoft industry."}' \
  '["GT"]'

seed_entity "organization" "SciMedMedia" \
  '{"industry":"Science and medical communications, startup","location":"New York City, NY","connection_to_maxwell":"Max first NYC employer. Found through old contacts while on military orders at NTC California. Quit the nuclear powerplant job to take this role. Left when an opportunity arose to join Medidata. Described as a toxic startup environment."}' \
  '[]'

seed_entity "organization" "Venture Jets" \
  '{"industry":"Private jet charter","location":"Lancaster PA","connection_to_maxwell":"Victor Ms company, which he owned and recently sold before retiring. Victor dotes on Donna using proceeds from the sale."}' \
  '[]'

echo ""
echo "== Entity seeding complete: $COUNT/$TOTAL entities written. =="
