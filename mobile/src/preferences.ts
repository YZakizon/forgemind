import AsyncStorage from "@react-native-async-storage/async-storage";

export type OnboardingPreferences = {
  goals: string[];
  stressCategories: string[];
  communicationPreference: string;
  supportPreference: string;
};

export const ONBOARDING_STORAGE_KEY = "forgemind:onboarding:v1";

export async function loadOnboardingPreferences(): Promise<OnboardingPreferences | null> {
  const value = await AsyncStorage.getItem(ONBOARDING_STORAGE_KEY);
  return value ? (JSON.parse(value) as OnboardingPreferences) : null;
}

export async function saveOnboardingPreferences(preferences: OnboardingPreferences): Promise<void> {
  await AsyncStorage.setItem(ONBOARDING_STORAGE_KEY, JSON.stringify(preferences));
}
