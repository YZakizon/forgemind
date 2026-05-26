import AsyncStorage from "@react-native-async-storage/async-storage";

import type { Mode } from "./components";

export type OnboardingPreferences = {
  goals: string[];
  stressCategories: string[];
  communicationPreference: string;
  supportPreference: string;
};

export const ONBOARDING_STORAGE_KEY = "forgemind:onboarding:v1";
const LAST_TALK_MODE_KEY = "forgemind:talk-mode:last:v1";
const PENDING_TALK_MODE_KEY = "forgemind:talk-mode:pending:v1";

export async function loadOnboardingPreferences(): Promise<OnboardingPreferences | null> {
  const value = await AsyncStorage.getItem(ONBOARDING_STORAGE_KEY);
  return value ? (JSON.parse(value) as OnboardingPreferences) : null;
}

export async function saveOnboardingPreferences(preferences: OnboardingPreferences): Promise<void> {
  await AsyncStorage.setItem(ONBOARDING_STORAGE_KEY, JSON.stringify(preferences));
}

export async function loadLastTalkMode(): Promise<Mode | null> {
  const value = await AsyncStorage.getItem(LAST_TALK_MODE_KEY);
  return isMode(value) ? value : null;
}

export async function saveLastTalkMode(mode: Mode): Promise<void> {
  await AsyncStorage.setItem(LAST_TALK_MODE_KEY, mode);
}

export async function savePendingTalkMode(mode: Mode): Promise<void> {
  await AsyncStorage.setItem(PENDING_TALK_MODE_KEY, mode);
}

export async function consumePendingTalkMode(): Promise<Mode | null> {
  const value = await AsyncStorage.getItem(PENDING_TALK_MODE_KEY);
  await AsyncStorage.removeItem(PENDING_TALK_MODE_KEY);
  return isMode(value) ? value : null;
}

function isMode(value: string | null): value is Mode {
  return value === "Vent" || value === "Advice" || value === "Calm" || value === "Clarity";
}
