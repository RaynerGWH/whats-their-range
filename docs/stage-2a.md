# Stage 2A delivery

Complete on `feat/pokerth-opponents`, based on Stage 1 delivery
`01f3a8120790fbdad4d8589962be6d90fcb7d8b7`. Final implementation and evidence
revision: `c2131d4`. This report is committed separately after that revision.
Shared project context revision 12 was read at start and rechecked at delivery.

The application now completes six-player PokerKit tournaments with five real
PokerTH engine 4 opponents and the existing hero `Agent.decide(observation)`.
New UI tables select PokerTH by default. Hero mode remains independently selectable
as Heuristic baseline or OpenRouter. Legacy heuristic opponents remain explicit
in the UI and the compatibility default for API clients omitting `opponents`.
Historical snapshots and replay need no migration.

## Delivered history

| Commit | Change |
| --- | --- |
| `6f3b965` | Verified vendored PokerTH core, bounded native bridge and offline build |
| `4773341` | Private adapter, independent RNG and memory, worker/evaluation integration, UI and native regression tests |
| `c2131d4` | Setup-error guidance, CI build prerequisite, recorded smoke/browser evidence and reproduction tools |

No main merge, remote push, deployment, paid provider call, extra agent or
cross-chat message was made. Other checkouts and canonical planning documents
were not edited. Reserved QA ports 8012/5175 were checked before use; both
servers were stopped and the temporary browser tab closed after verification.

## Native source and setup

