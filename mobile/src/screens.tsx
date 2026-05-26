import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  Animated,
  BackHandler,
  Easing,
  KeyboardAvoidingView,
  NativeModules,
  PermissionsAndroid,
  Platform,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View
} from "react-native";
import { useFocusEffect, useNavigation } from "@react-navigation/native";

import {
  AppHeader,
  AppIcon,
  AppScreen,
  Card,
  ChatBubble,
  GradientCard,
  MessageInput,
  Mode,
  ProgressBar,
  QuickActionCard,
  ResetToolCard,
  SettingsRow
} from "./components";
import {
  archiveMemories,
  completeResetSession,
  createVoiceWebSocket,
  createMoodCheckin,
  createResetSession,
  deleteUserData,
  DEMO_USER_ID,
  exportUserData,
  fetchProgressSummary,
  generateReplySuggestions,
  sendChatMessage,
  type ChatHistoryItem,
  type ForgeChatResponse,
  type ProgressSummary,
  type VoiceSocketMessage
} from "./api";
import { colors, radii, spacing } from "./design";
import { consumePendingTalkMode, loadLastTalkMode, saveLastTalkMode, savePendingTalkMode, type OnboardingPreferences } from "./preferences";

const goalOptions = ["Think clearer", "Feel less overwhelmed", "Handle anger", "Sleep better"];
const stressOptions = ["Work pressure", "Relationship stress", "Loneliness", "Family conflict", "Dating stress", "Burnout"];
const communicationOptions = ["Direct and practical", "Calm and reflective", "Short and focused"];
const supportOptions = ["Vent first", "Advice when ready", "Calm me down", "Help me find clarity"];
const onboardingStepCount = 4;
const maxVoiceRecordingMs = 60_000;
const voiceSilenceMs = 1_000;
const voicePreferredSegmentMinMs = 3_000;
const voicePreferredSegmentMaxMs = 8_000;
const voiceMaxSegmentMs = 12_000;
const voiceAmplitudeThreshold = 900;
const checkinTimeoutMs = 11_000;

type TalkMessage = {
  id: string;
  role: "forge" | "user";
  text: string;
  createdAt: number;
};

function toggleSelection(values: string[], value: string) {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
}

export function OnboardingScreen({ onComplete }: { onComplete: (preferences: OnboardingPreferences) => Promise<void> }) {
  const [goals, setGoals] = useState<string[]>(["Think clearer"]);
  const [stressCategories, setStressCategories] = useState<string[]>(["Work pressure"]);
  const [communicationPreference, setCommunicationPreference] = useState(communicationOptions[0]);
  const [supportPreference, setSupportPreference] = useState(supportOptions[0]);
  const [saving, setSaving] = useState(false);
  const [showValidation, setShowValidation] = useState(false);
  const [step, setStep] = useState(0);

  const canContinue = goals.length > 0 && stressCategories.length > 0 && communicationPreference && supportPreference;
  const lastStep = step === onboardingStepCount - 1;
  const currentStepValid =
    (step === 0 && goals.length > 0) ||
    (step === 1 && stressCategories.length > 0) ||
    (step === 2 && Boolean(communicationPreference)) ||
    (step === 3 && Boolean(supportPreference));

  function continueStep() {
    if (!currentStepValid) {
      setShowValidation(true);
      return;
    }
    setShowValidation(false);
    setStep((current) => Math.min(current + 1, onboardingStepCount - 1));
  }

  function backStep() {
    setShowValidation(false);
    setStep((current) => Math.max(current - 1, 0));
  }

  async function submit() {
    if (!currentStepValid || !canContinue || saving) {
      setShowValidation(true);
      return;
    }
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

      <Text style={styles.onboardingStepText}>
        Step {step + 1} of {onboardingStepCount}
      </Text>

      {step === 0 ? (
        <OnboardingSection title="What do you want help with?" error={showValidation && goals.length === 0 ? "Choose at least one goal." : undefined}>
          <SelectableGrid options={goalOptions} selected={goals} onToggle={(item) => setGoals((current) => toggleSelection(current, item))} />
        </OnboardingSection>
      ) : null}

      {step === 1 ? (
        <OnboardingSection
          title="What has been taking space lately?"
          error={showValidation && stressCategories.length === 0 ? "Choose at least one stress area." : undefined}
        >
          <SelectableGrid
            options={stressOptions}
            selected={stressCategories}
            onToggle={(item) => setStressCategories((current) => toggleSelection(current, item))}
          />
        </OnboardingSection>
      ) : null}

      {step === 2 ? (
        <OnboardingSection title="How should Forge talk with you?" error={showValidation && !communicationPreference ? "Choose a communication style." : undefined}>
          <SelectableGrid options={communicationOptions} selected={[communicationPreference]} onToggle={setCommunicationPreference} single />
        </OnboardingSection>
      ) : null}

      {step === 3 ? (
        <OnboardingSection title="What support should come first?" error={showValidation && !supportPreference ? "Choose a support preference." : undefined}>
          <SelectableGrid options={supportOptions} selected={[supportPreference]} onToggle={setSupportPreference} single />
        </OnboardingSection>
      ) : null}

      <View style={styles.onboardingActions}>
        <TouchableOpacity
          style={[styles.secondaryButton, step === 0 && styles.secondaryButtonDisabled]}
          onPress={backStep}
          activeOpacity={0.86}
          disabled={step === 0}
        >
          <Text style={[styles.secondaryButtonText, step === 0 && styles.secondaryButtonTextDisabled]}>Back</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.primaryButton, !currentStepValid && styles.primaryButtonDisabled, styles.onboardingActionPrimary]}
          onPress={lastStep ? submit : continueStep}
          activeOpacity={0.86}
        >
          <Text style={styles.primaryButtonText}>{saving ? "Saving..." : lastStep ? "Start with Forge" : "Continue"}</Text>
        </TouchableOpacity>
      </View>
    </AppScreen>
  );
}

