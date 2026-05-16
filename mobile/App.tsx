import React, { useState } from "react";
import { SafeAreaView, ScrollView, StatusBar, StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";

const tabs = ["Home", "Talk", "Reset", "Progress", "Profile"] as const;
type Tab = (typeof tabs)[number];

const quickActions = ["Talk it out", "Calm down", "Clear my head", "I’m overwhelmed", "Angry", "Can’t sleep"];
const modes = ["Vent", "Advice", "Calm Down", "Think Clearly", "Night Support"];
const resetTools = ["Anger Reset", "Panic Reset", "Breakup Reset", "Burnout Reset", "Sleep Reset", "Confidence Reset"];

function HomeScreen() {
  return (
    <ScrollView contentContainerStyle={styles.screen}>
      <Text style={styles.kicker}>Morning.</Text>
      <Text style={styles.title}>What’s taking most of your energy today?</Text>
      <View style={styles.chipGrid}>
        {quickActions.map((action) => (
          <TouchableOpacity style={styles.chip} key={action}>
            <Text style={styles.chipText}>{action}</Text>
          </TouchableOpacity>
        ))}
      </View>
      <View style={styles.panel}>
        <Text style={styles.panelLabel}>Daily insight</Text>
        <Text style={styles.panelText}>Work pressure has shown up several times this week.</Text>
      </View>
      <View style={styles.panel}>
        <Text style={styles.panelLabel}>Reflection</Text>
        <Text style={styles.panelText}>You tend to feel clearer after naming the one decision in front of you.</Text>
      </View>
    </ScrollView>
  );
}

function TalkScreen() {
  const [text, setText] = useState("");
  return (
    <View style={styles.screen}>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.modeRow}>
        {modes.map((mode) => (
          <TouchableOpacity style={styles.modeChip} key={mode}>
            <Text style={styles.chipText}>{mode}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>
      <View style={styles.messageUser}>
        <Text style={styles.messageText}>I’m overthinking again.</Text>
      </View>
      <View style={styles.messageAi}>
        <Text style={styles.messageText}>Let’s slow it down. What part of this is fact, and what part is pressure?</Text>
      </View>
      <View style={styles.inputBar}>
        <TextInput
          value={text}
          onChangeText={setText}
          placeholder="Say what’s going on"
          placeholderTextColor="#7f898c"
          style={styles.input}
        />
        <TouchableOpacity style={styles.sendButton}>
          <Text style={styles.sendText}>Send</Text>
        </TouchableOpacity>
      </View>
      <TouchableOpacity style={styles.voiceButton}>
        <Text style={styles.voiceText}>Voice support coming later</Text>
      </TouchableOpacity>
    </View>
  );
}

function ResetScreen() {
  return (
    <ScrollView contentContainerStyle={styles.screen}>
      <Text style={styles.kicker}>Reset</Text>
      <Text style={styles.title}>Pick the pressure you want to lower.</Text>
      {resetTools.map((tool) => (
        <TouchableOpacity style={styles.listItem} key={tool}>
          <Text style={styles.listTitle}>{tool}</Text>
          <Text style={styles.listSubtitle}>Short, practical, and low pressure.</Text>
        </TouchableOpacity>
      ))}
    </ScrollView>
  );
}

function ProgressScreen() {
  return (
    <ScrollView contentContainerStyle={styles.screen}>
      <Text style={styles.kicker}>Progress</Text>
      <Text style={styles.title}>Patterns, not pressure.</Text>
      {["Work pressure", "Sleep consistency", "Small wins"].map((item) => (
        <View style={styles.panel} key={item}>
          <Text style={styles.panelLabel}>{item}</Text>
          <Text style={styles.panelText}>A calm summary will appear here as ForgeMind learns what helps.</Text>
        </View>
      ))}
    </ScrollView>
  );
}

function ProfileScreen() {
  return (
    <ScrollView contentContainerStyle={styles.screen}>
      <Text style={styles.kicker}>Profile</Text>
      <Text style={styles.title}>Privacy and control.</Text>
      {["Memory controls", "Delete memory", "Export data", "Notification settings", "Subscription status", "Emergency resources"].map((item) => (
        <TouchableOpacity style={styles.listItem} key={item}>
          <Text style={styles.listTitle}>{item}</Text>
        </TouchableOpacity>
      ))}
    </ScrollView>
  );
}

function CurrentScreen({ tab }: { tab: Tab }) {
  if (tab === "Talk") return <TalkScreen />;
  if (tab === "Reset") return <ResetScreen />;
  if (tab === "Progress") return <ProgressScreen />;
  if (tab === "Profile") return <ProfileScreen />;
  return <HomeScreen />;
}

export default function App() {
  const [tab, setTab] = useState<Tab>("Home");
  return (
    <SafeAreaView style={styles.root}>
      <StatusBar barStyle="light-content" />
      <CurrentScreen tab={tab} />
      <View style={styles.tabBar}>
        {tabs.map((item) => (
          <TouchableOpacity style={[styles.tab, tab === item && styles.tabActive]} key={item} onPress={() => setTab(item)}>
            <Text style={[styles.tabText, tab === item && styles.tabTextActive]}>{item}</Text>
          </TouchableOpacity>
        ))}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: "#0d0f10"
  },
  screen: {
    flexGrow: 1,
    padding: 20,
    gap: 16
  },
  kicker: {
    color: "#79a7c8",
    fontSize: 14
  },
  title: {
    color: "#edf0ee",
    fontSize: 28,
    lineHeight: 34,
    fontWeight: "700"
  },
  chipGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 10
  },
  chip: {
    backgroundColor: "#171a1d",
    borderColor: "#2b3236",
    borderWidth: 1,
    borderRadius: 8,
    paddingVertical: 12,
    paddingHorizontal: 14
  },
  modeRow: {
    flexGrow: 0,
    marginBottom: 18
  },
  modeChip: {
    backgroundColor: "#171a1d",
    borderColor: "#2b3236",
    borderWidth: 1,
    borderRadius: 8,
    paddingVertical: 10,
    paddingHorizontal: 12,
    marginRight: 8
  },
  chipText: {
    color: "#edf0ee"
  },
  panel: {
    backgroundColor: "#171a1d",
    borderColor: "#2b3236",
    borderWidth: 1,
    borderRadius: 8,
    padding: 16
  },
  panelLabel: {
    color: "#9aa4a6",
    marginBottom: 6
  },
  panelText: {
    color: "#edf0ee",
    lineHeight: 22
  },
  messageUser: {
    alignSelf: "flex-end",
    backgroundColor: "#20303a",
    borderRadius: 8,
    padding: 12,
    maxWidth: "82%"
  },
  messageAi: {
    alignSelf: "flex-start",
    backgroundColor: "#171a1d",
    borderRadius: 8,
    padding: 12,
    maxWidth: "82%"
  },
  messageText: {
    color: "#edf0ee",
    lineHeight: 21
  },
  inputBar: {
    marginTop: "auto",
    flexDirection: "row",
    alignItems: "center",
    gap: 8
  },
  input: {
    flex: 1,
    minHeight: 46,
    color: "#edf0ee",
    backgroundColor: "#171a1d",
    borderColor: "#2b3236",
    borderWidth: 1,
    borderRadius: 8,
    paddingHorizontal: 12
  },
  sendButton: {
    minHeight: 46,
    justifyContent: "center",
    backgroundColor: "#79a7c8",
    borderRadius: 8,
    paddingHorizontal: 14
  },
  sendText: {
    color: "#0d0f10",
    fontWeight: "700"
  },
  voiceButton: {
    borderColor: "#2b3236",
    borderWidth: 1,
    borderRadius: 8,
    padding: 12,
    alignItems: "center"
  },
  voiceText: {
    color: "#9aa4a6"
  },
  listItem: {
    backgroundColor: "#171a1d",
    borderColor: "#2b3236",
    borderWidth: 1,
    borderRadius: 8,
    padding: 16
  },
  listTitle: {
    color: "#edf0ee",
    fontWeight: "700"
  },
  listSubtitle: {
    color: "#9aa4a6",
    marginTop: 6
  },
  tabBar: {
    flexDirection: "row",
    borderTopColor: "#2b3236",
    borderTopWidth: 1,
    backgroundColor: "#101315"
  },
  tab: {
    flex: 1,
    alignItems: "center",
    paddingVertical: 12
  },
  tabActive: {
    backgroundColor: "#171a1d"
  },
  tabText: {
    color: "#9aa4a6",
    fontSize: 12
  },
  tabTextActive: {
    color: "#edf0ee"
  }
});
