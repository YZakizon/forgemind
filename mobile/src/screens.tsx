import React, { useState } from "react";
import { NativeModules, PermissionsAndroid, Platform, ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";

import {
  AppHeader,
  AppIcon,
  AppScreen,
  Card,
  ChatBubble,
  GradientCard,
  MessageInput,
  Mode,
  ModeSelector,
  ModeSelectorSheet,
  ProgressBar,
  QuickActionCard,
  ResetToolCard,
  SettingsRow,
  VoiceOrb,
  VoiceRecordingState
} from "./components";
import { sendChatMessage, sendVoiceMessage } from "./api";
import { colors, radii, spacing } from "./design";
import type { OnboardingPreferences } from "./preferences";

const goalOptions = ["Think clearer", "Feel less overwhelmed", "Handle anger", "Sleep better"];
const stressOptions = ["Work pressure", "Relationship stress", "Loneliness", "Family conflict", "Dating stress", "Burnout"];
const communicationOptions = ["Direct and practical", "Calm and reflective", "Short and focused"];
const supportOptions = ["Vent first", "Advice when ready", "Calm me down", "Help me find clarity"];

function toggleSelection(values: string[], value: string) {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
}

export function OnboardingScreen({ onComplete }: { onComplete: (preferences: OnboardingPreferences) => Promise<void> }) {
  const [goals, setGoals] = useState<string[]>(["Think clearer"]);
  const [stressCategories, setStressCategories] = useState<string[]>(["Work pressure"]);
  const [communicationPreference, setCommunicationPreference] = useState(communicationOptions[0]);
  const [supportPreference, setSupportPreference] = useState(supportOptions[0]);
  const [saving, setSaving] = useState(false);

  const canContinue = goals.length > 0 && stressCategories.length > 0 && communicationPreference && supportPreference;

  async function submit() {
    if (!canContinue || saving) return;
    setSaving(true);
    await onComplete({ goals, stressCategories, communicationPreference, supportPreference });
  }

  return (
    <AppScreen>
      <View style={styles.onboardingHero}>
        <View style={styles.onboardingMark}>
          <Text style={styles.onboardingMarkText}>F</Text>
        </View>
        <Text style={styles.onboardingTitle}>ForgeMind</Text>
        <Text style={styles.onboardingCopy}>Set the kind of support that feels useful when pressure is high.</Text>
      </View>

      <OnboardingSection title="What do you want help with?">
        <SelectableGrid options={goalOptions} selected={goals} onToggle={(item) => setGoals((current) => toggleSelection(current, item))} />
      </OnboardingSection>

      <OnboardingSection title="What has been taking space lately?">
        <SelectableGrid
          options={stressOptions}
          selected={stressCategories}
          onToggle={(item) => setStressCategories((current) => toggleSelection(current, item))}
        />
      </OnboardingSection>

      <OnboardingSection title="How should Forge talk with you?">
        <SelectableGrid options={communicationOptions} selected={[communicationPreference]} onToggle={setCommunicationPreference} single />
      </OnboardingSection>

      <OnboardingSection title="What support should come first?">
        <SelectableGrid options={supportOptions} selected={[supportPreference]} onToggle={setSupportPreference} single />
      </OnboardingSection>

      <TouchableOpacity style={[styles.primaryButton, !canContinue && styles.primaryButtonDisabled]} onPress={submit} activeOpacity={0.86}>
        <Text style={styles.primaryButtonText}>{saving ? "Saving..." : "Start with Forge"}</Text>
      </TouchableOpacity>
    </AppScreen>
  );
}

function OnboardingSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card style={styles.onboardingSection}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {children}
    </Card>
  );
}