function OnboardingSection({ title, children, error }: { title: string; children: React.ReactNode; error?: string }) {
  return (
    <Card style={styles.onboardingSection}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {children}
      {error ? <Text style={styles.validationText}>{error}</Text> : null}
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
  const [checkinStatus, setCheckinStatus] = useState<string | null>(null);
  const [savingCheckin, setSavingCheckin] = useState(false);
  const checkinRequestIdRef = useRef(0);
  const navigation = useNavigation();

  async function submitCheckin(label: string, intensity: number) {
    if (savingCheckin) return;
    const requestId = checkinRequestIdRef.current + 1;
    checkinRequestIdRef.current = requestId;
    setSavingCheckin(true);
    const statusTimer = setTimeout(() => {
      if (checkinRequestIdRef.current === requestId) {
        setCheckinStatus("Still trying to sync check-in...");
      }
    }, 4_000);
    const stopTimer = setTimeout(() => {
      if (checkinRequestIdRef.current === requestId) {
        setCheckinStatus("Check-in could not sync. Please try again.");
        setSavingCheckin(false);
      }
    }, checkinTimeoutMs + 1_000);
    setCheckinStatus("Saving check-in...");
    try {
      await withTimeout(createMoodCheckin(label, intensity), checkinTimeoutMs);
      if (checkinRequestIdRef.current !== requestId) return;
      const talkMode = modeForCheckin(label);
      savePendingTalkMode(talkMode).catch(() => undefined);
      setCheckinStatus(`${checkinFeedback(label)} Talk mode set to ${talkMode}.`);
    } catch {
      if (checkinRequestIdRef.current === requestId) {
        setCheckinStatus("Check-in could not sync. Please try again.");
      }
    } finally {
      clearTimeout(statusTimer);
      clearTimeout(stopTimer);
      if (checkinRequestIdRef.current === requestId) {
        setSavingCheckin(false);
      }
    }
  }

  return (
    <AppScreen>
      <View style={styles.homeHeader}>
        <View>
          <Text style={styles.greeting}>Good evening, Yeffry</Text>
          <Text style={styles.heroQuestion}>What’s taking most of your headspace right now?</Text>
        </View>
        <TouchableOpacity style={styles.iconCircle} onPress={() => setCheckinStatus("Notifications are quiet for now.")}>
          <AppIcon name="bell" size={20} />
        </TouchableOpacity>
      </View>

      <GradientCard title="Talk to Forge" subtitle="I’m here. Let’s talk." cta="→" onPress={() => navigation.navigate("Talk" as never)} />

      <View style={styles.sectionGap}>
        <Text style={styles.sectionTitle}>Quick check-in</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.quickRow}>
          <QuickActionCard title="Angry" icon="anger" color={colors.danger} onPress={() => submitCheckin("Angry", 7)} disabled={savingCheckin} />
          <QuickActionCard title="Burned out" icon="burnout" color={colors.warning} onPress={() => submitCheckin("Burned out", 8)} disabled={savingCheckin} />
          <QuickActionCard title="Lonely" icon="lonely" color={colors.purple} onPress={() => submitCheckin("Lonely", 6)} disabled={savingCheckin} />
          <QuickActionCard title="Breakup" icon="breakup" color="#EC4899" onPress={() => submitCheckin("Breakup", 7)} disabled={savingCheckin} />
        </ScrollView>
        {checkinStatus ? <Text style={styles.syncStatus}>{checkinStatus}</Text> : null}
      </View>

      <View style={styles.twoColumn}>
        <Card style={styles.smallCard} onPress={() => navigation.navigate("Progress" as never)}>
          <Text style={styles.cardLabel}>Insight</Text>
          <Text style={styles.cardText}>You’ve mentioned work stress several times this week.</Text>
          <Text style={styles.cardLink}>View details →</Text>
        </Card>
        <Card style={styles.smallCard} onPress={() => navigation.navigate("Reset" as never)}>
          <Text style={styles.cardLabel}>Reset</Text>
          <Text style={styles.cardText}>2-minute reset to clear your mind.</Text>
          <Text style={styles.cardLink}>Start →</Text>
        </Card>
      </View>
    </AppScreen>
  );
}

function checkinFeedback(label: string) {
  const feedback: Record<string, string> = {
    Angry: "Angry check-in saved. Take 20 seconds before you respond to anything.",
    "Burned out": "Burned out check-in saved. Pick one thing to put down for now.",
    Lonely: "Lonely check-in saved. Reach for one honest connection today, even a short one.",
    Breakup: "Breakup check-in saved. Give yourself space before chasing closure."
  };
  return feedback[label] ?? `${label} check-in saved.`;
}

function modeForCheckin(label: string): Mode {
  const modes: Record<string, Mode> = {
    Angry: "Calm",
    "Burned out": "Vent",
    Lonely: "Vent",
    Breakup: "Calm"
  };
  return modes[label] ?? "Clarity";
}

function withTimeout<T>(promise: Promise<T>, timeoutMs: number): Promise<T> {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error("Timed out")), timeoutMs);
    promise
      .then(resolve)
      .catch(reject)
      .finally(() => clearTimeout(timeout));
  });
}

