import { NativeModules } from "react-native";

import type { Mode } from "./components";

const { ForgeMindConfig } = NativeModules as {
  ForgeMindConfig?: { API_BASE_URL?: string };
};

export const API_BASE_URL = ForgeMindConfig?.API_BASE_URL ?? "http://127.0.0.1:8005";
const API_BASE_URLS = Array.from(
  new Set([API_BASE_URL, "http://127.0.0.1:8005", "http://10.0.2.2:8005"])
);
const BACKEND_REQUEST_TIMEOUT_MS = 3_000;
export const VOICE_WS_URL = `${API_BASE_URL.replace(/^http/, "ws")}/voice/ws`;
export const DEMO_USER_ID = "00000000-0000-4000-8000-000000000001";
let demoAccessToken: string | null = null;
let activeBackendBaseUrl: string | null = null;

export type ForgeChatResponse = {
  response: string;
  response_parts?: {
    body: string;
    question?: string | null;
  } | null;
  safety_level: string;
  memories_used: string[];
  guidance_topics: string[];
  transcript?: string | null;
  persisted: boolean;
};

export type ChatHistoryItem = {
  role: "forge" | "user";
  text: string;
};

export type VoiceSocketMessage =
  | { type: "ready" }
  | { type: "transcript"; index: number; text: string; started_at_ms?: number | null; ended_at_ms?: number | null }
  | {
      type: "final_transcript";
      text: string;
      segments?: Array<{ index: number; text: string; started_at_ms?: number | null; ended_at_ms?: number | null }>;
    }
  | { type: "response_part"; part: "body" | "question"; text: string; chunk_index?: number; chunk_total?: number }
  | {
      type: "tts_audio";
      part: "body" | "question";
      text: string;
      chunk_index?: number;
      chunk_total?: number;
      audio_base64: string;
      format?: string;
      media_type?: string;
    }
  | { type: "response"; payload: ForgeChatResponse }
  | { type: "done" }
  | { type: "error"; detail?: string; status_code?: number };

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

async function fetchWithBackendFallback(path: string, init: () => RequestInit): Promise<Response> {
  let lastError: unknown = null;
  const baseUrls = activeBackendBaseUrl
    ? [activeBackendBaseUrl, ...API_BASE_URLS.filter((baseUrl) => baseUrl !== activeBackendBaseUrl)]
    : API_BASE_URLS;
  for (const baseUrl of baseUrls) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), BACKEND_REQUEST_TIMEOUT_MS);
    try {
      const request = init();
      const response = await fetch(`${baseUrl}${path}`, { ...request, signal: controller.signal });
      if (response.ok || (response.status >= 400 && response.status < 500)) {
        if (response.ok) {
          activeBackendBaseUrl = baseUrl;
        }
        return response;
      }
      lastError = new Error(await response.text());
    } catch (error) {
      lastError = error;
    } finally {
      clearTimeout(timeout);
    }
  }
  throw new Error(networkErrorMessage(lastError));
}

function networkErrorMessage(error: unknown) {
  const detail = error instanceof Error && error.message ? error.message : "Network request failed";
  return `Backend is unreachable at ${API_BASE_URLS.join(", ")}. Last error: ${detail}`;
}

async function ensureDemoAccessToken(): Promise<string> {
  if (demoAccessToken) return demoAccessToken;
  const response = await fetchWithBackendFallback("/auth/login", () => ({
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider: "google", identity_token: "demo-token" })
  }));
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

export function createVoiceWebSocket(): WebSocket {
  const baseUrl = activeBackendBaseUrl ?? API_BASE_URL;
  return new WebSocket(`${baseUrl.replace(/^http/, "ws")}/voice/ws`);
}

export async function sendChatMessage(message: string, mode: Mode, history: ChatHistoryItem[] = []): Promise<ForgeChatResponse> {
  const response = await fetchWithBackendFallback("/chat", () => ({
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: DEMO_USER_ID, message, mode: mode.toLowerCase(), history })
  }));
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

