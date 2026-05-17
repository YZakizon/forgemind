import { NativeModules } from "react-native";

import type { Mode } from "./components";

const { ForgeMindConfig } = NativeModules as {
  ForgeMindConfig?: { API_BASE_URL?: string };
};

export const API_BASE_URL = ForgeMindConfig?.API_BASE_URL ?? "http://127.0.0.1:8005";
export const DEMO_USER_ID = "00000000-0000-4000-8000-000000000001";

export type ForgeChatResponse = {
  response: string;
  safety_level: string;
  memories_used: string[];
  guidance_topics: string[];
  transcript?: string | null;
  persisted: boolean;
};

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
