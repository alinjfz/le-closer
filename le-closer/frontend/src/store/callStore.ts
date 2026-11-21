import { create } from "zustand";

export interface Segment { id: string; speaker: "rep" | "client"; text: string; start_ms: number; end_ms: number; }
export interface Card {
  id: string; kind: string; title: string; body: string; sources: string[];
  confidence: number; status: string; segment_id?: string; meta: Record<string, any>;
}
export interface Task { id: string; title: string; owner: string; origin: string; status: string; result_ref?: string; }
export interface FlowState { stage: string; bant: Record<string, string>; }
export interface DealFacts { seats?: number; list_price_per_seat?: number; currency: string; requested_discount_pct?: number; budget?: number; contract_years?: number; }
export interface DealNumbers { deal_value?: number; discount_floor_pct: number; price_at_requested_discount?: number; margin_pct?: number; client_roi_estimate?: number; within_guardrails: boolean; }
export interface ActivityEntry { agent: string; message: string; status: string; ts: number; }
export interface ClientProfile { company: string; country: string; people: any[]; cultural_briefing?: string; industry: string; }

interface CallState {
  call_id: string; mode: string; demo: boolean; client: ClientProfile;
  segments: Segment[]; cards: Card[]; tasks: Task[]; flow: FlowState;
  facts: DealFacts; numbers: DealNumbers | null; mindmap_md: string;
  prototypes: { id: string; title: string; html: string }[];
  activity: ActivityEntry[]; notes: any; followup_draft: string | null;
  followup_status: string; ended: boolean;
  meet_url: string | null; bot_status: string; bot_detail: string; started_at: number;
}

interface Store {
  call: CallState | null;
  partials: Record<string, string>;
  connected: boolean;
  setCall: (c: CallState) => void;
  setConnected: (v: boolean) => void;
  applyEvent: (type: string, payload: any) => void;
  reset: () => void;
}

const initialCall: CallState = {
  call_id: "", mode: "sales", demo: false,
  client: { company: "", country: "DE", people: [], industry: "" },
  segments: [], cards: [], tasks: [],
  flow: { stage: "rapport", bant: { budget: "unknown", authority: "unknown", need: "unknown", timeline: "unknown" } },
  facts: { currency: "EUR" }, numbers: null, mindmap_md: "# Call",
  prototypes: [], activity: [], notes: null, followup_draft: null,
  followup_status: "none", ended: false,
  meet_url: null, bot_status: "offline", bot_detail: "", started_at: 0,
};

export const useCallStore = create<Store>((set) => ({
  call: null,
  partials: {},
  connected: false,
  setCall: (c) => set({ call: c }),
  setConnected: (v) => set({ connected: v }),
  reset: () => set({ call: null, partials: {}, connected: false }),
  applyEvent: (type, payload) => set((s) => {
    if (!s.call) return s;
    const call = { ...s.call };
    switch (type) {
      case "state.sync": return { call: payload, partials: {} };
      case "transcript.delta":
        return { partials: { ...s.partials, [payload.speaker]: (s.partials[payload.speaker] || "") + payload.text } };
      case "transcript.segment": {
        const partials = { ...s.partials };
        delete partials[payload.speaker];
        return { call: { ...call, segments: [...call.segments, payload] }, partials };
      }
      case "card.upsert": {
        const idx = call.cards.findIndex((c) => c.id === payload.id);
        const cards = idx >= 0 ? call.cards.map((c, i) => (i === idx ? payload : c)) : [...call.cards, payload];
        return { call: { ...call, cards } };
      }
      case "task.upsert": {
        const idx = call.tasks.findIndex((t) => t.id === payload.id);
        const tasks = idx >= 0 ? call.tasks.map((t, i) => (i === idx ? payload : t)) : [...call.tasks, payload];
        return { call: { ...call, tasks } };
      }
      case "flow.update": return { call: { ...call, flow: payload } };
      case "numbers.update": return { call: { ...call, facts: payload.facts, numbers: payload.numbers } };
      case "mindmap.update": return { call: { ...call, mindmap_md: payload } };
      case "prototype.ready": return { call: { ...call, prototypes: [...call.prototypes, payload] } };
      case "activity.log": return { call: { ...call, activity: [...call.activity.slice(-199), payload] } };
      case "call.ended": return { call: { ...call, ended: true } };
      case "bot.status": return { call: { ...call, bot_status: payload.status, bot_detail: payload.detail } };
      case "meet.update": return { call: { ...call, meet_url: payload.meet_url } };
      case "notes.ready": return { call: { ...call, notes: payload } };
      case "followup.awaiting_approval": return { call: { ...call, followup_draft: payload, followup_status: call.followup_status === "sent" ? "sent" : "awaiting_approval" } };
      default: return s;
    }
  }),
}));

export { initialCall };