export function TalkScreen() {
  const initialForgeMessage = { id: "m1", role: "forge" as const, text: "What can I help you with right now?", createdAt: Date.now() };
  const [mode, setMode] = useState<Mode>("Clarity");
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [voiceRecording, setVoiceRecording] = useState(false);
  const [inputFocused, setInputFocused] = useState(false);
  const [speakingMessageId, setSpeakingMessageId] = useState<string | null>(null);
  const [readAloudFollowups, setReadAloudFollowups] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigation = useNavigation();
  const scrollViewRef = useRef<ScrollView | null>(null);
  const recordingRef = useRef(false);
  const startedAtRef = useRef<number | null>(null);
  const stoppingRef = useRef(false);
  const maxRecordingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const vadTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const speechTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const speechQueueRef = useRef(Promise.resolve());
  const speechQueueTokenRef = useRef(0);
  const voiceSocketRef = useRef<WebSocket | null>(null);
  const chunkIndexRef = useRef(0);
  const chunkStartedAtRef = useRef<number | null>(null);
  const lastVoiceAtRef = useRef<number | null>(null);
  const voiceDetectedRef = useRef(false);
  const chunkVoiceDetectedRef = useRef(false);
  const chunkRotatingRef = useRef(false);
  const pendingChunkUploadsRef = useRef(0);
  const voiceTranscriptRef = useRef("");
  const forgeStreamMessageIdRef = useRef<string | null>(null);
  const forgeStreamPartsRef = useRef<{ bodyChunks: string[]; question: string }>({
    bodyChunks: [],
    question: ""
  });
  const queuedTtsAudioKeysRef = useRef<Set<string>>(new Set());
  const suggestionRequestIdRef = useRef(0);
  const [messages, setMessages] = useState<TalkMessage[]>([initialForgeMessage]);
  const [chatClock, setChatClock] = useState(Date.now());
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const conversationStarted = messages.some((message) => message.role === "user");

  function clearTalk() {
    ForgeMindTts?.stop?.().catch(() => undefined);
    speechQueueTokenRef.current += 1;
    speechQueueRef.current = Promise.resolve();
    if (recordingRef.current && ForgeMindAudioRecorder) {
      ForgeMindAudioRecorder.cancel().catch(() => undefined);
      recordingRef.current = false;
      setVoiceRecording(false);
    }
    resetVoiceSessionState();
    if (speechTimerRef.current) {
      clearTimeout(speechTimerRef.current);
      speechTimerRef.current = null;
    }
    setSpeakingMessageId(null);
    setReadAloudFollowups(false);
    setDraft("");
    setError(null);
    suggestionRequestIdRef.current += 1;
    setSuggestions([]);
    setMessages([{ ...initialForgeMessage, id: `m1-${Date.now()}`, createdAt: Date.now() }]);
  }

  async function updateSuggestionsFromConversation(response: string, userMessage: string, history: ChatHistoryItem[] = buildChatHistory(messages)) {
    const requestId = suggestionRequestIdRef.current + 1;
    suggestionRequestIdRef.current = requestId;
    try {
      const generated = await generateReplySuggestions(userMessage, response, mode, history);
      if (suggestionRequestIdRef.current === requestId) {
        setSuggestions(generated.length ? generated : buildReplySuggestions(response, userMessage, mode));
      }
    } catch {
      if (suggestionRequestIdRef.current === requestId) {
        setSuggestions(buildReplySuggestions(response, userMessage, mode));
      }
    }
  }

  function scrollChatToBottom(animated = true) {
    requestAnimationFrame(() => {
      scrollViewRef.current?.scrollToEnd({ animated });
    });
  }

  function speakForgeMessage(messageId: string, text: string, segments = splitSpeechSegments(text)) {
    if (speechTimerRef.current) {
      clearTimeout(speechTimerRef.current);
    }
    setReadAloudFollowups(true);
    setSpeakingMessageId(messageId);
    ForgeMindTts?.stop?.().catch(() => undefined);
    speechQueueTokenRef.current += 1;
    speechQueueRef.current = Promise.resolve();
    if (segments.length > 1 && ForgeMindTts?.speakSegments) {
      ForgeMindTts.speakSegments(segments).catch(() => undefined);
    } else {
      ForgeMindTts?.speak(text).catch(() => undefined);
    }
    const estimatedDuration = Math.min(14_000, Math.max(2_400, text.length * 62));
    speechTimerRef.current = setTimeout(() => {
      setSpeakingMessageId(null);
      speechTimerRef.current = null;
    }, estimatedDuration);
  }

  function stopReadAloud() {
    if (speechTimerRef.current) {
      clearTimeout(speechTimerRef.current);
      speechTimerRef.current = null;
    }
    setSpeakingMessageId(null);
    ForgeMindTts?.stop?.().catch(() => undefined);
    speechQueueTokenRef.current += 1;
    speechQueueRef.current = Promise.resolve();
  }

  function toggleForgeSpeech(messageId: string, text: string) {
    if (speakingMessageId === messageId) {
      stopReadAloud();
      return;
    }
    speakForgeMessage(messageId, text);
  }

  const leaveTalk = useCallback(() => {
    stopReadAloud();
    if (recordingRef.current && ForgeMindAudioRecorder) {
      ForgeMindAudioRecorder.cancel().catch(() => undefined);
      recordingRef.current = false;
      setVoiceRecording(false);
    }
    clearVoiceTimers();
    voiceSocketRef.current?.close();
    voiceSocketRef.current = null;

    if (navigation.canGoBack()) {
      navigation.goBack();
    } else {
      navigation.navigate("Home" as never);
    }
  }, [navigation]);

  function queueForgeSpeech(messageId: string, text: string) {
    if (!text.trim()) return;
    if (speechTimerRef.current) {
      clearTimeout(speechTimerRef.current);
    }
    setReadAloudFollowups(true);
    setSpeakingMessageId(messageId);
    const queueToken = speechQueueTokenRef.current;
    speechQueueRef.current = speechQueueRef.current
      .catch(() => undefined)
      .then(() => {
        if (speechQueueTokenRef.current !== queueToken) return undefined;
        if (ForgeMindTts?.enqueue) {
          return ForgeMindTts.enqueue(text);
        }
        return ForgeMindTts?.speak(text);
      })
      .then(() => undefined);
    const estimatedDuration = Math.min(14_000, Math.max(2_400, text.length * 62));
    speechTimerRef.current = setTimeout(() => {
      setSpeakingMessageId(null);
      speechTimerRef.current = null;
    }, estimatedDuration);
  }

  function queueForgeAudio(messageId: string, text: string, audioBase64: string, format = "mp3", cacheKey = `${messageId}-${text}`) {
    if (!audioBase64.trim()) return;
    if (speechTimerRef.current) {
      clearTimeout(speechTimerRef.current);
    }
    setReadAloudFollowups(true);
    setSpeakingMessageId(messageId);
    const queueToken = speechQueueTokenRef.current;
    speechQueueRef.current = speechQueueRef.current
      .catch(() => undefined)
      .then(() => {
        if (speechQueueTokenRef.current !== queueToken) return undefined;
        if (ForgeMindTts?.enqueueAudioBase64) {
          return ForgeMindTts.enqueueAudioBase64(audioBase64, format, cacheKey);
        }
        return ForgeMindTts?.enqueue?.(text);
      })
      .then(() => undefined);
    const estimatedDuration = Math.min(14_000, Math.max(2_400, text.length * 62));
    speechTimerRef.current = setTimeout(() => {
      setSpeakingMessageId(null);
      speechTimerRef.current = null;
    }, estimatedDuration);
  }

  function clearVoiceTimers() {
    if (maxRecordingTimerRef.current) {
      clearTimeout(maxRecordingTimerRef.current);
      maxRecordingTimerRef.current = null;
    }
    if (vadTimerRef.current) {
      clearInterval(vadTimerRef.current);
      vadTimerRef.current = null;
    }
  }

  function resetVoiceSessionState() {
    clearVoiceTimers();
    voiceSocketRef.current?.close();
    voiceSocketRef.current = null;
    pendingChunkUploadsRef.current = 0;
    chunkRotatingRef.current = false;
    voiceTranscriptRef.current = "";
    forgeStreamMessageIdRef.current = null;
    forgeStreamPartsRef.current = { bodyChunks: [], question: "" };
    queuedTtsAudioKeysRef.current.clear();
    chunkIndexRef.current = 0;
    chunkStartedAtRef.current = null;
    lastVoiceAtRef.current = null;
    voiceDetectedRef.current = false;
    chunkVoiceDetectedRef.current = false;
  }

  async function submitMessage(text = draft, speakResponse = false) {
    const trimmed = text.trim();
    if (!trimmed || sending) return;
    const history = buildChatHistory(messages);
    setDraft("");
    setError(null);
    suggestionRequestIdRef.current += 1;
    setSuggestions([]);
    setSending(true);
    setMessages((current) => [...current, { id: `user-${Date.now()}`, role: "user", text: trimmed, createdAt: Date.now() }]);
    try {
      const result = await sendChatMessage(trimmed, mode, history);
      const messageId = `forge-${Date.now()}`;
      setMessages((current) => [...current, { id: messageId, role: "forge", text: result.response, createdAt: Date.now() }]);
      updateSuggestionsFromConversation(result.response, trimmed, [
        ...history,
        { role: "user", text: trimmed },
        { role: "forge", text: result.response }
      ]).catch(() => undefined);
      if (speakResponse) {
        speakForgeMessage(messageId, result.response, responseSpeechSegments(result));
      }
    } catch {
      setError("Forge is unable to connect. Please try again.");
    } finally {
      setSending(false);
    }
  }

  function appendVoiceTranscript(transcript: string) {
    setMessages((current) => [...current, { id: `voice-${Date.now()}`, role: "user", text: transcript, createdAt: Date.now() }]);
  }

  useEffect(() => {
    return () => {
      if (speechTimerRef.current) {
        clearTimeout(speechTimerRef.current);
      }
      clearVoiceTimers();
      voiceSocketRef.current?.close();
      if (recordingRef.current && ForgeMindAudioRecorder) {
        ForgeMindAudioRecorder.cancel().catch(() => undefined);
      }
    };
  }, []);

  useEffect(() => {
    const timer = setInterval(() => setChatClock(Date.now()), 60_000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    navigation.setOptions({ tabBarStyle: { display: "none" } });
  }, [navigation]);

  useFocusEffect(
    useCallback(() => {
      const subscription = BackHandler.addEventListener("hardwareBackPress", () => {
        leaveTalk();
        return true;
      });
      return () => subscription.remove();
    }, [leaveTalk])
  );

  useFocusEffect(
    useCallback(() => {
      let active = true;
      async function syncTalkMode() {
        const pendingMode = await consumePendingTalkMode();
        if (!active) return;
        if (pendingMode) {
          setMode(pendingMode);
          await saveLastTalkMode(pendingMode);
          return;
        }
        const lastMode = await loadLastTalkMode();
        if (active && lastMode) {
          setMode(lastMode);
        }
      }
      syncTalkMode().catch(() => undefined);
      return () => {
        active = false;
      };
    }, [])
  );

  useEffect(() => {
    scrollChatToBottom();
  }, [messages.length, sending]);

  async function startVoiceMessage() {
    if (sending || recordingRef.current) return;
    stopReadAloud();
    setError(null);
    if (!ForgeMindAudioRecorder) {
      setError("Voice recorder is not available. Reinstall the Android app and try again.");
      return;
    }
    try {
      const granted = await ensureRecordPermission();
      if (!granted) {
        setError("Microphone permission is needed.");
        return;
      }
      const history = buildChatHistory(messages);
      voiceTranscriptRef.current = "";
      forgeStreamMessageIdRef.current = null;
      forgeStreamPartsRef.current = { bodyChunks: [], question: "" };
      queuedTtsAudioKeysRef.current.clear();
      chunkIndexRef.current = 0;
      pendingChunkUploadsRef.current = 0;
      chunkRotatingRef.current = false;
      voiceDetectedRef.current = false;
      chunkVoiceDetectedRef.current = false;

      let socket = voiceSocketRef.current;
      const startPayload = {
        type: "start",
        user_id: DEMO_USER_ID,
        mode: mode.toLowerCase(),
        history
      };
      if (!socket || socket.readyState === WebSocket.CLOSING || socket.readyState === WebSocket.CLOSED) {
        socket = createVoiceWebSocket();
        voiceSocketRef.current = socket;
        socket.onopen = () => {
          socket?.send(JSON.stringify(startPayload));
        };
        socket.onmessage = (event) => handleVoiceSocketMessage(event.data);
        socket.onerror = () => {
          setError("Voice is unable to connect. Please try again.");
        };
        socket.onclose = () => {
          if (recordingRef.current) {
            setError("Voice connection closed. Tap again to retry.");
          }
        };
      } else if (socket.readyState === WebSocket.OPEN) {
        socket.send(
          JSON.stringify(startPayload)
        );
      }

      await ForgeMindAudioRecorder.cancel().catch(() => undefined);
      await ForgeMindAudioRecorder.start();
      recordingRef.current = true;
      startedAtRef.current = Date.now();
      chunkStartedAtRef.current = Date.now();
      lastVoiceAtRef.current = Date.now();
      setVoiceRecording(true);
      startVadLoop();
      maxRecordingTimerRef.current = setTimeout(() => {
        stopVoiceMessage().catch(() => undefined);
      }, maxVoiceRecordingMs);
    } catch (voiceError) {
      clearVoiceTimers();
      voiceSocketRef.current?.close();
      voiceSocketRef.current = null;
      recordingRef.current = false;
      startedAtRef.current = null;
      setVoiceRecording(false);
      setError(voiceErrorMessage(voiceError));
    }
  }

  function handleVoiceSocketMessage(data: string) {
    let message: VoiceSocketMessage;
    try {
      message = JSON.parse(data) as VoiceSocketMessage;
    } catch {
      setError("Voice is unable to connect. Please try again.");
      return;
    }

    if (message.type === "error") {
      setError(voiceErrorMessage(new Error(message.detail || "Voice chat failed")));
      setTranscribing(false);
      setSending(false);
      return;
    }

    if (message.type === "final_transcript") {
      voiceTranscriptRef.current = message.text;
      appendVoiceTranscript(message.text);
      setTranscribing(false);
      setSending(true);
      return;
    }

    if (message.type === "response_part") {
      setSending(false);
      const partText = message.text.trim();
      if (!partText) return;

      const messageId = ensureForgeStreamMessageId();
      applyForgeStreamPart(message.part, partText, message.chunk_index ?? 0);
      updateForgeStreamMessage(messageId);
      if (message.part === "question") {
        updateSuggestionsFromConversation(partText, voiceTranscriptRef.current).catch(() => undefined);
      }
      return;
    }

    if (message.type === "tts_audio") {
      const text = message.text.trim();
      if (!text) return;
      const messageId = ensureForgeStreamMessageId();
      const chunkIndex = message.chunk_index ?? 0;
      applyForgeStreamPart(message.part, text, chunkIndex);
      updateForgeStreamMessage(messageId);
      const audioKey = `${message.part}-${chunkIndex}-${text}`;
      if (queuedTtsAudioKeysRef.current.has(audioKey)) return;
      queuedTtsAudioKeysRef.current.add(audioKey);
      queueForgeAudio(messageId, text, message.audio_base64, message.format || "mp3", audioKey);
      return;
    }

    if (message.type === "response") {
      const result = message.payload;
      const messageId = forgeStreamMessageIdRef.current;
      if (messageId) {
        setMessages((current) => current.map((item) => (item.id === messageId ? { ...item, text: result.response } : item)));
      } else {
        setMessages((current) => [...current, { id: `forge-${Date.now()}`, role: "forge", text: result.response, createdAt: Date.now() }]);
      }
      updateSuggestionsFromConversation(result.response, voiceTranscriptRef.current, [
        ...buildChatHistory(messages),
        { role: "user", text: voiceTranscriptRef.current },
        { role: "forge", text: result.response }
      ]).catch(() => undefined);
      return;
    }

    if (message.type === "done") {
      setTranscribing(false);
      setSending(false);
    }
  }

  function ensureForgeStreamMessageId() {
    if (!forgeStreamMessageIdRef.current) {
      forgeStreamMessageIdRef.current = `forge-${Date.now()}`;
    }
    return forgeStreamMessageIdRef.current;
  }

  function updateForgeStreamMessage(messageId: string) {
    const parts = forgeStreamPartsRef.current;
    const text = [parts.bodyChunks.filter(Boolean).join(" "), parts.question].filter(Boolean).join(" ");
    setMessages((current) => {
      const exists = current.some((item) => item.id === messageId);
      if (!exists) {
        return [...current, { id: messageId, role: "forge", text, createdAt: Date.now() }];
      }
      return current.map((item) => (item.id === messageId ? { ...item, text } : item));
    });
  }

  function applyForgeStreamPart(part: "body" | "question", text: string, chunkIndex: number) {
    const parts = forgeStreamPartsRef.current;
    if (part === "body") {
      parts.bodyChunks[chunkIndex] = text;
      return;
    }
    parts.question = text;
  }

  function startVadLoop() {
    vadTimerRef.current = setInterval(() => {
      if (!recordingRef.current || stoppingRef.current || !ForgeMindAudioRecorder?.getMaxAmplitude) return;
      ForgeMindAudioRecorder.getMaxAmplitude()
        .then((amplitude) => {
          const now = Date.now();
          if (amplitude > voiceAmplitudeThreshold) {
            voiceDetectedRef.current = true;
            chunkVoiceDetectedRef.current = true;
            lastVoiceAtRef.current = now;
            return;
          }
          const chunkStartedAt = chunkStartedAtRef.current ?? now;
          const lastVoiceAt = lastVoiceAtRef.current ?? now;
          const chunkAge = now - chunkStartedAt;
          const silenceAge = now - lastVoiceAt;
          const preferredSegmentReady =
            silenceAge >= voiceSilenceMs && chunkAge >= voicePreferredSegmentMinMs && chunkAge <= voicePreferredSegmentMaxMs;
          const longSegmentReady = silenceAge >= voiceSilenceMs && chunkAge > voicePreferredSegmentMaxMs;
          if (preferredSegmentReady || longSegmentReady || chunkAge >= voiceMaxSegmentMs) {
            rotateAndSendVoiceChunk().catch((error) => setError(voiceErrorMessage(error)));
          }
        })
        .catch(() => undefined);
    }, 250);
  }

  async function rotateAndSendVoiceChunk() {
    if (chunkRotatingRef.current || !recordingRef.current || stoppingRef.current || !ForgeMindAudioRecorder?.rotateChunk) return;
    chunkRotatingRef.current = true;
    try {
      const segmentStartedAt = chunkStartedAtRef.current ?? Date.now();
      const segmentEndedAt = Date.now();
      const hadVoice = chunkVoiceDetectedRef.current;
      const path = await ForgeMindAudioRecorder.rotateChunk();
      chunkStartedAtRef.current = Date.now();
      lastVoiceAtRef.current = Date.now();
      chunkVoiceDetectedRef.current = false;
      if (!hadVoice) {
        ForgeMindAudioRecorder.deleteFile?.(path).catch(() => undefined);
        return;
      }
      await sendVoiceChunk(path, segmentStartedAt, segmentEndedAt);
    } finally {
      chunkRotatingRef.current = false;
    }
  }

  async function sendVoiceChunk(path: string, startedAtMs: number, endedAtMs: number) {
    const socket = voiceSocketRef.current;
    if (!socket || !ForgeMindAudioRecorder?.readBase64) return;
    await waitForVoiceSocketOpen(socket);
    const index = chunkIndexRef.current;
    chunkIndexRef.current += 1;
    pendingChunkUploadsRef.current += 1;
    try {
      const audioBase64 = await ForgeMindAudioRecorder.readBase64(path);
      const sessionStartedAt = startedAtRef.current ?? startedAtMs;
      socket.send(
        JSON.stringify({
          type: "audio_chunk",
          index,
          suffix: ".m4a",
          audio_base64: audioBase64,
          started_at_ms: Math.max(0, startedAtMs - sessionStartedAt),
          ended_at_ms: Math.max(0, endedAtMs - sessionStartedAt)
        })
      );
    } finally {
      pendingChunkUploadsRef.current = Math.max(0, pendingChunkUploadsRef.current - 1);
      ForgeMindAudioRecorder?.deleteFile?.(path).catch(() => undefined);
    }
  }

  function waitForVoiceSocketOpen(socket: WebSocket): Promise<void> {
    if (socket.readyState === WebSocket.OPEN) return Promise.resolve();
    if (socket.readyState === WebSocket.CLOSING || socket.readyState === WebSocket.CLOSED) {
      return Promise.reject(new Error("Voice connection closed"));
    }
    return new Promise((resolve, reject) => {
      const startedAt = Date.now();
      const timer = setInterval(() => {
        if (socket.readyState === WebSocket.OPEN) {
          clearInterval(timer);
          resolve();
          return;
        }
        if (socket.readyState === WebSocket.CLOSING || socket.readyState === WebSocket.CLOSED || Date.now() - startedAt > 4_000) {
          clearInterval(timer);
          reject(new Error("Voice connection did not open"));
        }
      }, 80);
    });
  }

  function sendVoiceStopWhenReady() {
    const socket = voiceSocketRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) return;
    if (pendingChunkUploadsRef.current > 0) {
      setTimeout(sendVoiceStopWhenReady, 80);
      return;
    }
    socket.send(JSON.stringify({ type: "stop" }));
  }

  async function stopVoiceMessage() {
    if (sending || transcribing || stoppingRef.current || !recordingRef.current || !ForgeMindAudioRecorder) return;
    clearVoiceTimers();
    const startedAt = startedAtRef.current;
    if (startedAt && Date.now() - startedAt < 700) {
      await ForgeMindAudioRecorder.cancel().catch(() => undefined);
      voiceSocketRef.current?.close();
      voiceSocketRef.current = null;
      recordingRef.current = false;
      startedAtRef.current = null;
      setVoiceRecording(false);
      setError("Record a little longer, then tap stop.");
      return;
    }
    stoppingRef.current = true;
    setTranscribing(true);
    try {
      const segmentStartedAt = chunkStartedAtRef.current ?? Date.now();
      const segmentEndedAt = Date.now();
      const finalChunkHadVoice = chunkVoiceDetectedRef.current;
      const path = await ForgeMindAudioRecorder.stop();
      recordingRef.current = false;
      setVoiceRecording(false);
      if (!voiceDetectedRef.current) {
        ForgeMindAudioRecorder.deleteFile?.(path).catch(() => undefined);
        voiceSocketRef.current?.close();
        voiceSocketRef.current = null;
        setError("No voice is detected.");
        setTranscribing(false);
        return;
      }
      setSuggestions([]);
      if (finalChunkHadVoice) {
        await sendVoiceChunk(path, segmentStartedAt, segmentEndedAt);
      } else {
        ForgeMindAudioRecorder.deleteFile?.(path).catch(() => undefined);
      }
      startedAtRef.current = null;
      sendVoiceStopWhenReady();
    } catch (voiceError) {
      setError(voiceErrorMessage(voiceError));
      voiceSocketRef.current?.close();
      voiceSocketRef.current = null;
      setTranscribing(false);
      setSending(false);
    } finally {
      stoppingRef.current = false;
      recordingRef.current = false;
      startedAtRef.current = null;
      setVoiceRecording(false);
    }
  }

  async function toggleVoiceMessage() {
    if (voiceRecording) {
      await stopVoiceMessage();
    } else {
      await startVoiceMessage();
    }
  }

  return (
    <SafeAreaView style={styles.talkSafeArea}>
      <KeyboardAvoidingView style={styles.talkKeyboard} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <ScrollView
          ref={scrollViewRef}
          contentContainerStyle={[styles.talkScroll, inputFocused && styles.talkScrollFocused]}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
          onContentSizeChange={() => scrollChatToBottom()}
        >
          <AppHeader
            title="Forge"
            leftIcon="back"
            rightIcon="trash"
            onLeftPress={leaveTalk}
            onRightPress={clearTalk}
          />

          <View style={styles.chatStack}>
            {messages.map((message) => (
              <ChatBubble
                key={message.id}
                role={message.role}
                subtitle={message.role === "forge" ? "Forge" : "You"}
                timestamp={humanizeChatDate(message.createdAt, chatClock)}
                speaking={message.id === speakingMessageId}
                onSpeak={message.role === "forge" && conversationStarted ? () => toggleForgeSpeech(message.id, message.text) : undefined}
              >
                {message.text}
              </ChatBubble>
            ))}
            {sending ? <TalkStatusRow label="Forge is thinking" /> : null}
          </View>

          {conversationStarted && suggestions.length > 0 ? (
            <View style={styles.suggestionRow}>
              {suggestions.map((item) => (
                <TouchableOpacity key={item} style={styles.suggestionChip} onPress={() => submitMessage(item, readAloudFollowups)}>
                  <Text style={styles.suggestionText}>{item}</Text>
                </TouchableOpacity>
              ))}
            </View>
          ) : null}

          {error ? <Text style={styles.errorText}>{error}</Text> : null}
          {transcribing ? <TalkStatusRow label="Transcribing" compact /> : null}
        </ScrollView>

        <View style={[styles.chatInputDock, inputFocused && styles.chatInputDockFocused]}>
          <MessageInput
            value={draft}
            onChangeText={setDraft}
            onSubmit={() => submitMessage()}
            mode={mode}
            onModeChange={(nextMode) => {
              setMode(nextMode);
              saveLastTalkMode(nextMode).catch(() => undefined);
            }}
            onVoicePress={toggleVoiceMessage}
            onFocusChange={setInputFocused}
            voiceActive={voiceRecording}
            sendDisabled={!draft.trim()}
            disabled={(sending || transcribing) && !voiceRecording}
          />
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function TalkStatusRow({ label, compact = false }: { label: string; compact?: boolean }) {
  const pulse = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const animation = Animated.loop(
      Animated.timing(pulse, {
        toValue: 1,
        duration: 900,
        easing: Easing.inOut(Easing.ease),
        useNativeDriver: true
      })
    );
    animation.start();
    return () => animation.stop();
  }, [pulse]);

  const dots = [0, 1, 2];
  return (
    <View style={[styles.talkStatusRow, compact && styles.talkStatusRowCompact]}>
      <View style={styles.talkStatusDots}>
        {dots.map((index) => {
          const opacity = pulse.interpolate({
            inputRange: [0, 0.35, 0.7, 1],
            outputRange: index === 0 ? [0.35, 1, 0.35, 0.35] : index === 1 ? [0.35, 0.35, 1, 0.35] : [0.35, 0.35, 0.35, 1]
          });
          const scale = pulse.interpolate({
            inputRange: [0, 0.35, 0.7, 1],
            outputRange: index === 0 ? [0.8, 1.2, 0.8, 0.8] : index === 1 ? [0.8, 0.8, 1.2, 0.8] : [0.8, 0.8, 0.8, 1.2]
          });
          return <Animated.View key={index} style={[styles.talkStatusDot, { opacity, transform: [{ scale }] }]} />;
        })}
      </View>
      <Text style={styles.talkStatusText}>{label}</Text>
    </View>
  );
}

