import { useState } from "react";
import { HeroControl } from "../workspace/HeroControl";
import { ThemeSwitch } from "../theme";
import { CreateDialog } from "../workspace/Dialogs";
import {
  DecisionPanel,
  History,
  PokerTable,
  PublicChat,
  Standings,
} from "../workspace/Panels";
import { seatDefaults } from "../workspace/data";
import type { Decision, ServerConfig, Table } from "../types";
import type { TraceRecord } from "../trace/types";
import TraceView from "../trace/TraceView";
import sharedTrace from "../../../../contracts/trace-v1.example.json";

// Explicit synthetic presentation data. Imported exclusively by a DEV-gated entry.
const cards = [
  ["As", "Js"],
  ["8h", "8d"],
  ["Kh", "Qh"],
  ["Tc", "9c"],
  ["5s", "5h"],
  ["Ad", "6d"],
];
const actions = ["check", "check", "raise:40", "call", "fold", "call"];
const decisions = Object.fromEntries(
  cards.map((hole, seat) => [
    String(seat),
    {
      player: seat,
      chat_sequence: 2,
      action: actions[seat],
      source: "fixture",
      model: "fixture/model",
      summary: `Synthetic decision for Player ${seat + 1}. This preview is not a measured run.`,
      uncertainty: "No strategy was evaluated in this development fixture.",
      evidence_ids: [],
      evidence: [],
      observation: {
        player: seat,
        hole,
        board: ["Ks", "7s", "2d"],
        hand: 3,
        state_version: 12,
      },
      latency_ms: 1260,
      state_version: 12,
      hand: 3,
      street: "flop",
      event_id: `fixture-event-${seat}`,
      fallback: null,
      calls: 1,
      usage: {},
      trace_id: `10000000-0000-4000-8000-00000000000${seat}`,
    } satisfies Decision,
  ]),
);
const fixture: Table = {
  id: "workspace-fixture-only",
  config: {
    name: "Six-player preview",
    seed: 0,
    stack_bb: 50,
    hands_per_level: 8,
    payouts: "70/30",
    mode: "openrouter",
    opponents: "llm",
    model: "fixture/model",
    pace: 1.2,
    player_count: 6,
    hero_control: "human",
    hero_seat: 0,
    seat_configs: seatDefaults(6),
  },
  status: "paused",
  phase: "playing",
  version: 12,
  hand: 3,
  street: "flop",
  level: 1,
  small_blind: 5,
  big_blind: 10,
  hands_to_level: 5,
  button: 3,
  actor: 0,
  hero_turn: {
    player: 0,
    state_version: 12,
    chat_sequence: 2,
    turn_token: "synthetic-turn-12",
    observation: {
      legal: [
        { key: "check", kind: "check", amount: 0 },
        { key: "raise:40", kind: "raise", amount: 40 },
        { key: "fold", kind: "fold", amount: 0 },
      ],
    },
  },
  players: cards.map((hole, seat) => ({
    seat,
    name: `Player ${seat + 1}`,
    stack: [560, 420, 610, 410, 500, 500][seat],
    bet: 0,
    cards: hole,
    active: true,
    eliminated: false,
    position: ["SB", "BB", "UTG", "HJ", "CO", "BTN"][seat],
    last_action: seat < 2 ? "check" : null,
    stats: { actions: 0, raises: 0, calls: 0, folds: 0 },
    prize: 0,
    place: null,
  })),
  board: ["Ks", "7s", "2d"],
  pot: 80,
  remaining: 6,
  history: [
    {
      id: "preview-event-1",
      hand: 3,
      street: "flop",
      text: "Player 1 checks.",
      player: 0,
      action: "check",
      amount: 0,
    },
    {
      id: "preview-event-2",
      hand: 3,
      street: "flop",
      text: "Player 2 checks.",
      player: 1,
      action: "check",
      amount: 0,
    },
  ],
  decision: decisions["0"],
  decisions_by_player: decisions,
  series: [],
  icm: {},
  icm_basis: "Not recorded",
  agent_decisions: 1,
  chat_sequence: 2,
  chat: [
    {
      id: "preview-message-1",
      sequence: 1,
      player: 0,
      hand: 3,
      state_version: 10,
      text: "Let's see the next card.",
    },
    {
      id: "preview-message-2",
      sequence: 2,
      player: 1,
      hand: 3,
      state_version: 12,
      text: "I'm happy to keep this pot small.",
    },
  ],
};
const server: ServerConfig = {
  openrouter_configured: true,
  default_model: "",
  tracing: false,
  storage: "fixture",
  max_tables: 2,
  agent_call_limit: 100,
  capabilities: {
    llm_tables: true,
    public_chat: true,
    per_seat_traces: true,
    manual_hero: true,
  },
};
function traceFor(seat: number): TraceRecord {
  const trace = structuredClone(sharedTrace) as TraceRecord;
  trace.trace_id = decisions[String(seat)].trace_id!;
  trace.table_id = fixture.id;
  trace.metadata = { synthetic_fixture: true, player: seat, chat_sequence: 2 };
  trace.spans = trace.spans.map((span) => ({
    ...span,
    span_id: span.span_id.replace(/^00000000/, `2000000${seat}`),
    parent_span_id:
      span.parent_span_id?.replace(/^00000000/, `2000000${seat}`) ?? null,
    outputs:
      span.name === "decision" ? { action: actions[seat] } : span.outputs,
    inputs:
      span.name === "assess_hand"
        ? decisions[String(seat)].observation
        : span.inputs,
  }));
  return trace;
}
export default function WorkspacePreview() {
  const [seat, setSeat] = useState(0),
    [reveal, setReveal] = useState(false),
    [traceOpen, setTraceOpen] = useState(false),
    [configure, setConfigure] = useState(false);
  const [replay, setReplay] = useState(false);
  const [inspection, setInspection] = useState(false);
  const [live, setLive] = useState(fixture);
  const table = replay
    ? {
        ...live,
        version: 10,
        chat_sequence: 1,
        history: fixture.history.slice(0, 1),
        decisions_by_player: {},
        decision: null,
      }
    : live;
  return (
    <div className="terminal-app">
      <header className="app-header">
        <a className="wordmark" href="/">
          <span className="pixel-mark">♠</span>
          <strong>
            what's their range<span>?</span>
          </strong>
        </a>
        <div className="header-tools">
          <ThemeSwitch />
          <a href="/" className="text-button">
            Live tables
          </a>
        </div>
      </header>
      <main>
        <p className="notice">
          Development fixture only. Synthetic seats, messages and traces. No
          gameplay or provider calls.
        </p>
        <div className="workspace-heading">
          <div>
            <span className="kicker">UI preview</span>
            <h1>
              {fixture.config.name}
              <span className="state-label">
                {replay ? "Replay fixture" : "Fixture"}
              </span>
            </h1>
          </div>
          <div className="table-controls">
            <button className="button" onClick={() => setConfigure(true)}>
              Configure seats
            </button>
            <button className="button" onClick={() => setReplay(!replay)}>
              {replay ? "Latest fixture" : "Earlier snapshot"}
            </button>
          </div>
        </div>
        <div className="view-choice">
          <div className="segmented">
            <button
              aria-pressed={!inspection}
              onClick={() => {
                setInspection(false);
                setReveal(false);
                setTraceOpen(false);
              }}
            >
              Play
            </button>
            <button
              aria-pressed={inspection}
              onClick={() => setInspection(true)}
            >
              Spectator inspection
            </button>
          </div>
          {inspection && (
            <span className="muted">Private spectator records</span>
          )}
        </div>
        <div className="main-grid">
          <PokerTable
            table={table}
            selected={seat}
            onSelect={setSeat}
            inspection={inspection}
            reveal={reveal}
            setReveal={setReveal}
          />
          <PublicChat table={table} server={server} replay={replay} />
        </div>
        {inspection && traceOpen && (
          <section className="panel trace-workspace">
            <header className="panel-heading">
              <h2>Synthetic trace · Player {seat + 1}</h2>
              <button
                className="text-button"
                onClick={() => setTraceOpen(false)}
              >
                Close trace
              </button>
            </header>
            <TraceView key={seat} trace={traceFor(seat)} />
          </section>
        )}
        <div className="lower-grid">
          {!inspection ? (
            <HeroControl
              table={table}
              server={server}
              connection="live"
              replay={replay}
              onRefresh={async () => {}}
              onAction={async (payload) => {
                const version = live.version + 1;
                const record = {
                  ...decisions["0"],
                  action: payload.action,
                  source: "human",
                  model: null,
                  summary: "",
                  uncertainty: "",
                  trace_id: null,
                  state_version: version,
                  calls: 0,
                  latency_ms: 0,
                };
                setLive({
                  ...live,
                  version,
                  hero_turn: null,
                  decision: record,
                  decisions_by_player: {
                    ...live.decisions_by_player,
                    "0": record,
                  },
                  chat_sequence:
                    live.chat_sequence! + (payload.public_message ? 1 : 0),
                  chat: [
                    ...live.chat!,
                    ...(payload.public_message
                      ? [
                          {
                            id: `manual-fixture-message-${version}`,
                            player: 0,
                            sequence: live.chat_sequence! + 1,
                            state_version: version,
                            hand: live.hand,
                            text: payload.public_message,
                          },
                        ]
                      : []),
                  ],
                });
              }}
              onControl={async (payload) => {
                const version = live.version + 1;
                setLive({
                  ...live,
                  version,
                  config: {
                    ...live.config,
                    hero_control: payload.hero_control,
                  },
                  hero_turn:
                    payload.hero_control === "human"
                      ? {
                          ...fixture.hero_turn!,
                          state_version: version,
                          turn_token: `synthetic-turn-${version}`,
                        }
                      : null,
                });
              }}
            />
          ) : (
            <DecisionPanel
              key={seat}
              table={table}
              seat={seat}
              server={server}
              onTrace={() => setTraceOpen(!traceOpen)}
            />
          )}
          <History
            table={table}
            replay={replay}
            historyBusy={false}
            onReplay={() => setReplay(!replay)}
          />
          <Standings table={table} selected={seat} onSelect={setSeat} />
        </div>
        <footer>
          <span>Development preview</span>
          <span>Shared LLM table interface v1</span>
        </footer>
        {configure && (
          <CreateDialog
            server={server}
            count={0}
            onClose={() => setConfigure(false)}
            onCreate={async () => {
              throw new Error("Preview only. No table was created.");
            }}
          />
        )}
      </main>
    </div>
  );
}