Upstream is [PokerTH v2.1.10, revision 0a7dceb575d8b9dfcbd7c46ec7a90482cbdb40ba](https://github.com/pokerth/pokerth/tree/0a7dceb575d8b9dfcbd7c46ec7a90482cbdb40ba).
Eleven unmodified files are vendored: four C++ implementations and their headers,
`tools.h`, `game_defs.h` and `COPYING`. Each Git blob ID was checked against the
pinned upstream tree. [upstream.json](../native/pokerth/upstream.json) also records
SHA-256 checksums, checked by every build. Original notices and AGPL version 3 or
later are retained. See [native source and license notes](../native/pokerth/README.md).

The WTR wrapper replaces only the `Tools::GetRand` dependency with separately
seeded `mt19937_64` and rejection sampling. The four upstream implementation files
are unchanged. Position and stack semantics were additionally checked against
[the pinned LocalPlayer adapter](https://github.com/pokerth/pokerth/blob/0a7dceb575d8b9dfcbd7c46ec7a90482cbdb40ba/src/engine/local_engine/localplayer.cpp).
No research temporary path or fixed research RNG seed is used at runtime.

From the repository root, with Python 3 and a C++20 compiler:

```sh
python3 scripts/build_pokerth.py
native/pokerth/build/pokerth-opponent --version
npm ci
cd apps/api
uv sync --frozen --extra test
```

The verified local compiler was Apple Clang 21.0.0. The ignored
`native/pokerth/build/build.json` records compiler and bridge-source provenance;
this delivery copies that provenance into the smoke report. Clang emits one
warning about intentional adjacent string literals in the unchanged upstream
preflop chart. The local build and native tests pass.

There is no Qt, full PokerTH application, OpenSSL or network dependency in the
native build. Each decision runs in a fresh subprocess with a two-second timeout,
a 1,024-character input bound, validated cards/chip counts/personality parameters,
and a three-integer result checked by Python. Native errors do not echo inputs.
Subprocess exit disposes all native RNG state. Missing or incompatible binaries
produce setup guidance, never silent legacy substitution. Worker failures become
visible terminal errors; evaluation records `pokerth_setup_error` or
`pokerth_decision_error` with safe controller guidance.

The CI workflow builds the native core before API tests. The Docker template now
uses repository-root context, compiles the core in a build stage, includes its
source/license and installs the C++ runtime. The Fly template points to that
root-context Dockerfile. Docker/Linux builds and hosted CI were not executed in
this local milestone; no deployment is claimed.

## Observation, memory and action mapping

`Opponents.decide` takes a reconstructed permitted observation. It never receives
a Tournament object, spectator snapshot, future cards or any opponent's hole
cards. The native call gets the acting player's two cards, public board, street,
stack and committed bet, highest street bet, public pot/bets, blinds, legal-menu
minimum increment, remaining opponents, unacted opponents and public statistics.
All-in opponents remain counted for showdown equity. Effective opponent cash is
the largest remaining stack plus committed street bet, matching upstream.

PokerTH's raise intention is an increment above the highest bet. The adapter
converts it to a street total, clamps it to the actor's stack plus committed bet,
and selects the nearest available legal raise-to size, with lower size breaking
ties. A bet intention is already a street total. All-in uses the actor's total
available street contribution. If no raise is available, including a short all-in
that did not reopen action, the adapter checks/calls. Fold/check/call intentions
are similarly normalized to the actual menu. The worker applies that action with
the original observation version, and PokerKit revalidates it.

The menu contains PokerKit's minimum and maximum raise plus half-pot and pot
sizes. **This is a discrete sizing approximation, not exact desktop PokerTH
play.** Short all-in minimum increments come from that legal menu. PokerTH derives
its internal big blind as twice the small blind; odd scheduled big blinds can
therefore differ by one chip in its heuristic calculations. PokerKit still posts
and enforces the actual blinds. PokerTH uses the aggregate pot for decisions and
does not model each player's side-pot eligibility or tournament payout utility.
PokerKit owns legal side-pot settlement.

A table-local six-player statistics bank observes every committed public action,
including after hero folds. One preflop opportunity means a hand in which that
player actually had a voluntary decision; forced blind all-ins are excluded.
VPIP counts at most one paid call or raise per such hand. Postflop aggression is
bets/raises divided by all voluntary postflop decisions, including checks/folds.
Rates pool currently active opponents and stay unknown until ten opportunities
of the relevant kind have been observed. These explicit definitions differ from
the desktop application's per-player sample thresholds and averaging. They are
public behavioral summaries, not inferred private ranges.

Deck RNG, hero RNG, per-seat opponent RNG and personality assignment RNG are
separate. Omitted interactive `hero_seed`, `opponent_seed` and `personality_seed`
are independently generated and saved only in controller/spectator configuration.
Supplying all seeds permits reproduction. A SHA-256 namespace derives distinct
opponent streams per seat. Each native call gets a new seed drawn from its seat's
stream. Personality tuples and legacy profiles are privately shuffled across
neutral identities between tournaments; names stay stable within a tournament.
New tables create fresh policy/statistics objects.

## Verification actually run

From the repository root:

```sh
python3 scripts/build_pokerth.py
LANGSMITH_TRACING=false LANGCHAIN_TRACING_V2=false apps/api/.venv/bin/pytest -q apps/api/tests
npm run check
npm run test -w apps/web
npm run build
git diff --check
```

Final API result: **128 passed, 1 skipped**. The skip is the existing opt-in
PostgreSQL test. Frontend: **16 tests passed**, TypeScript and production build
passed. Ruff `F` checks passed on the changed Python implementation and scripts.

The 20 new native integration tests cover actual native calls on all four streets
and two through six players, legal raise-increment conversion, stack caps, short
all-ins without reopening, side-pot settlement, malformed output, bounded invalid
native input, timeout, missing builds, public statistics, shuffled assignments,
distinct seat RNGs, unchanged deck RNG and isolated table memory. A passive legal
execution fixture reaches every street while querying the native adapter at each
spot; it is distinct from the fully native tournament evidence below.

Production worker tests complete two independent processes using real native
opponents. One runs the heuristic hero and one runs the actual Agent provider
path with `httpx.MockTransport`. Tests verify pause, step, resume, stop/cleanup,
heads-up play, chip conservation, non-negative stacks, isolated trace roots,
replay and traces after reopening persistence. Missing-native API creation is
rejected before creating a session. Existing tests retain stale-action rejection,
legacy replay, provider budgets/deadlines, trace schema and exporter checks.

Semantic privacy regressions hold public facts fixed while changing private
configuration/spectator fields, then compare model messages, tool results and
local/exported traces. New tests additionally cover private personality changes,
per-seat RNG independence, native observation sanitation and memory reset.
Neither hero prompts nor hero traces receive opponent personality values, policy
seeds, source code or native private requests. Trusted Python extensions remain
trusted backend code, not an OS sandbox. Public action inference is intentionally
permitted, and seed-only holdouts do not establish generalization to unknown bots.

## Recorded games and public examples

The recorded evaluation set completed **20/20 tournaments**, **504 hands** and
**1,964 actions**, including **264 hero decisions** and **1,700 real native
opponent decisions**. All **10 repeat pairs** matched outcome hashes. Every
recorded chip-conservation check passed; transitions used observed legal menus.

| Set | Starting stack / hands per level | Attempts | Hands | Actions | Native decisions |
| --- | --- | --- | --- | --- | --- |
| native-set-a | 10 BB / 2 | 8 | 114 | 350 | 308 |
| native-set-b | 10 BB / 2 | 8 | 120 | 362 | 320 |
| native-standard | 50 BB / 8 | 4 | 270 | 1,252 | 1,072 |

From `apps/api`, reproduction commands are:

```sh
LANGSMITH_TRACING=false LANGCHAIN_TRACING_V2=false .venv/bin/python -m wtr.evaluation \
  --opponents pokerth --tuning-seeds 1,7 --held-out-seeds 101,107 --repeats 2 \
  --opponent-seed 43 --personality-seed 44 --output data/stage2a/native-set-a
LANGSMITH_TRACING=false LANGCHAIN_TRACING_V2=false .venv/bin/python -m wtr.evaluation \
  --opponents pokerth --tuning-seeds 1,7 --held-out-seeds 101,107 --repeats 2 \
  --opponent-seed 91 --personality-seed 100 --output data/stage2a/native-set-b
LANGSMITH_TRACING=false LANGCHAIN_TRACING_V2=false .venv/bin/python -m wtr.evaluation \
  --opponents pokerth --tuning-seeds 42 --held-out-seeds 101 --repeats 2 \
  --stack-bb 50 --hands-per-level 8 --opponent-seed 43 --personality-seed 44 \
  --output data/stage2a/native-standard
```

Use new output directories when repeating an existing run. These built-in hero
policies do not call providers. Repeats are not independent samples. The sets
cover five distinct deck seeds and two opponent/assignment seed pairs, not
independently held-out policy families.

[Smoke evidence](review/stage-2a-smoke.json) retains configurations, outcome hashes,
source hashes, compiler provenance and counts. Successful smoke runs were recorded
on `4773341`; the later runner change adds setup/failure guidance only. Full raw
controller reports remain in ignored `apps/api/data/stage2a/`. From the root,
`python3 scripts/stage2a_report.py` extracts the compact evidence and
[public hand records](review/stage-2a-hands.md), with structured counterparts in
[stage-2a-hands.json](review/stage-2a-hands.json). The standard-depth example shows
multiway postflop action continuing after hero folds. None of these records
asserts strategic quality or solver agreement.

## Application demonstration

For a local demonstration without paid calls, from `apps/api`:

```sh
DATABASE_URL=sqlite:///data/stage2a/demo.sqlite CONTROL_TOKEN=stage2a-local \
  ALLOWED_ORIGINS=http://127.0.0.1:5175,http://localhost:5175 PYTHONPATH=. \
  .venv/bin/python tests/stage2a_preview.py
```

In a second terminal from the root:

```sh
VITE_API_URL=http://127.0.0.1:8012 npm run dev -w apps/web -- --port 5175 --strictPort
```

Open `http://127.0.0.1:5175`, enter the local test token in Connections, create a
PokerTH table, select the hero mode and press Run table. The preview bootstrap
forces mocked OpenRouter responses and disables external tracing before imports.
It returns check/call on odd hands and an intentional 503 on even hands to exercise
labeled fallback. The native opponents are real. This bootstrap is never imported
by production. Normal `uvicorn wtr.main:app` retains the configured live OpenRouter
route; no live provider call was made for this delivery.

Browser QA created two 20 BB tournaments with two hands per blind level:

- Heuristic hero: finished in 20 hands, 12 hero decisions and 12 saved traces.
- Mock provider hero: finished in 13 hands, 13 hero decisions, 10 successful mocked
  model calls and three intentional model errors with labeled heuristic fallback.

Both retained 1,200 chips and 100 prize units. The browser inspected native public
history, completed provider and fallback spans, replay, session switching and
saved sessions/traces after a real API restart. Desktop 1440x1000 and narrow
390x844 checks showed no horizontal overflow. Browser console had no errors after
restart. [Browser evidence](review/stage-2a-browser.json) records the controller
configuration and counts. Screenshots are in [docs/qa/stage-2a](qa/stage-2a/):
setup, finished table, provider trace, fallback trace, narrow replay and restarted
library. These two browser games and the worker acceptance tests are separate
from the 20-game evaluation set; test reruns are not extra independent evidence.

## Remaining limits

PokerTH is a heuristic opponent engine, not a GTO or ICM solver, and its human
realism is unverified. Native sampling, public-statistic definitions and discrete
sizing differ from desktop PokerTH. Hero position remains fixed at seat 0.
The hero graph is still the existing preparation graph with one optional model
call; new strategy, a model-directed tool loop and solver access remain Stage 2B.
Hosted OpenRouter, LangSmith and Supabase are unverified. The PostgreSQL test was
not rerun. Restart preserves replay and traces but does not resume engine state.