export async function createMoodCheckin(label: string, intensity?: number): Promise<MoodCheckin> {
  const response = await fetchWithBackendFallback("/mood-checkins", () => ({
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: DEMO_USER_ID, label, intensity })
  }));
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
  const response = await fetchWithBackendFallback("/voice-chat", () => {
    const form = new FormData();
    form.append("user_id", DEMO_USER_ID);
    form.append("mode", mode.toLowerCase());
    form.append("audio", {
      uri: `file://${audioPath}`,
      name: "forgemind-voice.m4a",
      type: "audio/mp4"
    } as unknown as Blob);
    return {
      method: "POST",
      body: form
    };
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

type VoiceStreamEvent = "response" | "done" | "error";

type VoiceStreamHandlers = {
  onResponse?: (response: ForgeChatResponse) => void;
};

export async function transcribeVoiceMessage(audioPath: string): Promise<string> {
  const response = await fetchWithBackendFallback("/voice-transcribe", () => {
    const form = new FormData();
    form.append("audio", {
      uri: `file://${audioPath}`,
      name: "forgemind-voice.m4a",
      type: "audio/mp4"
    } as unknown as Blob);
    return {
      method: "POST",
      body: form
    };
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  const result = (await response.json()) as { transcript: string };
  return result.transcript;
}

export async function sendChatMessageStream(
  message: string,
  mode: Mode,
  history: ChatHistoryItem[] = [],
  handlers: VoiceStreamHandlers = {}
): Promise<ForgeChatResponse> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    let receivedLength = 0;
    let buffer = "";
    let settled = false;
    let finalResponse: ForgeChatResponse | null = null;

    function settleError(error: Error) {
      if (settled) return;
      settled = true;
      xhr.abort();
      reject(error);
    }

    async function fallbackToChat() {
      if (settled) return;
      settled = true;
      try {
        const result = await sendChatMessage(message, mode, history);
        handlers.onResponse?.(result);
        resolve(result);
      } catch (error) {
        reject(error instanceof Error ? error : new Error("Chat failed"));
      }
    }

    function handleBlock(block: string) {
      const lines = block.split(/\r?\n/);
      let event: VoiceStreamEvent = "done";
      const dataLines: string[] = [];

      for (const line of lines) {
        if (line.startsWith("event:")) {
          event = line.slice("event:".length).trim() as VoiceStreamEvent;
        } else if (line.startsWith("data:")) {
          dataLines.push(line.slice("data:".length).trim());
        }
      }

      if (!dataLines.length) return;
      const payload = JSON.parse(dataLines.join("\n")) as { detail?: string } | ForgeChatResponse;

      if (event === "response") {
        finalResponse = payload as ForgeChatResponse;
        handlers.onResponse?.(finalResponse);
      } else if (event === "error") {
        settleError(new Error("detail" in payload && payload.detail ? payload.detail : "Voice chat failed"));
      }
    }

    function processChunk(chunk: string) {
      buffer += chunk;
      const blocks = buffer.split(/\r?\n\r?\n/);
      buffer = blocks.pop() ?? "";
      try {
        for (const block of blocks) {
          handleBlock(block);
        }
      } catch (error) {
        settleError(error instanceof Error ? error : new Error("Voice chat stream failed"));
      }
    }

    xhr.onreadystatechange = () => {
      if (xhr.readyState === XMLHttpRequest.LOADING || xhr.readyState === XMLHttpRequest.DONE) {
        const nextText = xhr.responseText.slice(receivedLength);
        receivedLength = xhr.responseText.length;
        if (nextText) processChunk(nextText);
      }

      if (xhr.readyState !== XMLHttpRequest.DONE || settled) return;
      if (buffer.trim()) processChunk("\n\n");
      if (xhr.status < 200 || xhr.status >= 300) {
        settleError(new Error(xhr.responseText || "Voice chat failed"));
        return;
      }
      if (!finalResponse) {
        fallbackToChat();
        return;
      }
      settled = true;
      resolve(finalResponse);
    };
    xhr.onerror = fallbackToChat;
    xhr.open("POST", `${API_BASE_URL}/chat/stream`);
    xhr.setRequestHeader("Accept", "text/event-stream");
    xhr.setRequestHeader("Content-Type", "application/json");
    xhr.send(JSON.stringify({ user_id: DEMO_USER_ID, message, mode: mode.toLowerCase(), history }));
  });
}
