import React from "react";
import { NavigationContainer } from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { StatusBar } from "react-native";

import { BottomTabBar } from "./src/components";
import { colors } from "./src/design";
import { HomeScreen, ProfileScreen, ProgressScreen, ResetScreen, TalkScreen } from "./src/screens";

type RootTabParamList = {
  Home: undefined;
  Talk: undefined;
  Reset: undefined;
  Progress: undefined;
  Profile: undefined;
};

const Tab = createBottomTabNavigator<RootTabParamList>();

export default function App() {
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
