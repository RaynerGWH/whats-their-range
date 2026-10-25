import { useEffect, useState } from "react";
import {
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  Circle,
  Pause,
  Play,
  Plus,
  Settings2,
  SkipForward,
  Square,
  X,
} from "lucide-react";
import { request } from "./api";
import { HeroControl } from "./workspace/HeroControl";
import { ThemeSwitch } from "./theme";
import { useSession } from "./workspace/useSession";
import { Connections, CreateDialog } from "./workspace/Dialogs";
import {
  DecisionPanel,
  History,
  PokerTable,
  PublicChat,
  Standings,
} from "./workspace/Panels";
import { decisionFor, finished, supports } from "./workspace/data";
import TraceBrowser from "./trace/TraceBrowser";

export default function App() {
  const session = useSession();
  const {
    tables,
    table,
    live,
    server,
    selected,
    connection,
    error,
    token,
    replay,
    frames,
    historyBusy,
  } = session;
  const [create, setCreate] = useState(false),
    [settings, setSettings] = useState(false),
    [library, setLibrary] = useState(false);
  const [seat, setSeat] = useState(0),
    [reveal, setReveal] = useState(false),
    [traceOpen, setTraceOpen] = useState(false);
  const [inspection, setInspection] = useState(false);
  const active = tables.filter((table) => !finished(table.status));
  const ready = !!table?.players?.length;
  const decision = table ? decisionFor(table, seat) : null;
  useEffect(() => {
    setSeat(table?.config.hero_seat ?? 0);
    setReveal(false);
    setInspection(false);
    setTraceOpen(false);
  }, [selected, table?.config.hero_seat, table?.config.hero_control]);
  const choose = (id: string) => {
    session.choose(id);
    setLibrary(false);
  };
  const selectSeat = (next: number) => {
    setSeat(next);
    setTraceOpen(false);
  };
  const canTrace =
    !!table &&
    (inspection || table.config.opponents !== "llm") &&
    (table.config.opponents === "llm"
      ? supports(server, "per_seat_traces")
      : seat === 0);
  const frameIndex = replay
    ? frames.findIndex((frame) => frame.version === replay.version)
    : -1;
  return (
    <div className="terminal-app">
      <a className="skip-link" href="#workspace">
        Skip to table workspace
      </a>
      <header className="app-header">
        <a className="wordmark" href="#" onClick={() => setLibrary(false)}>
          <span className="pixel-mark">♠</span>
          <strong>
            what's their range<span>?</span>
          </strong>
        </a>
        <div className="header-tools">
          <span
            className={`connection-state ${connection === "live" ? "connected" : ""}`}
          >
            <i />
            {connection === "live" ? "Connected" : connection}
          </span>
          <ThemeSwitch />
          <button
            className="icon-button"
            aria-label="Connections"
            onClick={() => setSettings(true)}
          >
            <Settings2 size={17} />
          </button>
        </div>
      </header>
      <nav className="session-nav" aria-label="Table sessions">
        <button
          className={library ? "selected" : ""}
          aria-pressed={library}
          onClick={() => setLibrary(!library)}
        >
          Sessions <span>{tables.length}</span>
        </button>
        <div className="session-tabs">
          {active.map((item) => (
            <button
              key={item.id}
              className={!library && selected === item.id ? "selected" : ""}
              aria-pressed={!library && selected === item.id}
              onClick={() => choose(item.id)}
            >
              <Circle size={7} fill="currentColor" />
              {item.config.name}
              <span>{item.status}</span>
            </button>
          ))}
          {!active.length && (
            <span className="muted nav-empty">No active tables</span>
          )}
        </div>
        <button
          className="new-table"
          disabled={!server || active.length >= (server.max_tables || 2)}
          onClick={() => setCreate(true)}
        >
          <Plus size={14} />
          <span>New table</span>
        </button>
      </nav>
      <main id="workspace">
        {error && (
          <div className="error-banner" role="alert">
            <span>{error}</span>
            <button
              aria-label="Dismiss error"
              onClick={() => session.setError("")}
            >
              <X size={14} />
            </button>
          </div>
        )}
        {connection !== "live" && (
          <div className="notice" role="status">
            {connection === "offline"
              ? "Backend unavailable. Check Connections."
              : "Reconnecting to live tables..."}{" "}
            Existing records may be out of date.
          </div>
        )}
        {library ? (
          <>
            <div className="workspace-heading">
              <h1>Sessions</h1>
              <span className="muted">{tables.length} saved</span>
            </div>
            <div className="session-library">
              {tables.length ? (
                [...tables].reverse().map((item) => (
                  <button
                    className="session-card"
                    key={item.id}
                    onClick={() => choose(item.id)}
                  >
                    <span className="session-card-title">
                      {item.config.name}
                      <ChevronRight size={15} />
                    </span>
                    <span>
                      {item.config.opponents === "llm"
                        ? "LLM"
                        : item.config.opponents === "pokerth"
                          ? "PokerTH"
                          : "Legacy"}{" "}
                      · {item.config.player_count || 6} players
                    </span>
                    <span className="muted">
                      {item.status} · Hand {item.hand || 0}
                    </span>
                  </button>
                ))
              ) : (
                <p className="empty-state">
                  No saved sessions. Create a table to begin.
                </p>
              )}
            </div>
          </>
        ) : (
          <>
            <div className="workspace-heading">
              <div>
                <span className="kicker">
                  {replay ? "Replay" : "Live tables"}
                </span>
                <h1>
                  {table?.config.name || "Table workspace"}
                  <span
                    className={`state-label ${live?.status === "running" ? "running" : ""}`}
                  >
                    {replay ? "Historical" : table?.status || "Ready"}
                  </span>
                </h1>
              </div>
              <div className="table-controls">
                {replay ? (
                  <button
                    className="button primary"
                    onClick={() => session.setReplay(null)}
                  >
                    <ArrowLeft size={13} />
                    Return to live
                  </button>
                ) : (
                  <>
                    <button
                      className="button primary"
                      disabled={
                        !ready ||
                        finished(live?.status || "") ||
                        connection !== "live"
                      }
                      onClick={() =>
                        session.control(
                          live?.status === "running" ? "pause" : "resume",
                        )
                      }
                    >
                      {live?.status === "running" ? (
                        <Pause size={13} />
                      ) : (
                        <Play size={13} />
                      )}{" "}
                      {live?.status === "running" ? "Pause" : "Run table"}
                    </button>
                    <button
                      className="button"
                      disabled={
                        !ready ||
                        live?.status !== "paused" ||
                        connection !== "live"
                      }
                      onClick={() => session.control("step")}
                    >
                      <SkipForward size={14} />
                      Step
                    </button>
                  </>
                )}
                <label className="pace-label">
                  <span>Pace</span>
                  <select
                    aria-label="Table pace"
                    value={live?.config.pace || 1.2}
                    disabled={
                      !ready ||
                      finished(live?.status || "") ||
                      !!replay ||
                      connection !== "live"
                    }
                    onChange={(event) =>
                      session.control("speed", Number(event.target.value))
                    }
                  >
                    <option value={2.4}>0.5×</option>
                    <option value={1.2}>1×</option>
                    <option value={0.3}>4×</option>
                    <option value={0.05}>Fast</option>
                  </select>
                </label>
                <button
                  className="icon-button stop-button"
                  disabled={
                    !ready ||
                    finished(live?.status || "") ||
                    !!replay ||
                    connection !== "live"
                  }
                  aria-label="End and archive session"
                  onClick={() => session.control("stop")}
                >
                  <Square size={13} />
                </button>
              </div>
            </div>
            {table?.error && (
              <p className="error-banner" role="alert">
                {table.error}
              </p>
            )}
            {replay && (
              <div className="replay-bar">
                <button
                  className="button"
                  disabled={historyBusy}
                  onClick={() => session.loadHistory(true)}
                >
                  Load older
                </button>
                <button
                  className="icon-button"
                  aria-label="Previous replay event"
                  disabled={frameIndex <= 0}
                  onClick={() => session.setReplay(frames[frameIndex - 1])}
                >
                  <ChevronLeft size={15} />
                </button>
                <input
                  aria-label="Replay position"
                  type="range"
                  min={0}
                  max={Math.max(0, frames.length - 1)}
                  value={Math.max(0, frameIndex)}
                  onChange={(event) =>
                    session.setReplay(frames[Number(event.target.value)])
                  }
                />
                <button
                  className="icon-button"
                  aria-label="Next replay event"
                  disabled={frameIndex >= frames.length - 1}
                  onClick={() => session.setReplay(frames[frameIndex + 1])}
                >
                  <ChevronRight size={15} />
                </button>
                <label>
                  Hand
                  <select
                    aria-label="Replay hand"
                    value={replay.hand}
                    onChange={(event) =>
                      session.setReplay(
                        frames.find(
                          (frame) => frame.hand === Number(event.target.value),
                        )!,
                      )
                    }
                  >
                    {[...new Set(frames.map((frame) => frame.hand))].map(
                      (hand) => (
                        <option key={hand} value={hand}>
                          {hand}
                        </option>
                      ),
                    )}
                  </select>
                </label>
                <span>State {replay.version}</span>
              </div>
            )}
            {table && (
              <div className="view-choice">
                <div className="segmented" aria-label="Workspace view">
                  <button
                    aria-pressed={!inspection}
                    onClick={() => {
                      setInspection(false);
                      setReveal(false);
                      setTraceOpen(false);
                      setSeat(table.config.hero_seat ?? 0);
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
                  <span className="muted">
                    Private cards and decision records are available in this
                    view.
                  </span>
                )}
              </div>
            )}
            <div className="main-grid">
              <PokerTable
                table={table}
                selected={seat}
                onSelect={selectSeat}
                inspection={inspection}
                reveal={reveal}
                setReveal={setReveal}
              />
              <PublicChat table={table} server={server} replay={!!replay} />
            </div>
            {traceOpen && table && canTrace && (
              <div className="trace-workspace">
                <div className="trace-context">
                  <span>
                    Trace ·{" "}
                    {table.players?.find((player) => player.seat === seat)
                      ?.name || `Seat ${seat + 1}`}
                  </span>
                  <button
                    className="text-button"
                    onClick={() => setTraceOpen(false)}
                  >
                    Close trace <X size={13} />
                  </button>
                </div>
                <TraceBrowser
                  key={`${table.id}:${seat}:${replay ? replay.version : "live"}:${token}`}
                  tableId={table.id}
                  hand={table.hand}
                  decisionTraceId={decision?.trace_id}
                  decisionHand={decision?.hand}
                  activeTraceId={
                    !replay && table.actor === seat
                      ? table.active_trace_id
                      : null
                  }
                  player={
                    supports(server, "per_seat_traces") ? seat : undefined
                  }
                  token={token}
                  connection={connection}
                />
              </div>
            )}
            <div className="lower-grid">
              {table?.config.opponents === "llm" && !inspection ? (
                <HeroControl
                  key={table.id}
                  table={table}
                  server={server}
                  connection={connection}
                  replay={!!replay}
                  onAction={(payload, signal) =>
                    request(
                      `/tables/${encodeURIComponent(table.id)}/hero-action`,
                      token,
                      payload,
                      signal,
                    )
                  }
                  onControl={(payload, signal) =>
                    request(
                      `/tables/${encodeURIComponent(table.id)}/control`,
                      token,
                      payload,
                      signal,
                    )
                  }
                  onRefresh={session.refresh}
                />
              ) : (
                <DecisionPanel
                  key={`${selected}:${seat}`}
                  table={table}
                  seat={inspection ? seat : (table?.config.hero_seat ?? 0)}
                  server={server}
                  onTrace={() => {
                    if (!inspection) setSeat(table?.config.hero_seat ?? 0);
                    setTraceOpen(!traceOpen);
                  }}
                />
              )}
              <History
                table={table}
                replay={!!replay}
                onReplay={() => session.loadHistory()}
                historyBusy={historyBusy}
              />
              <Standings table={table} selected={seat} onSelect={selectSeat} />
            </div>
          </>
        )}
        <footer>
          <span>NLH · Tournament</span>
          <span>
            {server?.storage || "Storage unavailable"} ·{" "}
            {server?.tracing ? "LangSmith enabled" : "Local traces"}
          </span>
        </footer>
      </main>
      {create && (
        <CreateDialog
          server={server}
          count={tables.length}
          onClose={() => setCreate(false)}
          onCreate={session.create}
        />
      )}
      {settings && (
        <Connections
          server={server}
          token={token}
          onSave={session.saveToken}
          onClose={() => setSettings(false)}
        />
      )}
    </div>
  );
}
