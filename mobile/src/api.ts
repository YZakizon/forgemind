import { NativeModules } from "react-native";

import type { Mode } from "./components";

const { ForgeMindConfig } = NativeModules as {
  ForgeMindConfig?: { API_BASE_URL?: string };
};

export const API_BASE_URL = ForgeMindConfig?.API_BASE_URL ?? "http://127.0.0.1:8005";
export const DEMO_USER_ID = "00000000-0000-4000-8000-000000000001";
let demoAccessToken: string | null = null;

export type ForgeChatResponse = {
  response: string;
  safety_level: string;
  memories_used: string[];
  guidance_topics: string[];
  transcript?: string | null;
  persisted: boolean;
};

export type MoodCheckin = {
  id: string;
  user_id: string;
  label: string;
  intensity?: number | null;
  note?: string | null;
  created_at: string;
};

export type ResetSession = {
  id: string;
  user_id: string;
  reset_type: string;
  completed: boolean;
  notes?: string | null;
  created_at: string;
  completed_at?: string | null;
};

export type ProgressSummary = {
  user_id: string;
  checkins_this_week: number;
  resets_completed_this_week: number;
  themes: Array<{ label: string; value: number; tone: string }>;
  recent_checkins: MoodCheckin[];
  recent_resets: ResetSession[];
};

export type DataControlResponse = {
  user_id: string;
  status: string;
  detail: string;
};

export type UserDataExport = {
  user_id: string;
  memories: unknown[];
  mood_checkins: MoodCheckin[];
  reset_sessions: ResetSession[];
  chat_messages: Array<Record<string, string | null>>;
};

async function ensureDemoAccessToken(): Promise<string> {
  if (demoAccessToken) return demoAccessToken;
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider: "google", identity_token: "demo-token" })
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  const result = (await response.json()) as { access_token: string; user_id: string };
  if (result.user_id !== DEMO_USER_ID) {
    throw new Error("Demo token did not match the demo user.");
  }
  demoAccessToken = result.access_token;
  return demoAccessToken;
}

async function authHeaders() {
  return { Authorization: `Bearer ${await ensureDemoAccessToken()}` };
}

export async function sendChatMessage(message: string, mode: Mode): Promise<ForgeChatResponse> {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: DEMO_USER_ID, message, mode: mode.toLowerCase() })
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

export async function createMoodCheckin(label: string, intensity?: number): Promise<MoodCheckin> {
  const response = await fetch(`${API_BASE_URL}/mood-checkins`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: DEMO_USER_ID, label, intensity })
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

export async function createResetSession(resetType: string): Promise<ResetSession> {
  const response = await fetch(`${API_BASE_URL}/reset-sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: DEMO_USER_ID, reset_type: resetType })
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

export async function completeResetSession(resetId: string): Promise<ResetSession> {
  const response = await fetch(`${API_BASE_URL}/reset-sessions/${resetId}/complete?user_id=${DEMO_USER_ID}`, {
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

export async function fetchProgressSummary(): Promise<ProgressSummary> {
  const response = await fetch(`${API_BASE_URL}/progress/summary?user_id=${DEMO_USER_ID}`);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

export async function archiveMemories(): Promise<DataControlResponse> {
  const response = await fetch(`${API_BASE_URL}/memories/archive?user_id=${DEMO_USER_ID}`, {
    method: "POST",
    headers: await authHeaders()
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

export async function exportUserData(): Promise<UserDataExport> {
  const response = await fetch(`${API_BASE_URL}/users/${DEMO_USER_ID}/export`, {
    headers: await authHeaders()
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

export async function deleteUserData(): Promise<DataControlResponse> {
  const response = await fetch(`${API_BASE_URL}/users/${DEMO_USER_ID}/data`, {
    method: "DELETE",
    headers: await authHeaders()
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

export async function sendVoiceMessage(audioPath: string, mode: Mode): Promise<ForgeChatResponse> {
  const form = new FormData();
  form.append("user_id", DEMO_USER_ID);
  form.append("mode", mode.toLowerCase());
  form.append("audio", {
    uri: `file://${audioPath}`,
    name: "forgemind-voice.m4a",
    type: "audio/mp4"
  } as unknown as Blob);

  const response = await fetch(`${API_BASE_URL}/voice-chat`, {
    method: "POST",
    body: form
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}