function SelectableGrid({
  options,
  selected,
  onToggle,
  single = false
}: {
  options: string[];
  selected: string[];
  onToggle: (value: string) => void;
  single?: boolean;
}) {
  return (
    <View style={styles.selectableGrid}>
      {options.map((option) => {
        const active = selected.includes(option);
        return (
          <TouchableOpacity
            key={option}
            style={[styles.selectableChip, active && styles.selectableChipActive, single && styles.selectableChipWide]}
            onPress={() => onToggle(option)}
            activeOpacity={0.86}
          >
            <Text style={[styles.selectableChipText, active && styles.selectableChipTextActive]}>{option}</Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

export function HomeScreen() {
  return (
    <AppScreen>
      <View style={styles.homeHeader}>
        <View>
          <Text style={styles.greeting}>Good evening, Yeffry</Text>
          <Text style={styles.heroQuestion}>What’s taking most of your headspace right now?</Text>
        </View>
        <TouchableOpacity style={styles.iconCircle}>
          <AppIcon name="bell" size={20} />
        </TouchableOpacity>
      </View>

      <GradientCard title="Talk to Forge" subtitle="I’m here. Let’s talk." cta="→" />

      <View style={styles.sectionGap}>
        <Text style={styles.sectionTitle}>Quick check-in</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.quickRow}>
          <QuickActionCard title="Angry" icon="anger" color={colors.danger} />
          <QuickActionCard title="Burned out" icon="burnout" color={colors.warning} />
          <QuickActionCard title="Lonely" icon="lonely" color={colors.purple} />
          <QuickActionCard title="Breakup" icon="breakup" color="#EC4899" />
        </ScrollView>
      </View>

      <View style={styles.twoColumn}>
        <Card style={styles.smallCard}>
          <Text style={styles.cardLabel}>Insight</Text>
          <Text style={styles.cardText}>You’ve mentioned work stress several times this week.</Text>
          <Text style={styles.cardLink}>View details →</Text>
        </Card>
        <Card style={styles.smallCard}>
          <Text style={styles.cardLabel}>Reset</Text>
          <Text style={styles.cardText}>2-minute reset to clear your mind.</Text>
          <Text style={styles.cardLink}>Start →</Text>
        </Card>
      </View>
    </AppScreen>
  );
}

export function TalkScreen() {
  const [mode, setMode] = useState<Mode>("Clarity");
  const [sheetOpen, setSheetOpen] = useState(false);
  const [listening, setListening] = useState(false);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [messages, setMessages] = useState<Array<{ id: string; role: "forge" | "user"; text: string }>>([
    { id: "m1", role: "forge", text: "I’m here, Yeffry. What’s on your mind?" },
    { id: "m2", role: "user", text: "I feel so overwhelmed with work and life right now." },
    { id: "m3", role: "forge", text: "That’s a lot to carry. Let’s slow it down. What’s been the hardest part today?" }
  ]);

  async function submitMessage(text = draft) {
    const trimmed = text.trim();
    if (!trimmed || sending) return;
    setDraft("");
    setError(null);
    setSending(true);
    setMessages((current) => [...current, { id: `user-${Date.now()}`, role: "user", text: trimmed }]);
    try {
      const result = await sendChatMessage(trimmed, mode);
      setMessages((current) => [...current, { id: `forge-${Date.now()}`, role: "forge", text: result.response }]);
    } catch {
      setError("Forge couldn’t reach the backend. Check the server and try again.");
    } finally {
      setSending(false);
    }
  }

  function appendVoiceResponse(text: string, transcript?: string | null) {
    if (transcript) {
      setMessages((current) => [...current, { id: `voice-${Date.now()}`, role: "user", text: transcript }]);
    }
    setMessages((current) => [...current, { id: `forge-${Date.now()}`, role: "forge", text }]);
  }

  if (listening) {
    return (
      <VoiceScreen
        mode={mode}
        onModeChange={setMode}
        onBack={() => setListening(false)}
        onResponse={(result) => {
          appendVoiceResponse(result.response, result.transcript);
          setListening(false);
        }}
        onError={() => setError("Forge couldn’t process that recording. Try again when the backend is available.")}
      />
    );
  }

  return (
    <AppScreen>
      <AppHeader title="Forge" leftIcon="back" rightIcon="sliders" />

      <View style={styles.chatStack}>
        {messages.map((message) => (
          <ChatBubble key={message.id} role={message.role}>
            {message.text}
          </ChatBubble>
        ))}
        {sending ? <ChatBubble role="forge">Forge is thinking...</ChatBubble> : null}
      </View>

      <View style={styles.suggestionRow}>
        {["It’s the pressure", "No time for myself", "I don’t know"].map((item) => (
          <TouchableOpacity key={item} style={styles.suggestionChip} onPress={() => submitMessage(item)}>
            <Text style={styles.suggestionText}>{item}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <MessageInput value={draft} onChangeText={setDraft} onSubmit={() => submitMessage()} disabled={sending} />
      {error ? <Text style={styles.errorText}>{error}</Text> : null}

      <TouchableOpacity style={styles.voicePreview} onPress={() => setListening(true)} activeOpacity={0.86}>
        <View>
          <Text style={styles.voiceTitle}>Tap-to-Talk</Text>
          <Text style={styles.voiceCopy}>Use voice when typing feels like too much.</Text>
        </View>
        <View style={styles.smallMic}>
          <AppIcon name="mic" color={colors.text} size={18} />
        </View>
      </TouchableOpacity>

      <View style={styles.modeHeader}>
        <Text style={styles.modeLabel}>Mode</Text>
        <TouchableOpacity onPress={() => setSheetOpen(true)}>
          <Text style={styles.cardLink}>Change</Text>
        </TouchableOpacity>
      </View>
      <ModeSelector value={mode} onChange={setMode} />

      <ModeSelectorSheet visible={sheetOpen} selected={mode} onSelect={setMode} onClose={() => setSheetOpen(false)} />
    </AppScreen>
  );
}

const { ForgeMindAudioRecorder } = NativeModules as {
  ForgeMindAudioRecorder?: {
    start: () => Promise<string>;
    stop: () => Promise<string>;
  };
};

async function ensureRecordPermission() {
  if (Platform.OS !== "android") return true;
  const result = await PermissionsAndroid.request(PermissionsAndroid.PERMISSIONS.RECORD_AUDIO);
  return result === PermissionsAndroid.RESULTS.GRANTED;
}

function VoiceScreen({
  mode,
  onModeChange,
  onBack,
  onResponse,
  onError
}: {
  mode: Mode;
  onModeChange: (mode: Mode) => void;
  onBack: () => void;
  onResponse: (result: Awaited<ReturnType<typeof sendVoiceMessage>>) => void;
  onError: () => void;
}) {
  const [recording, setRecording] = useState(false);
  const [status, setStatus] = useState("Tap to start");
  const [busy, setBusy] = useState(false);

  async function toggleRecording() {
    if (busy || !ForgeMindAudioRecorder) return;
    try {
      if (!recording) {
        const granted = await ensureRecordPermission();
        if (!granted) {
          setStatus("Microphone permission is needed.");
          return;
        }
        await ForgeMindAudioRecorder.start();
        setRecording(true);
        setStatus("Tap to stop");
        return;
      }

      setBusy(true);
      setStatus("Sending...");
      const path = await ForgeMindAudioRecorder.stop();
      const result = await sendVoiceMessage(path, mode);
      onResponse(result);
    } catch {
      onError();
      setStatus("Tap to try again");
    } finally {
      setRecording(false);
      setBusy(false);
    }
  }

  return (
    <AppScreen>
      <TouchableOpacity onPress={onBack}>
        <AppHeader title="Forge" leftIcon="back" rightIcon="sliders" />
      </TouchableOpacity>

      <View style={styles.voiceCenter}>
        <Text style={styles.listeningTitle}>{recording ? "Listening..." : busy ? "Sending..." : "Tap-to-Talk"}</Text>
        <TouchableOpacity onPress={toggleRecording} activeOpacity={0.86} disabled={busy}>
          <VoiceOrb active={recording} />
        </TouchableOpacity>
        <Text style={styles.tapStop}>{status}</Text>
        <Text style={styles.voiceInstruction}>Speak naturally. I’m listening.</Text>
      </View>

      <ModeSelector value={mode} onChange={onModeChange} compact />
      <VoiceRecordingState />
    </AppScreen>
  );
}

export function ResetScreen() {
  const [filter, setFilter] = useState("All");
  const filters = ["All", "Emotions", "Life Events", "Sleep", "Relationships"];
  const tools = [
    { title: "Anger Reset", description: "Release tension and cool down", duration: "3 min", icon: "anger", color: colors.danger },
    { title: "Burnout Reset", description: "Recharge your energy", duration: "4 min", icon: "burnout", color: colors.warning },
    { title: "Breakup Reset", description: "Heal and move forward", duration: "5 min", icon: "breakup", color: "#EC4899" },
    { title: "Divorce Support", description: "Navigate with strength", duration: "5–10 min", icon: "talk", color: colors.accentBright },
    { title: "Wedding Stress", description: "Stay calm during big moments", duration: "3 min", icon: "work", color: "#EAB308" },
    { title: "Sleep Reset", description: "Quiet your mind for deep sleep", duration: "3 min", icon: "sleep", color: colors.purple },
    { title: "Confidence Boost", description: "Rebuild your inner strength", duration: "", icon: "support", color: colors.success },
    { title: "Family Conflict", description: "Handle tough conversations", duration: "", icon: "relationship", color: "#F59E0B" }
  ] as const;

  return (
    <AppScreen>
      <AppHeader title="Reset" rightIcon="info" />
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.filterRow}>
        {filters.map((item) => (
          <TouchableOpacity key={item} style={[styles.filterChip, filter === item && styles.filterChipActive]} onPress={() => setFilter(item)}>
            <Text style={[styles.filterText, filter === item && styles.filterTextActive]}>{item}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>
      <View style={styles.resetGrid}>
        {tools.map((tool) => (
          <ResetToolCard key={tool.title} title={tool.title} description={tool.description} duration={tool.duration} icon={tool.icon} color={tool.color} />
        ))}
      </View>
    </AppScreen>
  );
}

export function ProgressScreen() {
  return (
    <AppScreen>
      <AppHeader title="Progress" rightIcon="info" />
      <Card style={styles.progressThemeCard}>
        <View style={styles.progressTitleRow}>
          <Text style={styles.sectionTitle}>This week’s themes</Text>
          <Text style={styles.viewAllText}>View all</Text>
        </View>
        <View style={styles.progressStack}>
          <ProgressBar label="Work pressure" value={82} tone="High" color={colors.danger} icon="work" iconColor="#EAB308" />
          <ProgressBar label="Relationship stress" value={60} tone="Medium" color={colors.warning} icon="relationship" />
          <ProgressBar label="Sleep" value={60} tone="Medium" color={colors.purple} icon="sleep" />
        </View>
      </Card>
      <Card>
        <Text style={styles.cardLabel}>Pattern</Text>
        <Text style={styles.progressCardText}>Sunday nights seem harder for you. You often feel more stressed.</Text>
        <Text style={styles.cardLink}>View pattern →</Text>
      </Card>
      <Card>
        <Text style={styles.cardLabel}>Wins</Text>
        <Text style={styles.progressCardText}>You paused before reacting 3 times this week.</Text>
        <Text style={styles.winText}>Keep it up! 👍</Text>
      </Card>
    </AppScreen>
  );
}

export function ProfileScreen() {
  return (
    <AppScreen>
      <View style={styles.profileHeader}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>F</Text>
        </View>
        <View style={styles.profileCopy}>
          <Text style={styles.profileName}>Yeffry</Text>
          <Text style={styles.profileMeta}>Member since May 2025</Text>
          <View style={styles.premiumBadge}>
            <Text style={styles.premiumText}>Premium</Text>
          </View>
        </View>
        <TouchableOpacity style={styles.iconCircle}>
          <AppIcon name="settings" size={20} />
        </TouchableOpacity>
      </View>

      <Card>
        <Text style={styles.sectionTitle}>Your privacy, your control</Text>
        <SettingsRow label="Memory controls" icon="memory" />
        <SettingsRow label="Delete my data" icon="trash" />
        <SettingsRow label="Export my data" icon="export" />
        <SettingsRow label="Privacy settings" icon="privacy" />
      </Card>

      <Card>
        <Text style={styles.sectionTitle}>Preferences</Text>
        <SettingsRow label="AI tone" value="Calm & Grounded" icon="tone" />
        <SettingsRow label="Notifications" icon="notification" />
        <SettingsRow label="Appearance" value="Dark" icon="appearance" />
      </Card>

      <Card>
        <Text style={styles.sectionTitle}>Support</Text>
        <SettingsRow label="Emergency resources" icon="support" />
      </Card>
    </AppScreen>
  );
}

const styles = StyleSheet.create({
  onboardingHero: {
    alignItems: "center",
    gap: spacing.sm,
    paddingTop: spacing.lg,
    paddingBottom: spacing.sm
  },
  onboardingMark: {
    width: 76,
    height: 76,
    borderRadius: 38,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.accent,
    borderColor: colors.accentBright,
    borderWidth: 1
  },
  onboardingMarkText: {
    color: colors.text,
    fontSize: 34,
    fontWeight: "800"
  },
  onboardingTitle: {
    color: colors.text,
    fontSize: 28,
    lineHeight: 34,
    fontWeight: "800"
  },
  onboardingCopy: {
    color: colors.secondaryText,
    maxWidth: 310,
    textAlign: "center",
    fontSize: 15,
    lineHeight: 22
  },
  onboardingSection: {
    gap: spacing.md
  },
  selectableGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm
  },
  selectableChip: {
    minHeight: 42,
    maxWidth: "100%",
    borderRadius: radii.pill,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    paddingHorizontal: 14
  },
  selectableChipWide: {
    width: "100%"
  },
  selectableChipActive: {
    backgroundColor: colors.accent,
    borderColor: colors.accentBright
  },
  selectableChipText: {
    color: colors.secondaryText,
    fontSize: 14,
    fontWeight: "700"
  },
  selectableChipTextActive: {
    color: colors.text
  },
  primaryButton: {
    minHeight: 54,
    borderRadius: radii.pill,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.accentBright,
    marginTop: spacing.sm
  },
  primaryButtonDisabled: {
    opacity: 0.5
  },
  primaryButtonText: {
    color: colors.text,
    fontSize: 16,
    fontWeight: "800"
  },
  homeHeader: {
    flexDirection: "row",
    alignItems: "flex-start",
    justifyContent: "space-between",
    gap: spacing.md
  },
  greeting: {
    color: colors.text,
    fontSize: 22,
    lineHeight: 28,
    fontWeight: "700"
  },
  heroQuestion: {
    maxWidth: 245,
    color: colors.secondaryText,
    fontSize: 15,
    lineHeight: 21,
    marginTop: 5
  },
  iconCircle: {
    width: 42,
    height: 42,
    borderRadius: 21,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1
  },
  sectionGap: {
    gap: spacing.md
  },
  sectionTitle: {
    color: colors.text,
    fontSize: 17,
    fontWeight: "700"
  },
  quickRow: {
    gap: 8,
    paddingRight: spacing.md
  },
  twoColumn: {
    flexDirection: "row",
    gap: spacing.md
  },
  smallCard: {
    flex: 1,
    minHeight: 114
  },
  cardLabel: {
    color: colors.accentBright,
    fontSize: 14,
    fontWeight: "700",
    marginBottom: 8
  },
  cardText: {
    color: colors.text,
    fontSize: 14,
    lineHeight: 20
  },
  cardLink: {
    color: colors.accentBright,
    fontSize: 13,
    fontWeight: "700",
    marginTop: spacing.md
  },
  chatStack: {
    gap: spacing.md
  },
  suggestionRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm
  },
  suggestionChip: {
    borderRadius: radii.pill,
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    paddingVertical: 8,
    paddingHorizontal: 11
  },
  suggestionText: {
    color: colors.secondaryText,
    fontSize: 13,
    fontWeight: "700"
  },
  errorText: {
    color: colors.danger,
    fontSize: 13,
    lineHeight: 18
  },
  modeHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between"
  },
  modeLabel: {
    color: colors.text,
    fontSize: 15,
    fontWeight: "700"
  },
  voicePreview: {
    minHeight: 66,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    borderRadius: 16,
    backgroundColor: colors.elevated,
    borderColor: colors.border,
    borderWidth: 1,
    padding: 14
  },
  voiceTitle: {
    color: colors.text,
    fontSize: 15,
    fontWeight: "700"
  },
  voiceCopy: {
    color: colors.secondaryText,
    fontSize: 13,
    lineHeight: 18,
    marginTop: 5
  },
  smallMic: {
    width: 38,
    height: 38,
    borderRadius: 19,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.warning
  },
  voiceStates: {
    gap: spacing.md
  },
  voiceCenter: {
    minHeight: 340,
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.md
  },
  listeningTitle: {
    color: colors.text,
    fontSize: 24,
    fontWeight: "700"
  },
  tapStop: {
    color: colors.text,
    fontSize: 14,
    fontWeight: "700"
  },
  voiceInstruction: {
    color: colors.secondaryText,
    fontSize: 13
  },
  filterRow: {
    gap: spacing.sm,
    paddingRight: spacing.lg
  },
  filterChip: {
    minHeight: 42,
    borderRadius: radii.pill,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    paddingHorizontal: 18
  },
  filterChipActive: {
    backgroundColor: colors.accent
  },
  filterText: {
    color: colors.secondaryText,
    fontSize: 15,
    fontWeight: "700"
  },
  filterTextActive: {
    color: colors.text
  },
  resetGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "space-between",
    rowGap: spacing.md
  },
  progressStack: {
    gap: 18,
    marginTop: 16
  },
  progressThemeCard: {
    paddingVertical: 16
  },
  progressTitleRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between"
  },
  viewAllText: {
    color: colors.accentBright,
    fontSize: 14,
    fontWeight: "600"
  },
  progressCardText: {
    color: colors.secondaryText,
    fontSize: 14,
    lineHeight: 20
  },
  winText: {
    color: colors.success,
    fontSize: 15,
    fontWeight: "700",
    marginTop: spacing.md
  },
  profileHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md
  },
  avatar: {
    width: 70,
    height: 70,
    borderRadius: 35,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.accent
  },
  avatarText: {
    color: colors.text,
    fontSize: 34,
    fontWeight: "800"
  },
  profileCopy: {
    flex: 1,
    gap: 4
  },
  profileName: {
    color: colors.text,
    fontSize: 22,
    fontWeight: "700"
  },
  profileMeta: {
    color: colors.secondaryText,
    fontSize: 14
  },
  premiumBadge: {
    alignSelf: "flex-start",
    borderRadius: radii.pill,
    backgroundColor: colors.purple,
    paddingVertical: 5,
    paddingHorizontal: 10,
    marginTop: 4
  },
  premiumText: {
    color: colors.text,
    fontSize: 13,
    fontWeight: "800"
  }
});
