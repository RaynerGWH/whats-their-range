import React, { useEffect, useRef, useState } from "react";
import {
  Activity,
  ArrowDownLeft,
  ArrowUpRight,
  BrainCircuit,
  ChevronRight,
  CircleHelp,
  Clock3,
  Eye,
  EyeOff,
  Layers3,
  Pause,
  Play,
  Plus,
  Radio,
  RotateCcw,
  Settings2,
  ShieldCheck,
  SkipForward,
  Square,
  Target,
  WifiOff,
  X,
} from "lucide-react";
import type { Config, Decision, Player, ServerConfig, Table } from "./types";

import { API, request } from "./api";
import TraceBrowser from "./trace/TraceBrowser";

const terminal = (s: string) =>
  ["finished", "stopped", "interrupted", "error"].includes(s);
const fmt = (n = 0) => new Intl.NumberFormat("en").format(n);
const pct = (n = 0) => `${Math.round(n * 100)}%`;
const label = (s: string) =>
  s
    .replace("raise:", "Raise to ")
    .replace(/^check$/, "Check")
    .replace(/^call$/, "Call")
    .replace(/^fold$/, "Fold");
const defaultConfig: Config = {
  name: "Table 1",
  seed: 42,
  stack_bb: 50,
  hands_per_level: 8,
  payouts: "70/30",
  mode: "heuristic",
  opponents: "pokerth",
  model: "",
  pace: 1.2,
};

function Card({
  value,
  hidden = false,
  small = false,
}: {
  value?: string;
  hidden?: boolean;
  small?: boolean;
}) {
  const suits: Record<string, string> = { s: "♠", h: "♥", d: "♦", c: "♣" };
  if (hidden)
    return (
      <div
        className={`card back ${small ? "small" : ""}`}
        aria-label="Hidden card"
      >
        <span>✳</span>
      </div>
    );
  if (!value)
    return (
      <div
        className={`card ghost ${small ? "small" : ""}`}
        aria-label="Undealt card"
      >
        ·
      </div>
    );
  return (
    <div
      className={`card ${"hd".includes(value[1]) ? "red" : ""} ${small ? "small" : ""}`}
      aria-label={value}
    >
      <b>{value[0] === "T" ? "10" : value[0]}</b>
      <span>{suits[value[1]]}</span>
    </div>
  );
}

function Seat({
  p,
  actor,
  button,
  reveal,
}: {
  p: Player;
  actor: number | null;
  button: number;
  reveal: boolean;
}) {
  return (
    <div
      className={`seat seat-${p.seat} ${actor === p.seat ? "acting" : ""} ${p.eliminated ? "eliminated" : ""} ${p.seat === 0 ? "hero-seat" : ""}`}
    >
      <div className="seat-cards">
        {p.cards.map((c, i) => (
          <Card key={i} value={c} small hidden={p.seat !== 0 && !reveal} />
        ))}
        {button === p.seat && (
          <span className="dealer" title="Dealer button">
            D
          </span>
        )}
      </div>
      <div className="seat-body">
        <span className={`avatar avatar-${p.seat}`}>
          {p.seat === 0 ? <BrainCircuit size={17} /> : p.name.slice(0, 1)}
        </span>
        <div className="seat-info">
          <strong>{p.name}</strong>
          <span>{p.eliminated ? `Out · #${p.place}` : fmt(p.stack)}</span>
        </div>
        <small className="position">{p.position}</small>
      </div>
      <div className="seat-action">
        {actor === p.seat ? (
          <>
            <i /> To act
          </>
        ) : p.last_action ? (
          label(p.last_action)
        ) : p.eliminated ? (
          "Eliminated"
        ) : p.seat === 0 ? (
          "OUR AGENT"
        ) : (
          "SIMULATED"
        )}
      </div>
      {p.bet > 0 && (
        <div className="bet">
          <i className="chip" />
          {fmt(p.bet)}
        </div>
      )}
    </div>
  );
}

