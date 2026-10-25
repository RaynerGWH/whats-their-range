export type SeatConfig = {
  seat: number;
  name: string;
  model: string;
  instruction_profile: "free_play";
  harness: "baseline";
  chat_enabled: boolean;
  temperature?: number;
};
export type ChatMessage = {
  id: string;
  sequence: number;
  player: number;
  hand: number;
  state_version: number;
  text: string;
};
export type HeroAction = {
  turn_token: string;
  state_version: number;
  action: string;
  public_message?: string;
};
export type HeroControlChange = {
  action: "set_hero_control";
  hero_control: "human" | "llm";
  state_version: number;
};
export type HeroTurn = {
  player: number;
  state_version: number;
  chat_sequence: number;
  turn_token: string;
  observation: Record<string, unknown> & {
    legal: { key: string; kind: string; amount: number }[];
  };
};
export type Config = {
  llm_limits?: { max_message_chars?: number };
  hero_control?: "human" | "llm";
  player_count?: 4 | 6;
  hero_seat?: number;
  seat_configs?: SeatConfig[];
  name: string;
  seed: number;
  stack_bb: number;
  hands_per_level: number;
  payouts: "70/30" | "winner-take-all";
  mode: "heuristic" | "openrouter";
  opponents?: "legacy" | "pokerth" | "llm";
  model: string;
  pace: number;
};
export type Event = {
  id: string;
  hand: number;
  street: string;
  text: string;
  player: number | null;
  action: string | null;
  amount: number;
};
export type Stats = {
  actions: number;
  raises: number;
  calls: number;
  folds: number;
};
export type Player = {
  seat: number;
  name: string;
  stack: number;
  bet: number;
  cards: string[];
  active: boolean;
  eliminated: boolean;
  position: string;
  last_action: string | null;
  stats: Stats;
  prize: number;
  place: number | null;
};
export type Evidence = Stats & {
  seat: number;
  name: string;
  recent_actions: Event[];
};
export type Decision = {
  player?: number;
  chat_sequence?: number;
  trace_id?: string | null;
  langsmith_url?: string | null;
  action: string;
  source: string;
  model: string | null;
  summary: string;
  uncertainty: string;
  evidence_ids: string[];
  metrics?: {
    equity?: number;
    standard_error?: number;
    samples?: number;
    pot_odds_reference?: number;
    icm_at_hand_start?: number;
    assumption?: string;
    limitation?: string;
  };
  evidence: Evidence[];
  observation: Record<string, unknown>;
  latency_ms: number | null;
  state_version: number;
  hand: number;
  street: string;
  event_id: string;
  fallback: string | null;
  calls: number;
  usage: {
    prompt_tokens?: number | null;
    completion_tokens?: number | null;
    cost?: number | null;
    input_tokens?: number | null;
    output_tokens?: number | null;
    cost_usd?: number | null;
  };
};
export type Table = {
  hero_turn?: HeroTurn | null;
  chat?: ChatMessage[];
  chat_sequence?: number;
  decisions_by_player?: Record<string, Decision | null>;
  active_trace_id?: string | null;
  id: string;
  config: Config;
  status: string;
  phase: string;
  error?: string | null;
  version: number;
  hand: number;
  street: string;
  level: number;
  small_blind: number;
  big_blind: number;
  hands_to_level: number;
  button: number;
  actor: number | null;
  players: Player[];
  board: string[];
  pot: number;
  remaining: number;
  history: Event[];
  decision: Decision | null;
  series: { hand: number; stack: number }[];
  icm: Record<string, number>;
  icm_basis: string;
  agent_decisions: number;
};
export type ServerConfig = {
  llm_limits?: Config["llm_limits"];
  llm_preset?: Config;
  capabilities?: {
    manual_hero?: boolean;
    llm_tables?: boolean;
    public_chat?: boolean;
    per_seat_traces?: boolean;
  };
  openrouter_configured: boolean;
  default_model: string;
  tracing: boolean;
  storage: string;
  max_tables: number;
  agent_call_limit: number;
};