const { ForgeMindAudioRecorder } = NativeModules as {
  ForgeMindAudioRecorder?: {
    start: () => Promise<string>;
    stop: () => Promise<string>;
    cancel: () => Promise<void>;
    getMaxAmplitude?: () => Promise<number>;
    rotateChunk?: () => Promise<string>;
    readBase64?: (path: string) => Promise<string>;
    deleteFile?: (path: string) => Promise<void>;
  };
};
const { ForgeMindTts } = NativeModules as {
  ForgeMindTts?: {
    speak: (text: string) => Promise<void>;
    speakSegments?: (texts: string[]) => Promise<void>;
    enqueue?: (text: string) => Promise<void>;
    enqueueAudioBase64?: (audioBase64: string, format: string, cacheKey: string) => Promise<void>;
    stop: () => Promise<void>;
  };
};

async function ensureRecordPermission() {
  if (Platform.OS !== "android") return true;
  const result = await PermissionsAndroid.request(PermissionsAndroid.PERMISSIONS.RECORD_AUDIO);
  return result === PermissionsAndroid.RESULTS.GRANTED;
}

function voiceErrorMessage(error: unknown) {
  if (error instanceof Error && error.message) {
    if (error.message.includes("Voice transcription needs OPENAI_API_KEY")) {
      return "Voice needs OPENAI_API_KEY on the backend.";
    }
    if (error.message.includes("No speech detected")) {
      return "No voice is detected.";
    }
    return "Voice is unable to connect. Please try again.";
  }
  return "Forge is unable to process that recording. Please try again.";
}