function Chart({ data }: { data: { hand: number; stack: number }[] }) {
  const values = data.length ? data : [{ hand: 0, stack: 0 }];
  const max = Math.max(...values.map((v) => v.stack), 1) * 1.1;
  const points = values
    .map(
      (p, i) =>
        `${12 + (i / Math.max(1, values.length - 1)) * 516},${105 - (p.stack / max) * 86}`,
    )
    .join(" ");
  return (
    <svg
      className="chart"
      viewBox="0 0 540 130"
      role="img"
      aria-label="Agent chip stack after each completed hand"
    >
      <defs>
        <linearGradient id="fill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#55957d" stopOpacity=".22" />
          <stop offset="100%" stopColor="#55957d" stopOpacity="0" />
        </linearGradient>
      </defs>
      {[25, 65, 105].map((y) => (
        <line
          key={y}
          x1="12"
          x2="528"
          y1={y}
          y2={y}
          stroke="#e7e9e3"
          strokeDasharray="3 4"
        />
      ))}
      <polygon
        points={`12,105 ${points} ${values.length > 1 ? "528" : "12"},105`}
        fill="url(#fill)"
      />
      <polyline
        points={points}
        fill="none"
        stroke="#487b65"
        strokeWidth="2.5"
        strokeLinejoin="round"
      />
      {values.length === 1 && (
        <circle
          cx="12"
          cy={105 - (values[0].stack / max) * 86}
          r="3"
          fill="#487b65"
        />
      )}
      <text x="12" y="126">
        Hand {values[0].hand}
      </text>
      <text x="528" y="126" textAnchor="end">
        {values.at(-1)?.hand}
      </text>
    </svg>
  );
}

