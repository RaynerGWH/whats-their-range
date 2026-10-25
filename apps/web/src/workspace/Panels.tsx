import { useEffect, useRef, useState, type ReactNode } from "react";
import {
  ChevronRight,
  Eye,
  EyeOff,
  Terminal,
  MessageSquare,
  List,
  BarChart3,
} from "lucide-react";
import type { Decision, Player, ServerConfig, Table } from "../types";
import {
  actionLabel,
  decisionFor,
  number,
  supports,
  visibleChat,
} from "./data";
import { duration } from "../trace/layout";

export function Panel({
  title,
  icon,
  children,
  tools,
  className = "",
}: {
  title: string;
  icon?: ReactNode;
  children: ReactNode;
  tools?: ReactNode;
  className?: string;
}) {
  const ref = useRef<HTMLElement>(null);
  useEffect(() => {
    const element = ref.current;
    if (!element || !("IntersectionObserver" in window)) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          element.classList.add("revealed");
          observer.disconnect();
        }
      },
      { threshold: 0.04 },
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  return (
    <section ref={ref} className={`panel ${className}`} aria-label={title}>
      <header className="panel-heading">
        <h2>
          {icon}
          <span>{title}</span>
        </h2>
        {tools}
      </header>
      {children}
    </section>
  );
}
export function Card({
  value,
  hidden = false,
  small = false,
}: {
  value?: string;
  hidden?: boolean;
  small?: boolean;
}) {
  const suits: Record<string, string> = { s: "♠", h: "♥", d: "♦", c: "♣" };
  return (
    <span
      className={`card ${small ? "small" : ""} ${hidden ? "back" : !value ? "undealt" : "hd".includes(value[1]) ? "red" : ""}`}
      aria-label={hidden ? "Hidden card" : value || "Undealt card"}
    >
      {hidden ? (
        <span className="card-pattern" />
      ) : value ? (
        <>
          <b>{value[0] === "T" ? "10" : value[0]}</b>
          <span>{suits[value[1]]}</span>
        </>
      ) : (
        <span>·</span>
      )}
    </span>
  );
}
function Seat({
  player,
  table,
  reveal,
  selected,
  onSelect,
  index,
}: {
  player: Player;
  table: Table;
  reveal: boolean;
  selected: number;
  onSelect: (seat: number) => void;
  index: number;
}) {
  const hero = table.config.hero_seat ?? 0;
  return (
    <button
      className={`seat seat-position-${index} seat-color-${player.seat} ${selected === player.seat ? "selected-seat" : ""} ${table.actor === player.seat ? "acting" : ""} ${player.eliminated ? "eliminated" : ""}`}
      aria-label={`Inspect ${player.name}, seat ${player.seat + 1}`}
      aria-pressed={selected === player.seat}
      onClick={() => onSelect(player.seat)}
    >
      <span className="seat-title">
        <span className="seat-marker">
          {String(player.seat + 1).padStart(2, "0")}
        </span>
        <strong>{player.name}</strong>
        {hero === player.seat && (
          <span className="hero-mark" title="Hero">
            H
          </span>
        )}
        {table.button === player.seat && (
          <span className="dealer" title="Dealer">
            D
          </span>
        )}
      </span>
      <span className="seat-chips">
        {number(player.stack)} <small>{player.position}</small>
      </span>
      <span className="seat-cards">
        {player.cards.map((card, index) => (
          <Card
            key={index}
            value={card}
            small
            hidden={player.seat !== hero && !reveal}
          />
        ))}
      </span>
      <span className="seat-action">
        {player.eliminated
          ? `Out · #${player.place}`
          : table.actor === player.seat
            ? "▸ To act"
            : player.last_action
              ? actionLabel(player.last_action)
              : "Ready"}
        {player.bet > 0 && (
          <span className="seat-bet">{number(player.bet)} in</span>
        )}
      </span>
    </button>
  );
}
export function PokerTable({
  table,
  selected,
  onSelect,
  reveal,
  setReveal,
  inspection = false,
}: {
  table?: Table;
  selected: number;
  onSelect: (seat: number) => void;
  reveal: boolean;
  setReveal: (value: boolean) => void;
  inspection?: boolean;
}) {
  const ready = !!table?.players?.length;
  return (
    <Panel
      title="Table"
      icon={<Terminal size={14} />}
      className="table-panel"
      tools={
        inspection ? (
          <button
            className="text-button"
            disabled={!ready}
            onClick={() => setReveal(!reveal)}
          >
            {reveal ? <EyeOff size={14} /> : <Eye size={14} />}
            <span>
              {reveal ? "Hide opponent cards" : "Reveal spectator cards"}
            </span>
          </button>
        ) : (
          <span className="muted">Hero cards only</span>
        )
      }
    >
      <div className="table-meta">
        <span>
          {ready
            ? `${table.remaining} / ${table.players.length} players`
            : table
              ? "Preparing table"
              : "No table selected"}
        </span>
        <span>
          {ready
            ? `Blinds ${table.small_blind}/${table.big_blind} · Level ${table.level}`
            : "NLH tournament"}
        </span>
      </div>
      <div
        className={`arena ${table?.players?.length === 4 ? "four-seats" : "six-seats"}`}
      >
        <div className="table-felt">
          <div className="felt-inner">
            <span className="hand-street">
              {ready
                ? `Hand ${table.hand} · ${table.street}`
                : "Waiting for a table"}
            </span>
            <div className="board">
              {Array.from({ length: 5 }, (_, index) => (
                <Card key={index} value={table?.board?.[index]} />
              ))}
            </div>
            <div className="pot">
              <span>POT</span>
              <strong>{ready ? number(table.pot) : "0"}</strong>
            </div>
          </div>
        </div>
        {ready &&
          table.players.map((player, index) => (
            <Seat
              key={player.seat}
              player={player}
              index={index}
              table={table}
              reveal={inspection && reveal}
              selected={selected}
              onSelect={onSelect}
            />
          ))}
      </div>
      <div className="table-current" role="status">
        <span
          className={`status-dot ${table?.phase === "thinking" ? "thinking" : ""}`}
        />
        {table?.status === "finished"
          ? `${table.players.find((player) => player.place === 1)?.name || "Winner"} wins the tournament`
          : table?.phase === "thinking"
            ? `${table.players?.find((player) => player.seat === table.actor)?.name || "Player"} is deciding`
            : ready && table.actor !== null
              ? `${table.players.find((player) => player.seat === table.actor)?.name || "Player"} to act`
              : "Waiting for play"}
        <span className="muted">
          {table?.config.opponents === "pokerth"
            ? "PokerTH engine 4"
            : table?.config.opponents === "llm"
              ? "LLM table"
              : table
                ? "Legacy opponents"
                : ""}
        </span>
      </div>
    </Panel>
  );
}
export function DecisionPanel({
  table,
  seat,
  server,
  onTrace,
}: {
  table?: Table;
  seat: number;
  server: ServerConfig | null;
  onTrace: () => void;
}) {
  const [tab, setTab] = useState("Decision");
  const player = table?.players?.find((player) => player.seat === seat);
  const decision = table ? decisionFor(table, seat) : null;
  const canTrace =
    decision?.source !== "human" &&
    !!table &&
    (table.config.opponents === "llm"
      ? supports(server, "per_seat_traces")
      : seat === 0);
  return (
    <Panel
      title="Player decision"
      icon={<Terminal size={14} />}
      className="decision-panel"
      tools={<span className="badge">Private spectator record</span>}
    >
      <div className={`selected-player seat-color-${seat}`}>
        <span className="seat-marker">{String(seat + 1).padStart(2, "0")}</span>
        <strong>{player?.name || "Select a player"}</strong>
        <span className="muted">{player?.position}</span>
      </div>
      <div className="tabs" aria-label="Decision views">
        {["Decision", "Evidence", "Raw input"].map((name) => (
          <button
            key={name}
            aria-pressed={tab === name}
            className={tab === name ? "selected" : ""}
            onClick={() => setTab(name)}
          >
            {name}
          </button>
        ))}
      </div>
      <div className="decision-content">
        {!decision ? (
          <div className="empty-state">
            <span className="empty-symbol">[ ]</span>
            <p>
              {!player
                ? "Select a table to inspect a player."
                : table?.config.opponents !== "llm" && seat !== 0
                  ? `${table?.config.opponents === "pokerth" ? "PokerTH" : "Legacy opponents"} does not record LLM decisions.`
                  : "No decision recorded for this player yet."}
            </p>
            {player?.last_action && (
              <p>
                Last public action:{" "}
                <strong>{actionLabel(player.last_action)}</strong>
              </p>
            )}
          </div>
        ) : decision.source === "human" ? (
          <div className="empty-state">
            <p>Manual decision · {actionLabel(decision.action)}</p>
            <p>Source: human. No model execution.</p>
          </div>
        ) : tab === "Decision" ? (
          <DecisionSummary decision={decision} />
        ) : tab === "Evidence" ? (
          <>
            <p className="muted">Public actions available at this decision.</p>
            {decision.evidence?.length ? (
              decision.evidence.map((evidence) => (
                <div className="evidence" key={evidence.seat}>
                  <div className={`seat-color-${evidence.seat}`}>
                    <strong>{evidence.name}</strong>
                    <span>{evidence.actions} actions</span>
                  </div>
                  <p className="muted">
                    Raise {evidence.raises} · Call {evidence.calls} · Fold{" "}
                    {evidence.folds}
                  </p>
                  {evidence.recent_actions.map((event) => (
                    <p
                      key={event.id}
                      className={
                        decision.evidence_ids.includes(event.id) ? "cited" : ""
                      }
                    >
                      <span>H{event.hand} · </span>
                      {event.text}
                    </p>
                  ))}
                </div>
              ))
            ) : (
              <p className="empty-state">No evidence recorded.</p>
            )}
          </>
        ) : (
          <>
            <p className="muted">
              Permitted input for {player?.name}. Not public table talk.
            </p>
            <pre
              className="json"
              tabIndex={0}
              aria-label="Selected player input"
            >
              {JSON.stringify(decision.observation, null, 2)}
            </pre>
          </>
        )}
      </div>
      <div className="decision-footer">
        <button className="text-button" disabled={!canTrace} onClick={onTrace}>
          Tools and trace <ChevronRight size={14} />
        </button>
        <span className="muted">
          {!canTrace
            ? "Seat traces unavailable"
            : decision?.trace_id
              ? "Recorded execution"
              : "Browse available traces"}
        </span>
      </div>
    </Panel>
  );
}
function DecisionSummary({ decision: d }: { decision: Decision }) {
  const metrics = d.metrics;
  const inputTokens = d.usage?.input_tokens ?? d.usage?.prompt_tokens;
  const outputTokens = d.usage?.output_tokens ?? d.usage?.completion_tokens;
  const cost = d.usage?.cost_usd ?? d.usage?.cost;
  return (
    <>
      <div className="decision-action">
        <div>
          <span className="kicker">Executed action</span>
          <h3>{actionLabel(d.action)}</h3>
        </div>
        <div className="decision-latency">
          <strong>{duration(d.latency_ms ?? null)}</strong>
          <span>
            Hand {d.hand} · {d.street}
          </span>
        </div>
      </div>
      <div className="decision-source">
        <span className="badge">
          {d.source === "heuristic" ? "Heuristic baseline" : d.source}
        </span>
        <span>{d.model || "No model call"}</span>
      </div>
      {d.fallback && <p className="notice">Fallback: {d.fallback}</p>}
      <p className="decision-summary">{d.summary || "No summary recorded."}</p>
      {d.uncertainty && (
        <p className="uncertainty">
          <span>Uncertainty</span>
          {d.uncertainty}
        </p>
      )}
      <details className="recorded-estimates">
        <summary>Recorded estimates and usage</summary>
        <dl className="metrics">
          {metrics?.equity != null && (
            <div>
              <dt>Equity vs random hands</dt>
              <dd>{(metrics.equity * 100).toFixed(1)}%</dd>
            </div>
          )}
          {metrics?.pot_odds_reference != null && (
            <div>
              <dt>Pot-odds reference</dt>
              <dd>{(metrics.pot_odds_reference * 100).toFixed(1)}%</dd>
            </div>
          )}
          {metrics?.icm_at_hand_start != null && (
            <div>
              <dt>Hand-start ICM</dt>
              <dd>{metrics.icm_at_hand_start.toFixed(1)} units</dd>
            </div>
          )}
          <div>
            <dt>Input tokens</dt>
            <dd>{number(inputTokens)}</dd>
          </div>
          <div>
            <dt>Output tokens</dt>
            <dd>{number(outputTokens)}</dd>
          </div>
          <div>
            <dt>Cost (USD)</dt>
            <dd>
              {cost == null ? "Not recorded" : `$${cost}`}
            </dd>
          </div>
        </dl>
        {metrics?.samples != null && (
          <p className="muted">
            {metrics.samples} samples
            {metrics.standard_error != null &&
              ` · SE ±${(metrics.standard_error * 100).toFixed(1)} percentage points`}
          </p>
        )}
        {metrics?.assumption && <p className="muted">{metrics.assumption}</p>}
        {metrics?.limitation && <p className="muted">{metrics.limitation}</p>}
      </details>
    </>
  );
}
export function PublicChat({
  table,
  server,
  replay,
}: {
  table?: Table;
  server: ServerConfig | null;
  replay: boolean;
}) {
  const messages = table ? visibleChat(table) : [];
  const available =
    !!table && (Array.isArray(table.chat) || supports(server, "public_chat"));
  return (
    <Panel
      title="Table talk"
      icon={<MessageSquare size={14} />}
      className="chat-panel"
      tools={<span className="badge">Public</span>}
    >
      <div
        className="panel-scroll chat-messages"
        tabIndex={0}
        aria-label="Public table talk"
      >
        {messages.length ? (
          messages.map((message) => (
            <article className="chat-message" key={message.id}>
              <div className={`seat-color-${message.player}`}>
                <strong>
                  {table?.players.find(
                    (player) => player.seat === message.player,
                  )?.name || `Seat ${message.player + 1}`}
                </strong>
                <span>
                  H{message.hand} · #{message.sequence}
                </span>
              </div>
              <p>{message.text}</p>
            </article>
          ))
        ) : (
          <div className="empty-state">
            <span className="empty-symbol">{">_"}</span>
            <p>
              {!table
                ? "Select a table to view public messages."
                : !available
                  ? "Public chat is unavailable on this backend."
                  : replay
                    ? "No public messages at this point."
                    : table.config.opponents !== "llm"
                      ? "PokerTH and legacy opponents do not send chat."
                      : "No public messages yet."}
            </p>
          </div>
        )}
      </div>
      <p className="panel-note">Player statements are unverified claims.</p>
    </Panel>
  );
}
export function History({
  table,
  replay,
  onReplay,
  historyBusy,
}: {
  table?: Table;
  replay: boolean;
  onReplay: () => void;
  historyBusy: boolean;
}) {
  return (
    <Panel
      title="Action history"
      icon={<List size={14} />}
      className="history-panel"
      tools={
        <button
          className="text-button"
          disabled={!table?.players || historyBusy}
          onClick={onReplay}
        >
          {historyBusy
            ? "Loading..."
            : replay
              ? "Reload replay"
              : "Open replay"}
        </button>
      }
    >
      <div
        className="panel-scroll history-list"
        tabIndex={0}
        aria-label="Public action history"
      >
        {table?.history?.length ? (
          [...table.history].reverse().map((event) => (
            <div
              className={`history-row ${event.player !== null ? `seat-color-${event.player}` : ""}`}
              key={event.id}
            >
              <span className="history-hand">H{event.hand}</span>
              <span className="history-street">{event.street}</span>
              <p>{event.text}</p>
            </div>
          ))
        ) : (
          <p className="empty-state">No actions recorded yet.</p>
        )}
      </div>
      <p className="panel-note">
        {replay ? "Replay snapshot" : "Latest public actions"}
        {table?.version != null && ` · State ${table.version}`}
      </p>
    </Panel>
  );
}
export function Standings({
  table,
  selected,
  onSelect,
}: {
  table?: Table;
  selected: number;
  onSelect: (seat: number) => void;
}) {
  const players = [...(table?.players || [])].sort((a, b) =>
    a.eliminated !== b.eliminated
      ? Number(a.eliminated) - Number(b.eliminated)
      : b.stack - a.stack,
  );
  return (
    <Panel
      title="Standings"
      icon={<BarChart3 size={14} />}
      className="standings-panel"
      tools={<span className="muted">Chips</span>}
    >
      <div className="panel-scroll">
        <table className="standings">
          <thead>
            <tr>
              <th scope="col">#</th>
              <th scope="col">Player</th>
              <th scope="col">Stack</th>
              <th scope="col">BB</th>
            </tr>
          </thead>
          <tbody>
            {players.map((player, index) => (
              <tr
                className={`seat-color-${player.seat} ${selected === player.seat ? "selected-standing" : ""}`}
                key={player.seat}
              >
                <td>{player.place || index + 1}</td>
                <th scope="row">
                  <button
                    aria-pressed={selected === player.seat}
                    onClick={() => onSelect(player.seat)}
                  >
                    {player.name}
                    {player.seat === (table?.config.hero_seat ?? 0) && (
                      <span className="hero-mark">H</span>
                    )}
                  </button>
                </th>
                <td>{number(player.stack)}</td>
                <td>
                  {table?.big_blind
                    ? (player.stack / table.big_blind).toFixed(1)
                    : "?"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!players.length && <p className="empty-state">No players seated.</p>}
      </div>
      {table?.series?.length ? (
        <details className="stack-chart">
          <summary>Hero stack by hand</summary>
          <svg
            viewBox="0 0 300 80"
            role="img"
            aria-label="Hero chip stack after each completed hand"
          >
            <polyline
              fill="none"
              stroke="var(--cyan)"
              strokeWidth="2"
              points={table.series
                .map(
                  (point, index) =>
                    `${8 + (index / Math.max(1, table.series.length - 1)) * 284},${64 - (point.stack / Math.max(1, ...table.series.map((item) => item.stack))) * 50}`,
                )
                .join(" ")}
            />
            <text x="8" y="78">
              Hand {table.series[0].hand}
            </text>
            <text x="292" y="78" textAnchor="end">
              {table.series.at(-1)?.hand}
            </text>
          </svg>
          <p>Chips, hero seat {(table.config.hero_seat ?? 0) + 1}.</p>
        </details>
      ) : null}
      <p className="panel-note">
        {table?.config.payouts === "winner-take-all"
          ? "Winner takes all"
          : "Payouts 70 / 30"}{" "}
        · Simulated chips
      </p>
    </Panel>
  );
}
