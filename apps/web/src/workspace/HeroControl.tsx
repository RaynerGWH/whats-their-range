import { useEffect, useRef, useState } from "react";
import { UserRound } from "lucide-react";
import type {
  HeroAction,
  HeroControlChange,
  ServerConfig,
  Table,
} from "../types";
import { actionLabel, decisionFor, finished, supports } from "./data";
import { Panel } from "./Panels";

type Props = {
  table: Table;
  server: ServerConfig | null;
  connection: string;
  replay: boolean;
  onAction: (payload: HeroAction, signal: AbortSignal) => Promise<unknown>;
  onControl: (
    payload: HeroControlChange,
    signal: AbortSignal,
  ) => Promise<unknown>;
  onRefresh: () => Promise<void>;
};
export function HeroControl({
  table,
  server,
  connection,
  replay,
  onAction,
  onControl,
  onRefresh,
}: Props) {
  const [action, setAction] = useState("");
  const [message, setMessage] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const locked = useRef(false);
  const controller = useRef<AbortController | null>(null);
  const hero = table.config.hero_seat ?? 0;
  const mode = table.config.hero_control ?? "llm";
  const turn = table.hero_turn;
  const signature = `${table.id}:${mode}:${turn?.turn_token || ""}:${turn?.state_version ?? ""}:${replay}`;
  const current = useRef(signature);
  current.current = signature;
  useEffect(() => {
    locked.current = false;
    setBusy(false);
    setAction("");
    setMessage("");
    setStatus("");
    setError("");
    controller.current?.abort();
    return () => controller.current?.abort();
  }, [signature]);
  const available = supports(server, "manual_hero");
  const playable = !replay && connection === "live" && !finished(table.status);
  const valid =
    available &&
    playable &&
    mode === "human" &&
    turn?.player === hero &&
    turn.state_version === table.version &&
    !!turn.turn_token;
  const legal = valid ? turn.observation.legal || [] : [];
  const chatAllowed =
    supports(server, "public_chat") &&
    table.config.seat_configs?.find((seat) => seat.seat === hero)
      ?.chat_enabled === true;
  const messageLimit =
    table.config.llm_limits?.max_message_chars ??
    server?.llm_limits?.max_message_chars ??
    240;
  const publicMessage = message.trim();
  const invalidMessage =
    chatAllowed &&
    (Array.from(publicMessage).length > messageLimit ||
      /[\u0000-\u001f]/.test(publicMessage));
  const last = decisionFor(table, hero);
  const send = async (kind: "action" | "control", next?: "human" | "llm") => {
    if (locked.current || !available || !playable) return;
    if (
      kind === "action" &&
      (!valid || invalidMessage || !legal.some((item) => item.key === action))
    )
      return;
    if (kind === "control" && (!next || next === mode)) return;
    locked.current = true;
    setBusy(true);
    setError("");
    setStatus(
      kind === "action"
        ? "Submitting action..."
        : "Requesting control change...",
    );
    const started = signature;
    const requestController = new AbortController();
    controller.current = requestController;
    try {
      if (kind === "action")
        await onAction(
          {
            turn_token: turn!.turn_token,
            state_version: turn!.state_version,
            action,
            ...(chatAllowed && publicMessage
              ? { public_message: publicMessage }
              : {}),
          },
          requestController.signal,
        );
      else
        await onControl(
          {
            action: "set_hero_control",
            hero_control: next!,
            state_version: table.version,
          },
          requestController.signal,
        );
      if (requestController.signal.aborted || current.current !== started)
        return;
      setStatus(
        kind === "action"
          ? "Submitted. Waiting for the table to update."
          : "Control change requested. Waiting for the table to update.",
      );
      // Keep this turn locked until authoritative state changes or explicit refresh.
    } catch (error) {
      if (requestController.signal.aborted || current.current !== started)
        return;
      setStatus("");
      setError(
        `${(error as Error).message} Refresh the current turn before trying again.`,
      );
      setBusy(false);
    }
  };
  const refresh = async () => {
    if (busy) return;
    setBusy(true);
    const started = signature;
    try {
      await onRefresh();
      if (current.current !== started) return;
      locked.current = false;
      setStatus("");
      setError("");
      setAction("");
      setMessage("");
    } catch (error) {
      if (current.current === started) setError((error as Error).message);
    } finally {
      if (current.current === started) setBusy(false);
    }
  };
  return (
    <Panel
      title="Hero control"
      icon={<UserRound size={14} />}
      className="hero-control"
      tools={
        <span className="badge">
          {replay ? "Replay" : mode === "human" ? "Manual" : "LLM"}
        </span>
      }
    >
      <div className="hero-mode">
        <span>
          {table.players?.find((player) => player.seat === hero)?.name ||
            `Seat ${hero + 1}`}
        </span>
        <div className="segmented" aria-label="Hero control mode">
          <button
            type="button"
            aria-pressed={mode === "human"}
            disabled={!available || !playable || busy || locked.current}
            onClick={() => send("control", "human")}
          >
            Manual
          </button>
          <button
            type="button"
            aria-pressed={mode === "llm"}
            disabled={!available || !playable || busy || locked.current}
            onClick={() => send("control", "llm")}
          >
            LLM
          </button>
        </div>
      </div>
      {!available && (
        <p className="panel-note">
          Manual control is unavailable on this backend.
        </p>
      )}
      <div className="hero-turn-body">
        {error && (
          <p className="error-banner" role="alert">
            {error}
          </p>
        )}
        {status && (
          <p className="notice" role="status">
            {status}
          </p>
        )}
        {replay ? (
          <p className="empty-state">
            Historical state. Return to live to act.
          </p>
        ) : mode === "llm" ? (
          <div className="empty-state">
            <span className="empty-symbol">{">_"}</span>
            <p>The LLM controls the hero. Opponent settings stay fixed.</p>
            {last && (
              <p>
                Last action: <strong>{actionLabel(last.action)}</strong> ·{" "}
                {last.source === "human" ? "Manual" : last.source}
              </p>
            )}
          </div>
        ) : valid ? (
          <form
            onSubmit={(event) => {
              event.preventDefault();
              void send("action");
            }}
          >
            <div className="manual-turn-heading">
              <h3>Your turn</h3>
              <span>
                State {turn.state_version} · Chat #{turn.chat_sequence}
              </span>
            </div>
            <fieldset
              className="legal-actions"
              disabled={busy || locked.current}
            >
              <legend>Choose an action</legend>
              {legal.map((item) => (
                <button
                  type="button"
                  key={item.key}
                  aria-pressed={action === item.key}
                  className={action === item.key ? "chosen-action" : ""}
                  onClick={() => setAction(item.key)}
                >
                  {item.key === "check"
                    ? "Check"
                    : item.kind === "call"
                    ? `Call ${item.amount}`
                    : actionLabel(item.key)}
                </button>
              ))}
            </fieldset>
            <label className="hero-message">
              Public message <span>(optional)</span>
              <textarea
                aria-label="Public message"
                rows={2}
                value={message}
                disabled={!chatAllowed || busy || locked.current}
                onChange={(event) => setMessage(event.target.value)}
                placeholder={
                  chatAllowed
                    ? "Leave empty to stay silent"
                    : "Chat is disabled for the hero"
                }
              />
            </label>
            {chatAllowed && (
              <p className="field-note">
                {Array.from(publicMessage).length} / {messageLimit} characters
              </p>
            )}
            {invalidMessage && (
              <p className="error-banner" role="alert">
                Use one line with at most {messageLimit} characters.
              </p>
            )}
            <button
              className="button primary full-width"
              disabled={
                !action || invalidMessage || busy || locked.current || !valid
              }
            >
              Submit {action ? actionLabel(action).toLowerCase() : "action"}
            </button>
            <p className="field-note">
              Action and message are submitted together. No automatic action.
            </p>
          </form>
        ) : (
          <div className="empty-state">
            <span className="empty-symbol">[ ]</span>
            <p>
              {connection !== "live"
                ? "Disconnected. Waiting for current table state."
                : finished(table.status)
                  ? "This table has ended."
                  : turn && turn.state_version !== table.version
                    ? "Waiting for a current turn."
                    : table.status === "paused"
                      ? "Table paused. Step or run until your turn."
                      : "Waiting for your turn. No hero action will be chosen automatically."}
            </p>
          </div>
        )}
      </div>
      <div className="decision-footer">
        <span className="muted">
          {mode === "human"
            ? `${(table.config.player_count || 6) - 1} LLM opponents`
            : `${table.config.player_count || 6} LLM players`}
          {table.status === "paused" ? " · Paused" : ""}
        </span>
        <button
          className="text-button"
          disabled={busy || replay || connection !== "live"}
          onClick={refresh}
        >
          Refresh turn
        </button>
      </div>
    </Panel>
  );
}