function Inspector({
  d,
  tab,
  setTab,
  thinking,
}: {
  d: Decision | null;
  tab: string;
  setTab: (s: string) => void;
  thinking: boolean;
}) {
  return (
    <aside className={`inspector panel ${tab === "Trace" ? "trace-tab" : ""}`}>
      <div className="panel-title">
        <div>
          <BrainCircuit size={17} />
          <h2>Agent decision</h2>
        </div>
        <span className={`tiny-badge ${thinking ? "active-badge" : ""}`}>
          {thinking ? "ANALYSING" : "AGENT VIEW"}
        </span>
      </div>
      <div className="tabs">
        {["Overview", "Evidence", "Trace"].map((t) => (
          <button
            key={t}
            className={tab === t ? "selected" : ""}
            onClick={() => setTab(t)}
          >
            {t}
          </button>
        ))}
      </div>
      {tab === "Trace" ? (
        <div className="inspector-content">
          <p className="subtle">
            {d?.trace_id
              ? `Decision at state ${d.state_version}.`
              : "No trace linked to this decision."}
          </p>
          <a className="button secondary" href="#trace-explorer">
            Open trace explorer <ChevronRight size={14} />
          </a>
        </div>
      ) : !d ? (
        <div className="inspector-empty">
          <p>No agent decisions yet.</p>
        </div>
      ) : (
        <>
          <div className="decision-meta">
            <span>
              HAND {d.hand} · {d.street.toUpperCase()}
            </span>
            <span>
              <Clock3 size={12} />
              {(d.latency_ms / 1000).toFixed(2)}s
            </span>
          </div>
          {tab === "Overview" && (
            <div className="inspector-content" key={d.event_id}>
              <div className="decision-action">
                <span className="eyebrow">EXECUTED ACTION</span>
                <h3>{label(d.action)}</h3>
                <span className="source">
                  <i />
                  {d.source === "openrouter" ? d.model : "Heuristic baseline"}
                </span>
              </div>
              {d.fallback && (
                <div className="notice">Fallback: {d.fallback}</div>
              )}
              <div className="analysis-block">
                <span className="section-kicker">
                  <Target size={14} /> HAND ASSESSMENT
                </span>
                <div className="meter-label">
                  <span>Equity vs random hands</span>
                  <strong>{pct(d.metrics.equity)}</strong>
                </div>
                <div className="meter">
                  <i style={{ width: pct(d.metrics.equity) }} />
                </div>
                <small>
                  {d.metrics.samples} samples · SE ±
                  {(d.metrics.standard_error * 100).toFixed(1)} percentage
                  points
                </small>
                <div className="metric-pair">
                  <span>
                    Pot-odds reference{" "}
                    <b>{pct(d.metrics.pot_odds_reference)}</b>
                  </span>
                  <span>
                    Hand-start ICM{" "}
                    <b>{d.metrics.icm_at_hand_start.toFixed(1)} units</b>
                  </span>
                </div>
              </div>
              <div className="analysis-block">
                <span className="section-kicker">
                  <BrainCircuit size={14} /> DECISION SUMMARY
                </span>
                <p>{d.summary}</p>
              </div>
              <div className="uncertainty">
                <CircleHelp size={16} />
                <div>
                  <strong>Uncertainty</strong>
                  <p>{d.uncertainty}</p>
                </div>
              </div>
            </div>
          )}
          {tab === "Evidence" && (
            <div className="inspector-content">
              <p className="subtle">
                Observed actions at this decision. Counts alone do not establish
                a leak.
              </p>
              {d.evidence.map((p) => (
                <div className="evidence" key={p.seat}>
                  <div>
                    <strong>{p.name}</strong>
                    <span>{p.actions} actions</span>
                  </div>
                  <div className="counts">
                    <span>
                      Raise <b>{p.raises}</b>
                    </span>
                    <span>
                      Call <b>{p.calls}</b>
                    </span>
                    <span>
                      Fold <b>{p.folds}</b>
                    </span>
                  </div>
                  {p.recent_actions.slice(-2).map((e) => (
                    <p
                      key={e.id}
                      className={d.evidence_ids.includes(e.id) ? "cited" : ""}
                    >
                      {e.text}
                      <small>
                        H{e.hand} · {e.street}
                      </small>
                    </p>
                  ))}
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </aside>
  );
}

export default function App() {
  const [tables, setTables] = useState<Table[]>([]),
    [selected, setSelected] = useState("");
  const [server, setServer] = useState<ServerConfig | null>(null),
    [connection, setConnection] = useState("connecting");
  const [error, setError] = useState(""),
    [modal, setModal] = useState(false),
    [settings, setSettings] = useState(false);
  const [form, setForm] = useState<Config>(defaultConfig),
    [busy, setBusy] = useState(false),
    [reveal, setReveal] = useState(false);
  const [tab, setTab] = useState("Overview"),
    [replay, setReplay] = useState<Table | null>(null),
    [frames, setFrames] = useState<Table[]>([]);
  const [token, setToken] = useState(
    () => sessionStorage.getItem("wtr-token") || "",
  );
  const [tokenDraft, setTokenDraft] = useState(token),
    [historyBusy, setHistoryBusy] = useState(false);
  const [section, setSection] = useState("live");
  const scrollRef = useRef<HTMLDivElement>(null);
  const api = (path: string, body?: unknown) => request<any>(path, token, body);
  useEffect(() => {
    let disposed = false,
      socket: WebSocket | undefined,
      timer: ReturnType<typeof setTimeout>;
    const connect = async () => {
      try {
        const [conf, initial] = await Promise.all([
          api("/config"),
          api("/tables"),
        ]);
        if (disposed) return;
        setServer(conf);
        setTables(initial);
        setSelected((old) => old || initial.at(-1)?.id || "");
        setError("");
        const origin = API || window.location.origin;
        socket = new WebSocket(`${origin.replace(/^http/, "ws")}/api/live`);
        socket.onopen = () => {
          socket?.send(JSON.stringify({ token }));
          setConnection("live");
        };
        socket.onmessage = (e) => {
          const msg = JSON.parse(e.data);
          if (msg.type === "tables") {
            setTables(msg.tables);
            setSelected((old) => old || msg.tables.at(-1)?.id || "");
          }
        };
        socket.onclose = () => {
          if (!disposed) {
            setConnection("reconnecting");
            timer = setTimeout(connect, 2000);
          }
        };
        socket.onerror = () => socket?.close();
      } catch (e) {
        if (!disposed) {
          setConnection("offline");
          setError((e as Error).message);
          timer = setTimeout(connect, 4000);
        }
      }
    };
    connect();
    return () => {
      disposed = true;
      clearTimeout(timer);
      socket?.close();
    };
  }, [token]);
  const live = tables.find((t) => t.id === selected);
  const table = replay || live;
  const ready = !!table?.players;
  const active = tables.filter((t) => !terminal(t.status));
  const choose = (id: string) => {
    setSelected(id);
    setReplay(null);
    setFrames([]);
    setSection("live");
  };
  const control = async (action: string, pace?: number) => {
    if (!live) return;
    try {
      await api(`/tables/${live.id}/control`, { action, pace });
      setError("");
    } catch (e) {
      setError((e as Error).message);
    }
  };
  const create = async () => {
    setBusy(true);
    try {
      const result = await api("/tables", form);
      choose(result.id);
      setModal(false);
      setError("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const loadHistory = async () => {
    if (!live) return;
    setHistoryBusy(true);
    try {
      const data: Table[] = await api(`/tables/${live.id}/history`);
      setFrames(data);
      if (data.length) setReplay(data.at(-1)!);
      setSection("live");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setHistoryBusy(false);
    }
  };
  const loadOlder = async () => {
    if (!live || !frames.length) return;
    setHistoryBusy(true);
    try {
      const data: Table[] = await api(
        `/tables/${live.id}/history?before=${frames[0].version}`,
      );
      setFrames((old) => [...data, ...old]);
      if (!data.length)
        setError("You have reached the beginning of this session.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setHistoryBusy(false);
    }
  };
  const openCreate = () => {
    setForm({
      ...defaultConfig,
      seed: Math.floor(Math.random() * 100000),
      name: `Table ${tables.length + 1}`,
      model: server?.default_model || "",
    });
    setModal(true);
  };
  useEffect(() => {
    if (!replay)
      scrollRef.current?.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
          ? "instant"
          : "smooth",
      });
  }, [table?.version, replay]);
  useEffect(() => {
    const fn = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setModal(false);
        setSettings(false);
      }
    };
    window.addEventListener("keydown", fn);
    return () => window.removeEventListener("keydown", fn);
  }, []);
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a href="#" className="brand" aria-label="What's Their Range home">
          <span className="brand-icon">
            w<span>r</span>
            <i>?</i>
          </span>
          <span>
            what’s their
            <br />
            <b>range?</b>
          </span>
        </a>
        <div className="workspace-label">
          THE POKER AGENT LAB <span>v0.1</span>
        </div>
        <nav>
          <button
            className={section === "live" ? "nav-active" : ""}
            onClick={() => setSection("live")}
          >
            <Layers3 size={18} /> Live tables{" "}
            <span className="nav-count">{active.length}</span>
          </button>
          <button
            className={section === "sessions" ? "nav-active" : ""}
            onClick={() => setSection("sessions")}
          >
            <RotateCcw size={18} /> Session library
          </button>
          <button onClick={() => setSettings(true)}>
            <Settings2 size={18} /> Connections
          </button>
        </nav>
        <div className="sidebar-divider" />
        <div className="sidebar-heading">
          YOUR TABLES{" "}
          <button
            aria-label="New table"
            onClick={openCreate}
            disabled={active.length >= 2}
          >
            <Plus size={15} />
          </button>
        </div>
        <div className="table-list">
          {tables
            .filter((t) => !terminal(t.status))
            .map((t, i) => (
              <button
                key={t.id}
                className={selected === t.id ? "table-selected" : ""}
                onClick={() => choose(t.id)}
              >
                <span
                  className={`status-dot ${t.status === "running" ? "green" : ""}`}
                />
                <div>
                  <strong>Table {String(i + 1).padStart(2, "0")}</strong>
                  <small>
                    {t.hand
                      ? `Hand ${t.hand} · ${t.remaining} players`
                      : "Preparing table"}
                  </small>
                </div>
                <ChevronRight size={14} />
              </button>
            ))}
          {!active.length && (
            <p className="empty-small">No active tables yet.</p>
          )}
        </div>
        <div className="sidebar-bottom">
          <div className="connection">
            <i
              className={`status-dot ${connection === "live" ? "green" : ""}`}
            />
            {connection === "live"
              ? "Backend connected"
              : "Connecting to backend"}
            <span>{server?.storage || "..."}</span>
          </div>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <ChevronRight size={13} />
            <strong>
              {section === "live" ? "Live tables" : "Session library"}
            </strong>
          </div>
          <div className="topbar-right">
            <span>
              <Eye size={14} /> Spectator mode
            </span>
          </div>
        </header>
        <main>
          <div className="page-heading">
            <div>
              <h1>{section === "live" ? "Live tables" : "Sessions"}</h1>
            </div>
            <button
              className="button primary"
              disabled={!server || active.length >= 2}
              onClick={openCreate}
            >
              <Plus size={16} /> New table
            </button>
          </div>
          {error && (
            <div className="error-banner" role="alert">
              <CircleHelp size={16} />
              <span>{error}</span>
              <button onClick={() => setError("")} aria-label="Dismiss error">
                <X size={15} />
              </button>
              {connection !== "live" && (
                <button onClick={() => setSettings(true)}>Connections</button>
              )}
            </div>
          )}
          {table?.error && <div className="error-banner" role="alert">{table.error}</div>}
          {connection !== "live" && (
            <div className="offline-banner">
              <WifiOff size={14} />{" "}
              {connection === "offline"
                ? "Backend unavailable. Start the API or check Connections."
                : "Connecting to the live event stream..."}
            </div>
          )}
          {section === "sessions" ? (
            <div className="panel session-list">
              <div className="panel-title">
                <h2>Tournament sessions</h2>
                <span>{tables.length} saved</span>
              </div>
              {tables.length === 0 ? (
                <div className="empty-session">No saved sessions.</div>
              ) : (
                tables
                  .slice()
                  .reverse()
                  .map((t) => (
                    <button key={t.id} onClick={() => choose(t.id)}>
                      <span className="session-icon">
                        <Layers3 size={20} />
                      </span>
                      <div>
                        <strong>{t.config.name}</strong>
                        <small>
                          Seed {t.config.seed} · {t.config.mode} · {t.config.opponents === "pokerth" ? "PokerTH" : "Legacy"} · {t.hand || 0}{" "}
                          hands
                        </small>
                      </div>
                      <span className="tiny-badge">{t.status}</span>
                      <ChevronRight size={16} />
                    </button>
                  ))
              )}
            </div>
          ) : (
            <>
              <div className="live-layout">
                <div className="left-column">
                  <section className="table-panel panel">
                    <div className="table-toolbar">
                      <div>
                        <span
                          className={`status-dot ${live?.status === "running" ? "green" : ""}`}
                        />
                        <strong>
                          {table?.config.name || "No active table"}
                        </strong>
                        <span className="tiny-badge">
                          {replay
                            ? "REPLAY"
                            : live?.status?.toUpperCase() || "READY"}
                        </span>
                      </div>
                      <button
                        className="icon-button"
                        onClick={() => setReveal(!reveal)}
                        title={
                          reveal
                            ? "Hide opponent cards"
                            : "Reveal spectator cards"
                        }
                        aria-label={
                          reveal
                            ? "Hide opponent cards"
                            : "Reveal spectator cards"
                        }
                      >
                        {reveal ? <Eye size={17} /> : <EyeOff size={17} />}
                      </button>
                    </div>
                    <div className="table-subbar">
                      <span>
                        <Layers3 size={13} /> 6-MAX NLH · FREEZEOUT
                      </span>
                      <span>
                        {ready
                          ? `Level ${table.level} · ${fmt(table.small_blind)} / ${fmt(table.big_blind)}`
                          : "6 players"}
                      </span>
                    </div>
                    <div className="arena">
                      <div className="table-rail">
                        <div className="felt">
                          <div className="felt-mark">WHAT’S THEIR RANGE?</div>
                          <div className="community">
                            <div className="pot-label">
                              {ready && table.phase === "hand_complete"
                                ? "HAND COMPLETE"
                                : "TOTAL POT"}
                            </div>
                            <div className="pot-value">
                              {ready ? fmt(table.pot) : "0"} <span>chips</span>
                            </div>
                            <div className="board">
                              {Array.from({ length: 5 }, (_, i) => (
                                <Card
                                  key={i}
                                  value={ready ? table.board[i] : undefined}
                                />
                              ))}
                            </div>
                            <div className="street-label">
                              {ready
                                ? `HAND ${table.hand} / ${table.street.toUpperCase()}`
                                : "WAITING FOR THE FIRST HAND"}
                            </div>
                          </div>
                        </div>
                      </div>
                      {ready ? (
                        table.players.map((p) => (
                          <Seat
                            key={p.seat}
                            p={p}
                            actor={table.actor}
                            button={table.button}
                            reveal={reveal}
                          />
                        ))
                      ) : (
                        <div className="start-overlay">
                          <button
                            className="button primary"
                            onClick={openCreate}
                            disabled={!server}
                          >
                            <Play size={15} /> Set up a tournament
                          </button>
                        </div>
                      )}
                      {ready && table.status === "finished" && (
                        <div className="winner-ribbon">
                          {table.players.find((p) => p.place === 1)?.name} wins
                          the tournament
                        </div>
                      )}
                    </div>
                    <div className="table-controls">
                      <div>
                        {replay ? (
                          <button
                            className="button primary"
                            onClick={() => setReplay(null)}
                          >
                            <Radio size={14} /> Return to live
                          </button>
                        ) : (
                          <>
                            <button
                              className="button primary"
                              disabled={
                                !ready ||
                                terminal(live?.status || "") ||
                                connection !== "live"
                              }
                              onClick={() =>
                                control(
                                  live?.status === "running"
                                    ? "pause"
                                    : "resume",
                                )
                              }
                            >
                              {live?.status === "running" ? (
                                <Pause size={14} />
                              ) : (
                                <Play size={14} />
                              )}{" "}
                              {live?.status === "running"
                                ? "Pause"
                                : "Run table"}
                            </button>
                            <button
                              className="button secondary"
                              disabled={
                                !ready ||
                                live?.status !== "paused" ||
                                connection !== "live"
                              }
                              onClick={() => control("step")}
                              title="Advance one action"
                            >
                              <SkipForward size={15} /> Step
                            </button>
                          </>
                        )}
                      </div>
                      <div>
                        <label className="speed-control">
                          Pace{" "}
                          <select
                            aria-label="Table pace"
                            value={live?.config.pace || 1.2}
                            disabled={
                              !ready || terminal(live?.status || "") || !!replay
                            }
                            onChange={(e) =>
                              control("speed", Number(e.target.value))
                            }
                          >
                            <option value={2.4}>0.5×</option>
                            <option value={1.2}>1×</option>
                            <option value={0.3}>4×</option>
                            <option value={0.05}>Fast</option>
                          </select>
                        </label>
                        <button
                          className="icon-button"
                          disabled={
                            !ready || terminal(live?.status || "") || !!replay
                          }
                          onClick={() => control("stop")}
                          title="End and archive session"
                          aria-label="End session"
                        >
                          <Square size={14} />
                        </button>
                      </div>
                    </div>
                  </section>
                  <div className="stats-grid">
                    <div className="stat-card">
                      <span>
                        <Activity size={14} /> AGENT STACK
                      </span>
                      <strong>
                        {ready ? fmt(table.players[0].stack) : "0"}
                        <small> chips</small>
                      </strong>
                      <p>
                        {ready
                          ? `${(table.players[0].stack / table.big_blind).toFixed(1)} BB at current level`
                          : "Waiting for a session"}
                      </p>
                    </div>
                    <div className="stat-card">
                      <span>
                        <Target size={14} /> PRIZE EQUITY
                      </span>
                      <strong>
                        {ready ? table.icm["0"].toFixed(1) : "0.0"}
                        <small> / 100</small>
                      </strong>
                      <p>
                        {ready
                          ? `ICM · ${table.icm_basis.toLowerCase()}`
                          : "Descriptive ICM calculation"}
                      </p>
                    </div>
                    <div className="stat-card">
                      <span>
                        <BrainCircuit size={14} /> DECISIONS
                      </span>
                      <strong>
                        {ready ? table.agent_decisions : 0}
                        <small> made</small>
                      </strong>
                      <p>
                        {table?.config.mode === "openrouter"
                          ? "OpenRouter"
                          : "Heuristic baseline"}
                      </p>
                    </div>
                  </div>
                  <section className="panel progress-panel">
                    <div className="panel-title">
                      <div>
                        <Activity size={16} />
                        <h2>Agent stack</h2>
                      </div>
                      <span className="subtle">Chips by hand</span>
                    </div>
                    <Chart data={ready ? table.series : []} />
                  </section>
                </div>
                <Inspector
                  d={ready ? table.decision : null}
                  tab={tab}
                  setTab={setTab}
                  thinking={table?.phase === "thinking"}
                />
              </div>
              {tab === "Trace" && table && (
                <TraceBrowser
                  key={`${table.id}:${replay ? replay.version : "live"}:${token}`}
                  tableId={table.id}
                  hand={table.hand}
                  decisionTraceId={table.decision?.trace_id}
                  decisionHand={table.decision?.hand}
                  activeTraceId={replay ? null : table.active_trace_id}
                  token={token}
                  connection={connection}
                />
              )}
              {tab === "Trace" && !table && (
                <p className="trace-message" id="trace-explorer">
                  Select a table to inspect traces.
                </p>
              )}
              <section className="panel activity-panel">
                <div className="panel-title">
                  <div>
                    <Radio size={16} />
                    <h2>Table activity</h2>
                    <span className="tiny-badge">
                      {replay ? "HISTORICAL" : "LIVE FEED"}
                    </span>
                  </div>
                  <button
                    className="text-button"
                    disabled={!ready || historyBusy}
                    onClick={loadHistory}
                  >
                    <RotateCcw size={14} />
                    {historyBusy ? "Loading..." : "Open replay"}
                  </button>
                </div>
                {replay && (
                  <div className="replay-bar">
                    <button
                      className="text-button"
                      onClick={loadOlder}
                      disabled={historyBusy}
                    >
                      Load older
                    </button>
                    <input
                      aria-label="Replay position"
                      type="range"
                      min="0"
                      max={Math.max(0, frames.length - 1)}
                      value={Math.max(
                        0,
                        frames.findIndex((f) => f.version === replay.version),
                      )}
                      onChange={(e) =>
                        setReplay(frames[Number(e.target.value)])
                      }
                    />
                    <span>
                      Event {replay.version} · Hand {replay.hand}
                    </span>
                  </div>
                )}
                <div className="activity-rows" ref={scrollRef}>
                  {ready && table.history.length ? (
                    table.history.slice(-35).map((e) => (
                      <div
                        className={`activity-row ${e.player === 0 ? "agent-row" : ""}`}
                        key={e.id}
                      >
                        <span className="hand-tag">H{e.hand}</span>
                        <span className="street-tag">{e.street}</span>
                        <span className="event-icon">
                          {e.action?.startsWith("raise") ? (
                            <ArrowUpRight size={14} />
                          ) : e.action === "fold" ? (
                            <ArrowDownLeft size={14} />
                          ) : (
                            <span>·</span>
                          )}
                        </span>
                        <span>{e.text}</span>
                        {e.player === 0 && (
                          <span className="tiny-badge">AGENT</span>
                        )}
                        <code>{e.id.split(":").at(-1)}</code>
                      </div>
                    ))
                  ) : (
                    <div className="empty-activity">No actions yet.</div>
                  )}
                </div>
              </section>
            </>
          )}
          <footer>
            <span>Simulated chips</span>
            <span>
              {server?.tracing ? "LangSmith enabled" : "Local traces"}
            </span>
          </footer>
        </main>
      </div>
      {modal && (
        <div className="modal-scrim" onClick={() => setModal(false)}>
          <section
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="modal-title"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="modal-close icon-button"
              onClick={() => setModal(false)}
              aria-label="Close"
            >
              <X size={20} />
            </button>
            <span className="modal-symbol">
              <Layers3 size={24} />
            </span>
            <h2 id="modal-title">New tournament</h2>
            <p>Six players. Starts paused.</p>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                create();
              }}
            >
              <label>
                Session name
                <input
                  autoFocus
                  value={form.name}
                  maxLength={50}
                  required
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                />
              </label>
              <div className="form-grid">
                <label>
                  Starting stack
                  <select
                    value={form.stack_bb}
                    onChange={(e) =>
                      setForm({ ...form, stack_bb: Number(e.target.value) })
                    }
                  >
                    <option value={20}>20 BB · Short stack</option>
                    <option value={50}>50 BB · Standard</option>
                    <option value={100}>100 BB · Deep stack</option>
                  </select>
                </label>
                <label>
                  Payout structure
                  <select
                    value={form.payouts}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        payouts: e.target.value as Config["payouts"],
                      })
                    }
                  >
                    <option value="70/30">Top two · 70 / 30</option>
                    <option value="winner-take-all">Winner takes all</option>
                  </select>
                </label>
                <label>
                  Hands per blind level
                  <input
                    type="number"
                    min={2}
                    max={100}
                    value={form.hands_per_level}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        hands_per_level: Number(e.target.value),
                      })
                    }
                  />
                </label>
                <label>
                  Deck seed
                  <input
                    type="number"
                    min={0}
                    max={2147483647}
                    value={form.seed}
                    onChange={(e) =>
                      setForm({ ...form, seed: Number(e.target.value) })
                    }
                  />
                </label>
              </div>
              <label>
                Opponents
                <select value={form.opponents ?? "legacy"}
                  onChange={(e) => setForm({ ...form, opponents: e.target.value as Config["opponents"] })}>
                  <option value="pokerth">PokerTH engine 4</option>
                  <option value="legacy">Legacy heuristic</option>
                </select>
              </label>
              <label>
                Agent mode
                <select
                  value={form.mode}
                  onChange={(e) =>
                    setForm({ ...form, mode: e.target.value as Config["mode"] })
                  }
                >
                  <option value="heuristic">Heuristic baseline</option>
                  <option
                    value="openrouter"
                    disabled={!server?.openrouter_configured}
                  >
                    OpenRouter
                    {!server?.openrouter_configured
                      ? " · configure backend key first"
                      : ""}
                  </option>
                </select>
              </label>
              {form.mode === "openrouter" && (
                <label>
                  OpenRouter model ID
                  <input
                    required
                    placeholder="provider/model-id"
                    value={form.model}
                    onChange={(e) =>
                      setForm({ ...form, model: e.target.value })
                    }
                  />
                  <small>
                    Choose a model supporting structured JSON output. Maximum{" "}
                    {server?.agent_call_limit} calls per table, then heuristic
                    fallback.
                  </small>
                </label>
              )}
              <button
                className="button primary full-width"
                disabled={busy || active.length >= 2}
              >
                {busy ? "Creating table..." : "Create table"}
                <ChevronRight size={16} />
              </button>
            </form>
          </section>
        </div>
      )}
      {settings && (
        <div className="modal-scrim" onClick={() => setSettings(false)}>
          <section
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="settings-title"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="modal-close icon-button"
              onClick={() => setSettings(false)}
              aria-label="Close"
            >
              <X size={20} />
            </button>
            <span className="modal-symbol">
              <Settings2 size={24} />
            </span>
            <h2 id="settings-title">Connections</h2>
            <p>Model, storage and tracing configuration.</p>
            <div className="connection-row">
              <span>OpenRouter</span>
              <b>
                {server?.openrouter_configured
                  ? "Key configured"
                  : "Not configured"}
              </b>
            </div>
            <div className="connection-row">
              <span>Persistence</span>
              <b>{server?.storage || "Unavailable"}</b>
            </div>
            <div className="connection-row">
              <span>LangSmith</span>
              <b>{server?.tracing ? "Enabled" : "Disabled"}</b>
            </div>
            <label>
              Server access token
              <input
                type="password"
                value={tokenDraft}
                onChange={(e) => setTokenDraft(e.target.value)}
                autoComplete="off"
                placeholder="Only required for a protected backend"
              />
            </label>
            <small>
              This is CONTROL_TOKEN, not your OpenRouter key. It is kept in this
              browser tab’s session storage.
            </small>
            <button
              className="button primary full-width"
              onClick={() => {
                sessionStorage.setItem("wtr-token", tokenDraft);
                setToken(tokenDraft);
                setSettings(false);
              }}
            >
              Save connection
            </button>
            <details>
              <summary>Local setup</summary>
              <p>
                Set OPENROUTER_API_KEY and OPENROUTER_MODEL in apps/api/.env,
                then restart the backend. Set DATABASE_URL to your Supabase
                PostgreSQL connection to use hosted storage.
              </p>
            </details>
          </section>
        </div>
      )}
    </div>
  );
}