function buildChatHistory(messages: Array<{ role: "forge" | "user"; text: string }>) {
  return messages
    .filter((message) => message.text.trim())
    .map((message) => ({ role: message.role, text: message.text }));
}

function humanizeChatDate(timestamp: number, now = Date.now()) {
  const elapsedMs = Math.max(0, now - timestamp);
  const elapsedMinutes = Math.floor(elapsedMs / 60_000);
  if (elapsedMinutes < 1) return "Just now";
  if (elapsedMinutes < 60) return `${elapsedMinutes} min ago`;

  const date = new Date(timestamp);
  const today = new Date(now);
  const yesterday = new Date(now);
  yesterday.setDate(today.getDate() - 1);
  const time = date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  if (date.toDateString() === today.toDateString()) return time;
  if (date.toDateString() === yesterday.toDateString()) return `Yesterday ${time}`;
  return date.toLocaleDateString([], { month: "short", day: "numeric" });
}

function responseSpeechSegments(response: ForgeChatResponse) {
  const parts = response.response_parts;
  if (parts?.body && parts.question) {
    return [...splitSpokenBody(parts.body), parts.question];
  }
  return splitSpeechSegments(response.response);
}

function splitSpeechSegments(text: string) {
  const normalized = text.trim();
  if (!normalized) return [];
  const questionMark = normalized.lastIndexOf("?");
  if (questionMark === -1) return [normalized];
  const questionStart = Math.max(
    normalized.lastIndexOf(".", questionMark),
    normalized.lastIndexOf("!", questionMark),
    normalized.lastIndexOf("\n", questionMark)
  ) + 1;
  const question = normalized.slice(questionStart, questionMark + 1).trim();
  const body = dropLeadingQuestionSentences(`${normalized.slice(0, questionStart)} ${normalized.slice(questionMark + 1)}`.trim());
  if (!body || question.split(/\s+/).length < 3) return splitSpokenBody(normalized);
  return [...splitSpokenBody(body), question];
}

