import { create } from "zustand";
import { API_BASE } from "../lib/api";

interface LlmState {
  providerOk: boolean | null;
  models: string[];
  selectedModel: string;
  discover: () => Promise<void>;
  setModel: (model: string) => void;
}

export const useLlmStore = create<LlmState>((set, get) => ({
  providerOk: null,
  models: [],
  selectedModel: (() => {
    try {
      return localStorage.getItem("llm_model") || "";
    } catch {
      return "";
    }
  })(),
  discover: async () => {
    try {
      const r = await fetch(`${API_BASE}/api/llm/providers`);
      const d = await r.json();
      const providers = d.providers || d;
      const list: string[] = [];
      if (Array.isArray(providers))
        for (const p of providers) if (p.models) list.push(...p.models);
      const saved = get().selectedModel;
      const next = list.includes(saved) ? saved : list[0] || "";
      if (next) localStorage.setItem("llm_model", next);
      set({ providerOk: list.length > 0, models: list, selectedModel: next });
    } catch {
      set({ providerOk: false });
    }
  },
  setModel: (model) => {
    localStorage.setItem("llm_model", model);
    set({ selectedModel: model });
  },
}));
