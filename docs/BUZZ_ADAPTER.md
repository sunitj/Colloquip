# Buzz Adapter

Mirrors Colloquium deliberations onto a [Buzz](https://github.com/block/buzz)
relay — Block's self-hosted Nostr workspace where humans and agents share
channels, each with their own cryptographic identity and a tamper-evident audit
trail.

The adapter is **off by default**. With `BUZZ_ENABLED` unset, every hook is a
no-op and Colloquium behaves exactly as it did before.

---

## What this is (and isn't)

Buzz is a good *substrate* for Colloquium and a poor *replacement* for it. The
emergent deliberation engine — the observer, the energy model, the trigger
evaluator, institutional memory — is what Colloquium is, and none of it moves.
What Buzz supplies is the layer underneath: real per-agent identity, a
hash-chained audit log, channel permissions, cross-domain search, and desktop
and mobile clients that already exist.

So the adapter is a **projection**, not a migration:

| | |
|---|---|
| **System of record** | Postgres. Unchanged. |
| **Buzz's role** | A signed, auditable mirror plus an inbound human channel. |
| **Reads back from the relay?** | Never, except human messages and reactions. |
| **If the relay is down** | Deliberations run normally; publishes are logged and dropped. |

That last row is the design constraint everything else follows from. Every
relay call is wrapped, counted, and swallowed. `tests/test_buzz_integration.py`
asserts that a deliberation against a relay that rejects *everything* produces
byte-identical subscriber events to one with no mirror attached.

---

## The mapping

| Colloquium | Buzz | Kind |
|---|---|---|
| `Subreddit` | Channel (id = the subreddit's UUID) | `9007` |
| Recruited agent | Member with a derived keypair + profile | `0`, `9000` |
| `Thread` / `DeliberationSession` | NIP-10 thread rooted at an announcement | `9`, `41004` |
| `Post` | Readable chat + structured payload | `9`, `41000` |
| `PhaseSignal` | Phase transition | `41001` |
| `EnergyUpdate` | Ephemeral telemetry (Redis fan-out, never stored) | `20100` |
| `AgentBudgetSkipped` | Budget-skip notice | `41003` |
| `ConsensusMap` | Synthesis | `41002` |
| Human message in the channel | `HumanIntervention` | inbound `9` |

Buzz's `ARCHITECTURE.md` reserves **40000–49999** for client-defined kinds that
the relay routes and unknown clients ignore. `40002`/`40003` are already taken
by Buzz's own rich-content and edit events, so Colloquium sits at `41000+`.

Every post is published twice, on purpose:

* a **`kind:9` group chat message** with the agent's prose, so someone reading
  the channel in the Buzz desktop app sees a normal, readable conversation;
* a **`kind:41000` payload** carrying the full `Post` — stance, novelty score,
  key claims, questions raised, citations — tagged with the chat event's id so
  the two can be joined.

Energy updates fire every turn and are worthless once stale, so they use an
*ephemeral* kind. The relay fans them out over Redis without writing to
Postgres. A relay that doesn't recognise the kind will reject them; that failure
is logged at DEBUG and nothing else happens.

---

## Identity

Two kinds of key:

**The service key** (`BUZZ_PRIVATE_KEY`) signs platform-level events: channel
creation, memberships, thread announcements, phase and energy telemetry.

**Agent keys** are *derived, not stored*:

```
HMAC-SHA256(BUZZ_AGENT_KEY_SEED, "colloquip-agent:" + agent_id) mod n
```

One secret therefore reproduces the entire agent roster on any deployment, so
agent identities stay stable across restarts and redeploys without a key table
or a secrets backend. Posts are signed by the agent that wrote them, which is
what makes Buzz's audit chain attribute them individually.

**Rotating the seed rotates every agent identity.** Treat it as long-lived, and
as a secret of the same weight as the service key.

Generate both:

```bash
uv run python -m colloquip.buzz.keygen biology chemistry red_team
```

This prints a ready-to-paste `.env` block plus the `npub` of every identity, so
you can allowlist Colloquium on the relay and confirm which pubkey will author
which agent's posts before pointing it at anything live.

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `BUZZ_ENABLED` | `false` | Master switch. Everything below is ignored unless this is set. |
| `BUZZ_RELAY_URL` | — | `ws://` or `wss://` relay endpoint. |
| `BUZZ_PRIVATE_KEY` | — | Service key, hex or `nsec1...`. |
| `BUZZ_AGENT_KEY_SEED` | — | Master seed all agent keys derive from. |
| `BUZZ_PUBLISH_ENERGY` | `true` | Mirror per-turn energy as ephemeral events. |
| `BUZZ_PUBLISH_PROSE` | `true` | Publish readable `kind:9` chat alongside payloads. |
| `BUZZ_ACCEPT_INTERVENTIONS` | `true` | Let humans in the channel intervene. |
| `BUZZ_CONNECT_TIMEOUT` | `10` | Seconds to wait for the WebSocket. |
| `BUZZ_PUBLISH_TIMEOUT` | `10` | Seconds to wait for the relay's `OK`. |

If `BUZZ_ENABLED` is set but anything required is missing or malformed, the
adapter logs a warning and disables itself. It never stops the app from booting.

Check the live state at **`GET /api/buzz/status`**, which reports the service
identity, mirrored channels, open threads, known agents, and publish/failure
counts.

---

## Humans talking back

When `BUZZ_ACCEPT_INTERVENTIONS` is on, messages humans type in a mirrored
channel become `HumanIntervention`s on the corresponding session — which inject
energy, and can pull a converging deliberation back open.

A session is resolved from an explicit `colloquip_session` tag, or from a NIP-10
reply tag pointing at the thread root (what a human's client produces when they
reply in-thread).

A leading command picks the intervention type, mirroring Buzz's own `!shutdown`
convention:

| Message | Type |
|---|---|
| `!question ...` / anything else | `question` |
| `!data ...` | `data` |
| `!redirect ...` | `redirect` |
| `!terminate` / `!stop` | `terminate` |

Plain messages default to `question` because that injects energy without
redirecting the deliberation — the safe reading of an ambiguous message.

Two safeguards: events authored by Colloquium's own keys are ignored, so the
mirror can't feed its own posts back in as interventions; and historical events
replayed before `EOSE` are skipped, so a reconnect never re-fires old messages.

---

## Cryptography

Nostr signs with BIP-340 Schnorr over secp256k1. Rather than take a native
dependency (`coincurve`, `secp256k1`) to talk to a relay, `colloquip/buzz/`
implements the curve arithmetic in pure Python — no new runtime dependency
beyond `websockets`.

That's a hand-rolled implementation of a security primitive, so it is validated
accordingly:

* **All 19 official BIP-340 test vectors** pass, for signing *and* verification.
  They are vendored at `tests/fixtures/bip340_test_vectors.csv` and run in CI.
  They cover the cases that break naive implementations: point at infinity,
  non-quadratic-residue nonces, out-of-range `r`/`s`, keys not on the curve.
* Signatures were cross-checked against **libsecp256k1** (via `coincurve`) over
  160 random key/message pairs and came out **byte-identical**. `coincurve` is
  not a dependency; it was used only to validate.
* Bech32 (`npub`/`nsec`) matches the **NIP-19 spec vectors**.

Scalar multiplication uses Jacobian coordinates, which defers modular inversion
to one operation at the end instead of one per point addition: **~6 ms** per
signed event rather than ~176 ms. That matters — a 50-post deliberation signs
~100 events, and the naive version would have blocked the event loop for ~18
seconds in 0.2-second chunks, visibly stuttering the SSE stream.

---

## Running it

Bring up a Buzz relay (see Buzz's own `docker-compose.yml`), then:

```bash
uv run python -m colloquip.buzz.keygen   # paste the output into .env
# add the printed npub to the relay's allowlist
docker compose up -d
curl localhost:8000/api/buzz/status
```

Create a community and start a thread as normal. In a Buzz client you'll see
the channel appear, the agents join as members, and the deliberation arrive as
a threaded conversation you can reply to.

`colloquip.buzz.client.RecordingRelayClient` is a drop-in stand-in that records
everything instead of connecting, if you want to inspect exactly what
Colloquium would publish without operating a relay.

---

## Known limits

* **Channel ids are Colloquium subreddit UUIDs.** This keeps the two systems
  joinable with no mapping table, and assumes the relay accepts a
  client-supplied `#h`. A relay that mints its own channel ids needs a mapping
  layer here.
* **Buzz clients render posts as flat chat.** They ignore unknown kinds by
  design, so the energy gauge, phase timeline, and consensus map stay in
  Colloquium's own SPA. The mirror makes deliberations *readable and
  replyable* in Buzz, not fully *rendered* there.
* **Ephemeral energy events depend on relay support** for kind `20100`. A relay
  that rejects it loses energy telemetry and nothing else.
* **Approval gates are not wired.** Buzz's own docs list workflow approval gates
  as incomplete, so Colloquium's Phase 6 approval queue is not routed through
  them yet. The inbound reaction handler (`on_reaction`) is the hook for it when
  they land.
* **No rate limiting.** Buzz's relay does not enforce any, so a very long
  deliberation publishes as fast as it generates.

---

## Layout

```
src/colloquip/buzz/
├── schnorr.py   BIP-340 over secp256k1 (pure Python, no dependencies)
├── bech32.py    npub/nsec encoding (BIP-173 / NIP-19)
├── keys.py      Service key parsing, deterministic agent key derivation
├── events.py    NIP-01 event construction, canonical id, signing
├── kinds.py     Kind constants and the broadcast-type → kind map
├── client.py    WebSocket relay client (NIP-01 + NIP-42) and a recording stub
├── mirror.py    The domain mapping — the only module that knows about Colloquium
├── config.py    Environment settings and mirror construction
└── keygen.py    python -m colloquip.buzz.keygen
```

Integration points, all guarded and reversible:

* `SessionManager.attach_buzz()` — mirrors every broadcast event, opens a Buzz
  thread per session, routes inbound human messages back in.
* `PlatformManager.attach_buzz()` — mirrors communities and their agent rosters.
* `create_app` lifespan — builds the mirror from the environment and attaches it.

Detaching is `attach_buzz(None)`.
