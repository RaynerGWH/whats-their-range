import type {
  ChatMessage,
  Config,
  Decision,
  SeatConfig,
  ServerConfig,
  Table,
} from "../types";
export const finished = (status: string) =>
  ["finished", "stopped", "interrupted", "error"].includes(status);
export const number = (value: number | null | undefined) =>
  value == null ? "Not recorded" : value.toLocaleString("en");
export const actionLabel = (action: string) =>
  action
    .replace("raise:", "Raise to ")
    .replace(/^./, (letter) => letter.toUpperCase());
export function decisionFor(table: Table, seat: number): Decision | null {
  const decision = table.decisions_by_player?.[String(seat)];
  if (
    decision &&
    (decision.player ?? 0) === seat &&
    decision.state_version <= table.version
  )
    return decision;
  const legacy = table.decision;
  // Unattributed historical records belong to seat 0, regardless of a newer hero setting.
  return legacy &&
    (legacy.player ?? 0) === seat &&
    legacy.state_version <= table.version
    ? legacy
    : null;
}
export function visibleChat(table: Table): ChatMessage[] {
  if (table.chat_sequence == null) return [];
  return (table.chat ?? [])
    .filter(
      (message) =>
        message.sequence <= table.chat_sequence! &&
        message.state_version <= table.version &&
        message.hand <= table.hand,
    )
    .sort((a, b) => a.sequence - b.sequence);
}
export const supports = (
  server: ServerConfig | null,
  capability: "llm_tables" | "public_chat" | "per_seat_traces",
) => server?.capabilities?.[capability] === true;
export function seatDefaults(
  count: number,
  old: SeatConfig[] = [],
): SeatConfig[] {
  return Array.from(
    { length: count },
    (_, seat) =>
      old.find((item) => item.seat === seat) ?? {
        seat,
        name: `Player ${seat + 1}`,
        model: "",
        instruction_profile: "free_play",
        harness: "baseline",
        chat_enabled: true,
      },
  );
}
export function creationPayload(
  config: Config,
  server: ServerConfig | null,
): Config {
  if (config.opponents === "llm") {
    if (!supports(server, "llm_tables") || !server?.openrouter_configured)
      throw new Error("LLM tables are unavailable. Check Connections.");
    const count = config.player_count ?? 4;
    const seats = seatDefaults(count, config.seat_configs).map((seat) => ({
      ...seat,
      model: seat.model.trim(),
      name: seat.name.trim(),
      chat_enabled: supports(server, "public_chat") && seat.chat_enabled,
    }));
    if (
      seats.some(
        (seat) => !(seat.model || config.model.trim() || server.default_model),
      )
    )
      throw new Error("Set a default model or a model for every seat.");
    return {
      ...config,
      mode: "openrouter",
      player_count: count,
      hero_seat: config.hero_seat ?? 0,
      model: config.model.trim(),
      seat_configs: seats,
    };
  }
  // Omit additive fields entirely for old six-player backends.
  const {
    player_count: _count,
    hero_seat: _hero,
    seat_configs: _seats,
    ...baseline
  } = config;
  return baseline;
}