function dropLeadingQuestionSentences(text: string) {
  let cleaned = text.trim();
  while (cleaned) {
    const questionMark = cleaned.indexOf("?");
    if (questionMark === -1) return cleaned;
    const stops = [cleaned.indexOf("."), cleaned.indexOf("!")].filter((index) => index !== -1);
    const firstStop = stops.length ? Math.min(...stops) : -1;
    if (firstStop !== -1 && firstStop < questionMark) return cleaned;
    const remainder = cleaned.slice(questionMark + 1).trim();
    if (!remainder) return text.trim();
    cleaned = remainder;
  }
  return cleaned;
}

function splitSpokenBody(text: string) {
  const sentences = text
    .split(/(?<=[.!])\s+/)
    .map((part) => part.trim())
    .filter(Boolean);
  if (sentences.length <= 1) return [text.trim()].filter(Boolean);

  const chunks: string[] = [];
  let current = "";
  for (const sentence of sentences) {
    const next = current ? `${current} ${sentence}` : sentence;
    if (next.length > 180 && current) {
      chunks.push(current);
      current = sentence;
    } else {
      current = next;
    }
  }
  if (current) chunks.push(current);
  return chunks;
}

function buildReplySuggestions(response: string, userMessage: string, mode: Mode): string[] {
  const forge = response.toLowerCase();
  const user = userMessage.toLowerCase();
  const context = `${user} ${forge}`;
  if (hasAny(forge, ["one safe next step", "next step", "one step"])) {
    return ["Give me one step", "Help me choose", "Make it simpler"];
  }
  return contextualOptions(context, {
    work: ["Work is the main thing", "I’m overloaded", "Help me prioritize"],
    relationship: ["I need clarity", "I’m replaying it", "Help me respond"],
    sleep: ["Help me shut off", "I need rest", "Keep it simple"],
    anger: ["Help me cool down", "I feel disrespected", "Stop me reacting"],
    fallback:
      mode === "Advice"
        ? ["What should I do?", "Give me one step", "Help me decide"]
        : mode === "Calm"
        ? ["Help me slow down", "I need grounding", "Stay with this"]
        : ["Say more", "Help me slow down", "What am I missing?"]
  });
}

