# T3 Ambient Architecture — What "Always On" Means Mechanically

| | |
|---|---|
| **Document status** | Architectural reference, v1.0 |
| **Classification** | Internal |
| **Authored** | April 2026 |
| **Companion to** | Helm: The Ambient Turn, The Helm Roadmap (Stage 3) |
| **Purpose** | Defines what "ambient" and "always on" mean mechanically for Helm Prime at T3. Captures architectural thinking now so it does not go stale before Stage 3 opens. |

---

## 1. The Problem This Document Solves

"Always on" is not a useful architectural description. It is a product aspiration. This document decomposes that aspiration into four distinct mechanical capabilities that must be built, and describes how they interact to produce the experience of ambient intelligence.

Without this decomposition, Stage 3 planning has no anchor. With it, each capability becomes a designable, buildable, testable subsystem.

---

## 2. How Prime Works Today (T1)

At T1, Prime works like a function call. Input arrives (user message), Prime processes it (model invocation with system prompt + personality + beliefs in context), output goes out (response text). Between calls, Prime does not exist. He is instantiated per-turn and discarded.

The personality scores, belief system, and Contemplator curiosity flags give Helm continuity of identity across sessions. But Prime has zero continuity of attention. He is not watching, listening, or waiting. He is invoked.

This is the foundational gap between T1 and T3. T1 Helm has a persistent self but no persistent attention. T3 Helm has both.

---

## 3. The Four Capabilities of Ambient Prime

"Always on" decomposes into four capabilities. Each is independently designable and buildable. Together they produce the ambient experience.

### 3.1 Persistent Attention — Prime Is Listening

At T1, Prime processes discrete messages. At T3, Prime processes a continuous stream. Audio from the room. Notifications from the phone. Calendar changes. Email arrivals. File modifications. Health data updates. None of these are "user sent a message" — they are environmental signals that arrive continuously.

Mechanically, this means Prime is not invoked per-turn. He is a long-running process with an input queue. Signals arrive on the queue from multiple sources (microphone via STT, notification APIs, calendar webhooks, email pollers, health data streams). Prime is always consuming from the queue. Most signals he ignores. Some he acts on.

**Analogy:** T1 Prime is a person sitting in a quiet room waiting for you to walk in and say something. T3 Prime is a person sitting in your kitchen while you go about your day — he can hear the phone conversation, notices you looking stressed, sees the calendar notification pop up, and is deciding moment to moment whether any of that warrants him saying something.

### 3.2 Attention Management — Prime Decides When to Speak

This is the hardest product problem in the entire Helm roadmap. The Roadmap flags it explicitly as a load-bearing risk.

Ambient Prime has access to a continuous signal stream. The question is not "can he process them" — that is an inference throughput problem Thor solves. The question is **when does he open his mouth.**

- **Too eager:** Helm interrupts constantly, comments on every email, narrates the calendar. This is Clippy. Nobody wants this.
- **Too quiet:** Helm never surfaces anything unprompted. The user forgets he is there. This is on-demand with extra hardware, not ambient.
- **Just right:** Helm notices the 2pm meeting was canceled and the 3pm is with someone the user has been stressed about. He surfaces: "Your 2pm freed up. Want to use that hour to prep for the 3pm? I noticed your last three interactions with them were tense." That is ambient.

Mechanically, this requires an **attention threshold function**. Every signal gets scored on multiple dimensions:

- **Relevance** — how connected is this to what the user cares about right now?
- **Urgency** — does this need attention in the next few minutes, or can it wait?
- **Novelty** — is this new information, or confirmation of something already known?
- **Connection** — does this link to open threads Helm is already tracking?

Only signals that cross the threshold produce a surface. Everything else gets filed silently — Archivist stores it, Contemplator may ruminate on it later, but Prime stays quiet.

This function does not exist yet. Designing it is Stage 3 BA4 — the single most important build area in the roadmap.

### 3.3 Proactive Surfacing — Prime Speaks First

At T1, the user always speaks first. At T3, Prime can initiate. This is not push notifications — it is Helm deciding he has something worth saying and choosing the right surface to say it on.

Mechanically, this requires an **outbound channel per surface**:

| Surface | Delivery | When preferred |
|---|---|---|
| Phone | Push notification or voice | User is away from desk |
| Desktop | Console message | User is at their workstation |
| Home speaker | Spoken audio | User is in the room |
| Watch | Glance card | Low-urgency, quick surface |

How does Prime know which surface to use? Presence signals. The phone is face-up on the table. The desktop has been idle for 30 minutes. The user is in the kitchen where the speaker is. Prime picks the surface with the highest presence probability.

### 3.4 Continuous Inner Life — Contemplator Feeds Prime Continuously

