import { useEffect, useRef, useState, type ReactNode } from "react";
import { X } from "lucide-react";
import type { Config, ServerConfig } from "../types";
import {
  applyPreset,
  readPreset,
  savePreset,
  type OpponentPreset,
} from "./preset";
import { creationPayload, seatDefaults, supports } from "./data";

export function Dialog({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current;
    if (dialog && !dialog.open) dialog.showModal();
    return () => dialog?.close();
  }, []);
  return (
    <dialog
      ref={ref}
      className="dialog"
      aria-label={title}
      onCancel={onClose}
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className="dialog-inner">
        <header>
          <h2>{title}</h2>
          <button
            type="button"
            className="icon-button"
            aria-label="Close dialog"
            onClick={onClose}
          >
            <X size={18} />
          </button>
        </header>
        {children}
      </div>
    </dialog>
  );
}
export function CreateDialog({
  server,
  count,
  onClose,
  onCreate,
}: {
  server: ServerConfig | null;
  count: number;
  onClose: () => void;
  onCreate: (config: Config) => Promise<void>;
}) {
  const [preset, setPreset] = useState<OpponentPreset>(
    () =>
      readPreset() || {
        model: server?.default_model || "",
        instruction_profile: "free_play",
        harness: "baseline",
        chat_enabled: true,
      },
  );
  const [presetStatus, setPresetStatus] = useState("");
  const [config, setConfig] = useState<Config>(() => ({
    name: `Table ${count + 1}`,
    seed: Math.floor(Math.random() * 100000),
    stack_bb: 50,
    hands_per_level: 8,
    payouts: "70/30",
    mode: "heuristic",
    opponents: "pokerth",
    model: server?.default_model || "",
    pace: 1.2,
  }));
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const isLLM = config.opponents === "llm";
  const canLLM =
    supports(server, "llm_tables") && !!server?.openrouter_configured;
  const update = <K extends keyof Config>(key: K, value: Config[K]) =>
    setConfig((old) => ({ ...old, [key]: value }));
  return (
    <Dialog title="New tournament" onClose={onClose}>
      <p className="dialog-intro">
        Starts paused. Configure the table before running.
      </p>
      <form
        onSubmit={async (event) => {
          event.preventDefault();
          setBusy(true);
          setError("");
          try {
            await onCreate(creationPayload(config, server));
            onClose();
          } catch (error) {
            setError((error as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <label>
          Session name
          <input
            autoFocus
            required
            maxLength={50}
            value={config.name}
            onChange={(event) => update("name", event.target.value)}
          />
        </label>
        <div className="form-grid">
          <label>
            Opponents
            <select
              value={config.opponents}
              onChange={(event) => {
                const opponents = event.target.value as Config["opponents"];
                setConfig((old) => ({
                  ...old,
                  opponents,
                  ...(opponents === "llm"
                    ? {
                        player_count: 6,
                        hero_control: "human",
                        hero_seat: 0,
                        mode: "openrouter",
                        seat_configs: applyPreset(
                          seatDefaults(6, old.seat_configs),
                          0,
                          preset,
                        ),
                      }
                    : { mode: "heuristic" }),
                }));
              }}
            >
              <option value="pokerth">PokerTH engine 4</option>
              <option value="legacy">Legacy heuristic</option>
              <option value="llm" disabled={!canLLM}>
                LLM players{!canLLM ? " (unavailable)" : ""}
              </option>
            </select>
          </label>
          <label>
            Players
            <select
              value={isLLM ? (config.player_count ?? 6) : 6}
              disabled={!isLLM}
              onChange={(event) => {
                const player_count = Number(event.target.value) as 4 | 6;
                setConfig((old) => ({
                  ...old,
                  player_count,
                  hero_seat: Math.min(old.hero_seat ?? 0, player_count - 1),
                  seat_configs: applyPreset(
                    seatDefaults(player_count, old.seat_configs),
                    Math.min(old.hero_seat ?? 0, player_count - 1),
                    preset,
                  ),
                }));
              }}
            >
              <option value={4}>4 players</option>
              <option value={6}>6 players</option>
            </select>
          </label>
        </div>
        {!canLLM && (
          <p className="field-note">
            {!supports(server, "llm_tables")
              ? "LLM seat configuration is unavailable on this backend."
              : "Configure the backend OpenRouter key to use LLM players."}
          </p>
        )}
        <div className="form-grid">
          <label>
            Starting stack
            <select
              value={config.stack_bb}
              onChange={(event) =>
                update("stack_bb", Number(event.target.value))
              }
            >
              <option value={20}>20 BB</option>
              <option value={50}>50 BB</option>
              <option value={100}>100 BB</option>
            </select>
          </label>
          <label>
            Payouts
            <select
              value={config.payouts}
              onChange={(event) =>
                update("payouts", event.target.value as Config["payouts"])
              }
            >
              <option value="70/30">Top two, 70 / 30</option>
              <option value="winner-take-all">Winner takes all</option>
            </select>
          </label>
          <label>
            Hands per blind level
            <input
              type="number"
              min={2}
              max={100}
              required
              value={config.hands_per_level}
              onChange={(event) =>
                update("hands_per_level", Number(event.target.value))
              }
            />
          </label>
          <label>
            Deck seed
            <input
              type="number"
              min={0}
              max={2147483647}
              required
              value={config.seed}
              onChange={(event) => update("seed", Number(event.target.value))}
            />
          </label>
        </div>
        {!isLLM && (
          <label>
            Hero policy
            <select
              value={config.mode}
              onChange={(event) =>
                update("mode", event.target.value as Config["mode"])
              }
            >
              <option value="heuristic">Heuristic baseline</option>
              <option
                value="openrouter"
                disabled={!server?.openrouter_configured}
              >
                OpenRouter
                {!server?.openrouter_configured ? " (key not configured)" : ""}
              </option>
            </select>
          </label>
        )}
        {(isLLM || config.mode === "openrouter") && (
          <label>
            {isLLM ? "Default OpenRouter model" : "OpenRouter model"}
            <input
              placeholder="provider/model-id"
              maxLength={150}
              required={!isLLM}
              value={config.model}
              onChange={(event) => update("model", event.target.value)}
            />
            <small>Model support is validated by the backend.</small>
          </label>
        )}
        {isLLM && (
          <>
            <label>
              Hero seat
              <select
                value={config.hero_seat ?? 0}
                onChange={(event) =>
                  setConfig((old) => ({
                    ...old,
                    hero_seat: Number(event.target.value),
                    seat_configs: applyPreset(
                      old.seat_configs || [],
                      Number(event.target.value),
                      preset,
                    ),
                  }))
                }
              >
                {seatDefaults(
                  config.player_count ?? 6,
                  config.seat_configs,
                ).map((seat) => (
                  <option key={seat.seat} value={seat.seat}>
                    {seat.seat + 1} · {seat.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Hero control
              <select
                value={config.hero_control || "human"}
                onChange={(event) =>
                  update("hero_control", event.target.value as "human" | "llm")
                }
              >
                <option
                  value="human"
                  disabled={!supports(server, "manual_hero")}
                >
                  Manual
                  {!supports(server, "manual_hero") ? " (unavailable)" : ""}
                </option>
                <option value="llm">LLM</option>
              </select>
            </label>
            {!supports(server, "manual_hero") && (
              <p className="field-note">
                Manual control is unavailable. Choose LLM explicitly to automate
                the hero.
              </p>
            )}
            <fieldset className="seat-config">
              <legend>Neutral opponent preset</legend>
              <label>
                Opponent model
                <input
                  value={preset.model}
                  placeholder="Use table default"
                  onChange={(event) => {
                    const next = {
                      ...preset,
                      seats: undefined,
                      model: event.target.value,
                    };
                    setPreset(next);
                    update(
                      "seat_configs",
                      applyPreset(
                        config.seat_configs || [],
                        config.hero_seat ?? 0,
                        next,
                      ),
                    );
                    setPresetStatus("");
                  }}
                />
              </label>
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={
                    preset.chat_enabled && supports(server, "public_chat")
                  }
                  disabled={!supports(server, "public_chat")}
                  onChange={(event) => {
                    const next = {
                      ...preset,
                      seats: undefined,
                      chat_enabled: event.target.checked,
                    };
                    setPreset(next);
                    update(
                      "seat_configs",
                      applyPreset(
                        config.seat_configs || [],
                        config.hero_seat ?? 0,
                        next,
                      ),
                    );
                    setPresetStatus("");
                  }}
                />
                Opponent public chat
              </label>
              <p className="field-note">
                Free play · Baseline · Applied to {config.player_count! - 1}{" "}
                opponents. Hero takeover keeps these settings.
              </p>
              <button
                type="button"
                className="button"
                onClick={() => {
                  try {
                    savePreset({
                      ...preset,
                      model:
                        preset.model.trim() ||
                        config.model.trim() ||
                        server?.default_model ||
                        "",
                      seats: config.seat_configs
                        ?.filter((seat) => seat.seat !== config.hero_seat)
                        .map((seat) => ({
                          ...seat,
                          model:
                            seat.model.trim() ||
                            config.model.trim() ||
                            server?.default_model ||
                            "",
                        })),
                    });
                    setPresetStatus("Preset saved in this browser.");
                  } catch {
                    setPresetStatus(
                      "Browser storage unavailable. Current settings still apply.",
                    );
                  }
                }}
              >
                Save opponent preset
              </button>
              {presetStatus && (
                <p role="status" className="field-note">
                  {presetStatus}
                </p>
              )}
            </fieldset>
            <p className="field-note">
              Free play supplies the rules and objective, with no suggested
              strategy. Each model chooses its own tactics.
            </p>
            <div className="seat-configs">
              {(config.seat_configs || []).map((seat, index) => (
                <fieldset
                  key={seat.seat}
                  className={`seat-config seat-color-${seat.seat}`}
                >
                  <legend>
                    Seat {seat.seat + 1}
                    {seat.seat === config.hero_seat ? " · Hero" : ""}
                  </legend>
                  <div className="form-grid">
                    <label>
                      Name
                      <input
                        aria-label={`Seat ${seat.seat + 1} name`}
                        required
                        value={seat.name}
                        maxLength={50}
                        onChange={(event) =>
                          update(
                            "seat_configs",
                            config.seat_configs!.map((item, i) =>
                              i === index
                                ? { ...item, name: event.target.value }
                                : item,
                            ),
                          )
                        }
                      />
                    </label>
                    <label>
                      Model override
                      <input
                        aria-label={`Seat ${seat.seat + 1} model`}
                        placeholder="Use table default"
                        maxLength={150}
                        value={seat.model}
                        onChange={(event) =>
                          update(
                            "seat_configs",
                            config.seat_configs!.map((item, i) =>
                              i === index
                                ? { ...item, model: event.target.value }
                                : item,
                            ),
                          )
                        }
                      />
                    </label>
                    <label>
                      Instruction profile
                      <select
                        aria-label={`Seat ${seat.seat + 1} instruction profile`}
                        value={seat.instruction_profile}
                        onChange={(event) =>
                          update(
                            "seat_configs",
                            config.seat_configs!.map((item, i) =>
                              i === index
                                ? {
                                    ...item,
                                    instruction_profile: event.target
                                      .value as typeof seat.instruction_profile,
                                  }
                                : item,
                            ),
                          )
                        }
                      >
                        <option value="free_play">Free play</option>
                      </select>
                    </label>
                    <label>
                      Harness
                      <select
                        aria-label={`Seat ${seat.seat + 1} harness`}
                        value="baseline"
                        onChange={() => {}}
                      >
                        <option value="baseline">Baseline</option>
                      </select>
                    </label>
                  </div>
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      aria-label={`Seat ${seat.seat + 1} public chat`}
                      checked={
                        supports(server, "public_chat") && seat.chat_enabled
                      }
                      disabled={!supports(server, "public_chat")}
                      onChange={(event) =>
                        update(
                          "seat_configs",
                          config.seat_configs!.map((item, i) =>
                            i === index
                              ? { ...item, chat_enabled: event.target.checked }
                              : item,
                          ),
                        )
                      }
                    />
                    Public chat
                    {!supports(server, "public_chat") && " (unavailable)"}
                  </label>
                </fieldset>
              ))}
            </div>
          </>
        )}
        {(isLLM || config.mode === "openrouter") && (
          <p className="field-note">
            Backend call and time limits apply. Call caps are not a dollar cap.
          </p>
        )}
        {error && (
          <p className="error-banner" role="alert">
            {error}
          </p>
        )}
        <button
          className="button primary full-width"
          disabled={busy || !server}
        >
          {busy ? "Creating..." : "Create table"}
        </button>
      </form>
    </Dialog>
  );
}
export function Connections({
  server,
  token,
  onSave,
  onClose,
}: {
  server: ServerConfig | null;
  token: string;
  onSave: (token: string) => void;
  onClose: () => void;
}) {
  const [draft, setDraft] = useState(token);
  return (
    <Dialog title="Connections" onClose={onClose}>
      <dl className="connection-list">
        <div>
          <dt>OpenRouter</dt>
          <dd>
            {server?.openrouter_configured
              ? "Key configured"
              : "Not configured"}
          </dd>
        </div>
        <div>
          <dt>Storage</dt>
          <dd>{server?.storage || "Unavailable"}</dd>
        </div>
        <div>
          <dt>LangSmith</dt>
          <dd>{server?.tracing ? "Enabled" : "Disabled"}</dd>
        </div>
        <div>
          <dt>LLM tables</dt>
          <dd>
            {supports(server, "llm_tables") ? "Available" : "Unavailable"}
          </dd>
        </div>
        <div>
          <dt>Public chat</dt>
          <dd>
            {supports(server, "public_chat") ? "Available" : "Unavailable"}
          </dd>
        </div>
        <div>
          <dt>Manual hero</dt>
          <dd>
            {supports(server, "manual_hero") ? "Available" : "Unavailable"}
          </dd>
        </div>
        <div>
          <dt>Per-seat traces</dt>
          <dd>
            {supports(server, "per_seat_traces") ? "Available" : "Unavailable"}
          </dd>
        </div>
      </dl>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          onSave(draft);
          onClose();
        }}
      >
        <label>
          Server access token
          <input
            autoFocus
            type="password"
            autoComplete="off"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
          />
        </label>
        <p className="field-note">
          CONTROL_TOKEN for this backend. Stored in this browser tab. Provider
          keys and database credentials stay on the server.
        </p>
        <button className="button primary full-width">Save connection</button>
      </form>
    </Dialog>
  );
}