function hasAny(text: string, terms: string[]) {
  return terms.some((term) => text.includes(term));
}

function contextualOptions(
  context: string,
  options: {
    work: string[];
    relationship: string[];
    sleep: string[];
    anger: string[];
    fallback: string[];
  }
) {
  if (hasAny(context, ["work", "job", "boss", "deadline", "pressure", "burnout", "meeting"])) return options.work;
  if (hasAny(context, ["relationship", "breakup", "ex", "dating", "wife", "fiance", "girlfriend", "partner"])) return options.relationship;
  if (hasAny(context, ["sleep", "tired", "exhausted", "night", "insomnia"])) return options.sleep;
  if (hasAny(context, ["angry", "anger", "rage", "react", "disrespect"])) return options.anger;
  return options.fallback;
}

export function ResetScreen() {
  const [filter, setFilter] = useState("All");
  const [status, setStatus] = useState<string | null>(null);
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

  async function startReset(title: string) {
    setStatus(`Starting ${title}...`);
    try {
      const session = await createResetSession(title);
      await completeResetSession(session.id);
      setStatus(`${title} completed`);
    } catch {
      setStatus("Reset could not sync. Please try again.");
    }
  }

  return (
    <AppScreen>
      <AppHeader title="Reset" rightIcon="info" onRightPress={() => setStatus("Choose a reset tool to save and complete a short reset session.")} />
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.filterRow}>
        {filters.map((item) => (
          <TouchableOpacity key={item} style={[styles.filterChip, filter === item && styles.filterChipActive]} onPress={() => setFilter(item)}>
            <Text style={[styles.filterText, filter === item && styles.filterTextActive]}>{item}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>
      <View style={styles.resetGrid}>
        {tools.map((tool) => (
          <ResetToolCard
            key={tool.title}
            title={tool.title}
            description={tool.description}
            duration={tool.duration}
            icon={tool.icon}
            color={tool.color}
            onPress={() => startReset(tool.title)}
          />
        ))}
      </View>
      {status ? <Text style={styles.syncStatus}>{status}</Text> : null}
    </AppScreen>
  );
}

export function ProgressScreen() {
  const [summary, setSummary] = useState<ProgressSummary | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    fetchProgressSummary()
      .then((result) => {
        if (mounted) setSummary(result);
      })
      .catch(() => {
        if (mounted) setSummary(null);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const themes =
    summary && summary.themes.length > 0
      ? summary.themes
      : [
          { label: "Work pressure", value: 82, tone: "High" },
          { label: "Relationship stress", value: 60, tone: "Medium" },
          { label: "Sleep", value: 60, tone: "Medium" }
        ];

  return (
    <AppScreen>
      <AppHeader title="Progress" rightIcon="info" onRightPress={() => setStatus("Progress is based on your check-ins, completed resets, and recurring themes.")} />
      <Card style={styles.progressThemeCard}>
        <View style={styles.progressTitleRow}>
          <Text style={styles.sectionTitle}>This week’s themes</Text>
          <TouchableOpacity onPress={() => setStatus(`${themes.length} active themes shown this week.`)} activeOpacity={0.82}>
            <Text style={styles.viewAllText}>View all</Text>
          </TouchableOpacity>
        </View>
        <View style={styles.progressStack}>
          {themes.map((theme, index) => (
            <ProgressBar
              key={theme.label}
              label={theme.label}
              value={theme.value}
              tone={theme.tone}
              color={index === 0 ? colors.danger : index === 1 ? colors.warning : colors.purple}
              icon={theme.label.toLowerCase().includes("sleep") ? "sleep" : theme.label.toLowerCase().includes("relationship") ? "relationship" : "work"}
              iconColor={index === 0 ? "#EAB308" : undefined}
            />
          ))}
        </View>
      </Card>
      <Card onPress={() => setStatus(summary ? "Pattern updated from your synced activity." : "Pattern preview shown until the backend has enough activity.")}>
        <Text style={styles.cardLabel}>Pattern</Text>
        <Text style={styles.progressCardText}>
          {summary
            ? `${summary.checkins_this_week} check-ins and ${summary.resets_completed_this_week} completed resets this week.`
            : "Sunday nights seem harder for you. You often feel more stressed."}
        </Text>
        <Text style={styles.cardLink}>View pattern →</Text>
      </Card>
      <Card onPress={() => setStatus("Wins are calculated from completed resets and check-in trends.")}>
        <Text style={styles.cardLabel}>Wins</Text>
        <Text style={styles.progressCardText}>
          {summary ? `You completed ${summary.resets_completed_this_week} reset tools this week.` : "You paused before reacting 3 times this week."}
        </Text>
        <Text style={styles.winText}>Keep it up! 👍</Text>
      </Card>
      {status ? <Text style={styles.syncStatus}>{status}</Text> : null}
    </AppScreen>
  );
}

export function ProfileScreen() {
  const [status, setStatus] = useState<string | null>(null);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [tone, setTone] = useState("Calm & Grounded");
  const [notificationsEnabled, setNotificationsEnabled] = useState(false);

  async function runDataControl(action: "archive" | "export" | "delete") {
    if (action !== "delete") {
      setConfirmingDelete(false);
    }
    if (action === "delete" && !confirmingDelete) {
      setConfirmingDelete(true);
      setStatus("Tap Delete my data again to confirm.");
      return;
    }
    setStatus(action === "archive" ? "Archiving memories..." : action === "export" ? "Preparing export..." : "Deleting stored data...");
    try {
      if (action === "archive") {
        const result = await archiveMemories();
        setStatus(result.detail);
        return;
      }
      if (action === "export") {
        const result = await exportUserData();
        const count = result.memories.length + result.mood_checkins.length + result.reset_sessions.length + result.chat_messages.length;
        setStatus(`Export ready with ${count} records.`);
        return;
      }
      const result = await deleteUserData();
      setConfirmingDelete(false);
      setStatus(result.detail);
    } catch {
      setStatus("Data control could not sync. Please try again.");
    }
  }

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
        <TouchableOpacity style={styles.iconCircle} onPress={() => setStatus("Profile settings are available below.")}>
          <AppIcon name="settings" size={20} />
        </TouchableOpacity>
      </View>

      <Card>
        <Text style={styles.sectionTitle}>Your privacy, your control</Text>
        <SettingsRow label="Memory controls" icon="memory" onPress={() => runDataControl("archive")} />
        <SettingsRow label="Delete my data" value={confirmingDelete ? "Confirm" : undefined} icon="trash" onPress={() => runDataControl("delete")} />
        <SettingsRow label="Export my data" icon="export" onPress={() => runDataControl("export")} />
        <SettingsRow label="Privacy settings" value="Local" icon="privacy" onPress={() => setStatus("Privacy controls are local-first in this build. Use export, archive, or delete above for stored data.")} />
      </Card>
      {status ? <Text style={styles.syncStatus}>{status}</Text> : null}

      <Card>
        <Text style={styles.sectionTitle}>Preferences</Text>
        <SettingsRow
          label="AI tone"
          value={tone}
          icon="tone"
          onPress={() => {
            const nextTone = tone === "Calm & Grounded" ? "Direct & Practical" : "Calm & Grounded";
            setTone(nextTone);
            setStatus(`AI tone set to ${nextTone}.`);
          }}
        />
        <SettingsRow
          label="Notifications"
          value={notificationsEnabled ? "On" : "Off"}
          icon="notification"
          onPress={() => {
            setNotificationsEnabled((current) => !current);
            setStatus(notificationsEnabled ? "Notifications turned off." : "Notifications turned on for this session.");
          }}
        />
        <SettingsRow label="Appearance" value="Dark" icon="appearance" onPress={() => setStatus("Dark appearance is active.")} />
      </Card>

      <Card>
        <Text style={styles.sectionTitle}>Support</Text>
        <SettingsRow
          label="Emergency resources"
          icon="support"
          onPress={() => setStatus("If there is immediate danger, call emergency services now. In the U.S., call or text 988 for crisis support.")}
        />
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
  onboardingStepText: {
    color: colors.secondaryText,
    fontSize: 13,
    fontWeight: "700",
    textAlign: "center"
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
  onboardingActions: {
    flexDirection: "row",
    gap: spacing.md,
    marginTop: spacing.sm
  },
  onboardingActionPrimary: {
    flex: 1,
    marginTop: 0
  },
  secondaryButton: {
    minHeight: 54,
    minWidth: 108,
    borderRadius: radii.pill,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1
  },
  secondaryButtonDisabled: {
    opacity: 0.4
  },
  secondaryButtonText: {
    color: colors.text,
    fontSize: 16,
    fontWeight: "800"
  },
  secondaryButtonTextDisabled: {
    color: colors.muted
  },
  talkSafeArea: {
    flex: 1,
    backgroundColor: colors.background
  },
  talkKeyboard: {
    flex: 1
  },
  talkScroll: {
    flexGrow: 1,
    paddingHorizontal: spacing.md,
    paddingTop: spacing.xs,
    paddingBottom: spacing.md,
    gap: 16
  },
  talkScrollFocused: {
    paddingBottom: spacing.sm
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
    flexGrow: 1,
    gap: spacing.md,
    justifyContent: "flex-start"
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
  chatInputDock: {
    paddingHorizontal: spacing.md,
    paddingTop: spacing.sm,
    paddingBottom: spacing.sm,
    backgroundColor: colors.background
  },
  chatInputDockFocused: {
    paddingBottom: spacing.xs
  },
  errorText: {
    color: colors.danger,
    fontSize: 13,
    lineHeight: 18
  },
  validationText: {
    color: colors.warning,
    fontSize: 13,
    lineHeight: 18,
    fontWeight: "700"
  },
  syncStatus: {
    color: colors.secondaryText,
    fontSize: 13,
    lineHeight: 18
  },
  talkStatusRow: {
    alignSelf: "flex-start",
    minHeight: 44,
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: radii.md,
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1
  },
  talkStatusRowCompact: {
    minHeight: 34,
    marginTop: spacing.xs
  },
  talkStatusDots: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4
  },
  talkStatusDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.accentBright
  },
  talkStatusText: {
    color: colors.secondaryText,
    fontSize: 13,
    lineHeight: 18,
    fontWeight: "700"
  },
  voiceStates: {
    gap: spacing.md
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
