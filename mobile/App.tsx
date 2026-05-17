import React, { useEffect, useState } from "react";
import { NavigationContainer } from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { ActivityIndicator, StatusBar, View } from "react-native";

import { BottomTabBar } from "./src/components";
import { colors } from "./src/design";
import { loadOnboardingPreferences, saveOnboardingPreferences, type OnboardingPreferences } from "./src/preferences";
import { HomeScreen, OnboardingScreen, ProfileScreen, ProgressScreen, ResetScreen, TalkScreen } from "./src/screens";

type RootTabParamList = {
  Home: undefined;
  Talk: undefined;
  Reset: undefined;
  Progress: undefined;
  Profile: undefined;
};

const Tab = createBottomTabNavigator<RootTabParamList>();

export default function App() {
  const [loading, setLoading] = useState(true);
  const [onboarded, setOnboarded] = useState(false);

  useEffect(() => {
    loadOnboardingPreferences()
      .then((preferences) => setOnboarded(Boolean(preferences)))
      .finally(() => setLoading(false));
  }, []);

  async function completeOnboarding(preferences: OnboardingPreferences) {
    await saveOnboardingPreferences(preferences);
    setOnboarded(true);
  }

  if (loading) {
    return (
      <View style={{ flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.background }}>
        <StatusBar barStyle="light-content" backgroundColor={colors.background} />
        <ActivityIndicator color={colors.accentBright} />
      </View>
    );
  }

  if (!onboarded) {
    return <OnboardingScreen onComplete={completeOnboarding} />;
  }

  return (
    <NavigationContainer>
      <StatusBar barStyle="light-content" backgroundColor={colors.background} />
      <Tab.Navigator
        initialRouteName="Home"
        tabBar={(props) => <BottomTabBar {...props} />}
        screenOptions={{ headerShown: false }}
      >
        <Tab.Screen name="Home" component={HomeScreen} />
        <Tab.Screen name="Talk" component={TalkScreen} />
        <Tab.Screen name="Reset" component={ResetScreen} />
        <Tab.Screen name="Progress" component={ProgressScreen} />
        <Tab.Screen name="Profile" component={ProfileScreen} />
      </Tab.Navigator>
    </NavigationContainer>
  );
}