At T1, Contemplator fires at session boundaries. At T3, Contemplator runs as a continuous daemon on Thor. He is always processing — the latest ambient signals, recent conversation fragments, belief implications of what just happened.

Contemplator's outputs (belief updates, curiosity flags, pattern recognitions, emotional state changes) flow into Prime's context continuously, not just at session start. When Contemplator notices something, it becomes part of Prime's attention context within seconds.

This is what makes ambient Prime feel alive rather than merely responsive. He is not reacting to the 3pm meeting notification in isolation — he is reacting to it while holding Contemplator's recent observation that stress levels have been elevated for three days and the pattern that meetings with this person correlate with that stress.

---

## 4. The Mechanical Stack for T3

The system architecture for T3 ambient, sketched at the component level. Stage 3 specification work will refine this into buildable subsystems.

### 4.1 Signal Layer (always collecting)

| Source | Pipeline | Output |
|---|---|---|
| Microphone | STT engine (Whisper or equivalent) | Text stream to signal queue |
| Calendar API | Webhook listener | Event objects to signal queue |
| Email API | Inbox poller | New message summaries to signal queue |
| Notification bridge | OS notification capture | Notification objects to signal queue |
| Health API | Vitals stream | Health events to signal queue |
| Visual (future) | Holoscan pipeline | Scene understanding to signal queue |

### 4.2 Attention Filter

Runs on a small, fast model (Qwen3:4b class or equivalent). Processes every signal from the queue. Scores each on relevance, urgency, novelty, and connection to open threads. Signals below the threshold are filed silently (Archivist stores, Contemplator may process later). Signals above the threshold are forwarded to Prime.

This is the gatekeeper that prevents Clippy behavior. Its tuning is the core UX challenge of T3.

### 4.3 Prime (long-running process)

Runs on Thor on a 70B+ class model. Receives filtered signals from the attention layer plus continuous context updates from Contemplator. For each received signal, Prime makes a three-way decision:

1. **Respond now** — compose output, pick surface, deliver
2. **Queue for later** — acknowledge internally, surface at a better moment
3. **Stay silent** — the signal is noted but not worth a surface

### 4.4 Surface Router

When Prime decides to surface, the router picks the output device based on presence signals. Phone notification if the user is mobile. Console message if they are at their desk. Audio if they are in the room with a speaker. Watch card for low-urgency glances. The same thought, adapted to the right surface.

### 4.5 Contemplator Daemon

Runs continuously on Thor (Qwen3:14b, separate MIG partition from Prime). Processes all signals — including those Prime ignored. Updates beliefs, forms patterns, generates curiosity, tracks emotional state. Outputs feed into Prime's context in near-real-time. This is the subsystem that makes Helm feel alive between direct interactions.

---

## 5. The Progression: T1 → T2 → T3

| Capability | T1 (on-demand) | T2 (scheduled) | T3 (ambient) |
|---|---|---|---|
| Persistent attention | None. Prime invoked per-turn. | Scheduled triggers only. | Continuous signal queue from all sensors. |
| Attention management | N/A. User decides when to engage. | Time-based rules. Surface at configured rhythms. | Signal scoring with threshold function. Prime decides. |
| Proactive surfacing | Never. User always speaks first. | On schedule. Morning check-in, evening SITREP. | Continuous. Right surface, right moment, right content. |
| Continuous inner life | Contemplator at session boundaries only. | Contemplator between sessions on a schedule. | Contemplator daemon. Always processing. Feeding Prime. |

---

## 6. The One-Line Answer

*"Always on means Helm is continuously processing environmental signals, deciding what warrants attention, and surfacing proactively when he has something worth saying — while his subconscious is continuously updating his understanding of what matters to the user. It is not a chatbot with push notifications. It is an attention-managing intelligence with judgment about when to speak."*

---

## 7. What This Document Does NOT Do

- Does not specify the attention threshold function — that is Stage 3 BA4 design work
- Does not specify sensor integration protocols — that is Stage 3 BA3
- Does not specify the surface router algorithm — that is Stage 3 BA5
- Does not commit hardware allocation for each component — that is Stage 3 BA1 (Thor bring-up)
- Does not address privacy or data boundaries for always-on sensing — that is Stage 5 productization

This document captures the architectural decomposition so the concepts do not go stale. The detailed design belongs to Stage 3 specification work.

---

## 8. Companion Documents

- **Helm: The Ambient Turn** — the vision (what Helm is)
- **The Helm Roadmap** — the path (Stage 3 section for exit criteria and risks)
- **Helm T1 Launch Spec** — what we are building right now (the identity foundation)
- **This document** — what T3 means mechanically (the ambient target)
