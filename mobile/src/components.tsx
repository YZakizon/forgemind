import React from "react";
import type { BottomTabBarProps } from "@react-navigation/bottom-tabs";
import {
  Bell,
  Brain,
  BriefcaseBusiness,
  ChevronLeft,
  Circle,
  Download,
  Flame,
  Heart,
  Home,
  Info,
  Lock,
  Mic,
  Moon,
  Send,
  Settings,
  Shield,
  SlidersHorizontal,
  Target,
  Trash2,
  TrendingUp,
  User,
  UserRound,
  UsersRound,
  Zap
} from "lucide-react-native";
import {
  type ColorValue,
  Modal,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View
} from "react-native";

import { colors, radii, shadow, spacing } from "./design";

export type Mode = "Vent" | "Advice" | "Calm" | "Clarity";
type TabName = "Home" | "Talk" | "Reset" | "Progress" | "Profile";

export type IconName =
  | "home"
  | "talk"
  | "reset"
  | "progress"
  | "profile"
  | "bell"
  | "sliders"
  | "back"
  | "info"
  | "settings"
  | "mic"
  | "send"
  | "anger"
  | "burnout"
  | "lonely"
  | "breakup"
  | "work"
  | "relationship"
  | "sleep"
  | "memory"
  | "trash"
  | "export"
  | "privacy"
  | "tone"
  | "notification"
  | "appearance"
  | "support";

const iconComponents: Record<IconName, typeof Home> = {
  home: Home,
  talk: Brain,
  reset: Target,
  progress: TrendingUp,
  profile: User,
  bell: Bell,
  sliders: SlidersHorizontal,
  back: ChevronLeft,
  info: Info,
  settings: Settings,
  mic: Mic,
  send: Send,
  anger: Zap,
  burnout: Flame,
  lonely: UserRound,
  breakup: Heart,
  work: BriefcaseBusiness,
  relationship: UsersRound,
  sleep: Moon,
  memory: Circle,
  trash: Trash2,
  export: Download,
  privacy: Shield,
  tone: Circle,
  notification: Bell,
  appearance: Circle,
  support: Lock
};

const tabIcons: Record<TabName, IconName> = {
  Home: "home",
  Talk: "talk",
  Reset: "reset",
  Progress: "progress",
  Profile: "profile"
};

export function AppIcon({ name, color = colors.secondaryText, size = 20 }: { name: IconName; color?: ColorValue; size?: number }) {
  const Icon = iconComponents[name];
  return <Icon color={color} size={size} strokeWidth={2.2} />;
}

export function BottomTabBar({ state, descriptors, navigation }: BottomTabBarProps) {
  return (
    <View style={styles.bottomBar}>
      {state.routes.map((route, index) => {
        const focused = state.index === index;
        const label = descriptors[route.key].options.tabBarLabel ?? descriptors[route.key].options.title ?? route.name;
        const color = focused ? colors.accentBright : colors.muted;

        return (
          <TouchableOpacity
            key={route.key}
            accessibilityRole="button"
            accessibilityState={focused ? { selected: true } : {}}
            onPress={() => {
              const event = navigation.emit({ type: "tabPress", target: route.key, canPreventDefault: true });
              if (!focused && !event.defaultPrevented) {
                navigation.navigate(route.name);
              }
            }}
            style={styles.bottomItem}
            activeOpacity={0.84}
          >
            <AppIcon name={tabIcons[route.name as TabName]} color={color} size={18} />
            <Text style={[styles.bottomLabel, { color }]}>{String(label)}</Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

export function AppScreen({ children }: { children: React.ReactNode }) {
  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.screen} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>
        {children}
      </ScrollView>
    </SafeAreaView>
  );
}

export function AppHeader({
  title,
  subtitle,
  leftIcon,
  rightIcon
}: {
  title: string;
  subtitle?: string;
  leftIcon?: IconName;
  rightIcon?: IconName;
}) {
  return (
    <View style={styles.header}>
      <View style={styles.headerSide}>{leftIcon ? <AppIcon name={leftIcon} size={22} /> : null}</View>
      <View style={styles.headerCopy}>
        <Text style={styles.headerTitle}>{title}</Text>
        {subtitle ? <Text style={styles.headerSubtitle}>{subtitle}</Text> : null}
      </View>
      <View style={styles.headerSide}>{rightIcon ? <AppIcon name={rightIcon} size={22} /> : null}</View>
    </View>
  );
}

export function GradientCard({
  title,
  subtitle,
  cta,
  icon
}: {
  title: string;
  subtitle: string;
  cta: string;
  icon?: IconName;
}) {
  return (
    <TouchableOpacity style={styles.heroCard} activeOpacity={0.86}>
      <View style={styles.heroGlow} />
      <View style={styles.heroGlowSecond} />
      <View style={styles.heroRidge} />
      <View style={styles.heroCopy}>
        <Text style={styles.heroTitle}>{title}</Text>
        <Text style={styles.heroSubtitle}>{subtitle}</Text>
      </View>
      <View style={styles.heroAction}>
        <AppIcon name="send" color={colors.text} size={20} />
      </View>
    </TouchableOpacity>
  );
}

export function QuickActionCard({ title, icon, color }: { title: string; icon: IconName; color: string }) {
  return (
    <TouchableOpacity style={styles.quickCard} activeOpacity={0.86}>
      <View style={[styles.iconBadge, styles.quickIconBadge, { backgroundColor: `${color}1F` }]}>
        <AppIcon name={icon} color={color} size={20} />
      </View>
      <Text style={styles.quickTitle}>{title}</Text>
    </TouchableOpacity>
  );
}

export function ResetToolCard({
  title,
  description,
  duration,
  icon,
  color = colors.accentBright
}: {
  title: string;
  description: string;
  duration?: string;
  icon: IconName;
  color?: string;
}) {
  return (
    <TouchableOpacity style={styles.resetCard} activeOpacity={0.86}>
      <View style={styles.resetTitleRow}>
        <View style={[styles.iconBadge, styles.resetIconBadge, { backgroundColor: `${color}1F` }]}>
          <AppIcon name={icon} color={color} size={17} />
        </View>
        <Text style={styles.cardTitle}>{title}</Text>
      </View>
      <Text style={styles.cardBody}>{description}</Text>
      {duration ? <Text style={styles.duration}>{duration}</Text> : null}
    </TouchableOpacity>
  );
}

export function ProgressBar({
  label,
  value,
  tone,
  color,
  icon,
  iconColor = color
}: {
  label: string;
  value: number;
  tone: string;
  color: string;
  icon: IconName;
  iconColor?: string;
}) {
  return (
    <View style={styles.progressRow}>
      <View style={[styles.progressIconBadge, { backgroundColor: `${iconColor}24` }]}>
        <AppIcon name={icon} color={iconColor} size={22} />
      </View>
      <View style={styles.progressBody}>
        <View style={styles.progressHeader}>
          <Text style={styles.progressLabel}>{label}</Text>
          <Text style={[styles.progressTone, { color }]}>{tone}</Text>
        </View>
        <View style={styles.progressTrack}>
          <View style={[styles.progressFill, { width: `${value}%`, backgroundColor: color }]} />
        </View>
      </View>
    </View>
  );
}

export function ChatBubble({ role, children }: { role: "forge" | "user"; children: React.ReactNode }) {
  return (
    <View style={[styles.chatBubble, role === "user" ? styles.userBubble : styles.forgeBubble]}>
      <Text style={[styles.chatText, role === "user" && styles.userChatText]}>{children}</Text>
    </View>
  );
}

export function ModeSelector({
  value,
  onChange,
  compact = false
}: {
  value: Mode;
  onChange: (mode: Mode) => void;
  compact?: boolean;
}) {
  const modes: Mode[] = ["Vent", "Advice", "Calm", "Clarity"];
  return (
    <View style={[styles.modeRow, compact && styles.modeRowCompact]}>
      {modes.map((mode) => (
        <TouchableOpacity
          key={mode}
          style={[styles.modeChip, value === mode && styles.modeChipActive]}
          onPress={() => onChange(mode)}
          activeOpacity={0.82}
        >
          <Text style={[styles.modeText, value === mode && styles.modeTextActive]}>{mode}</Text>
        </TouchableOpacity>
      ))}
    </View>
  );
}

export function ModeSelectorSheet({
  visible,
  selected,
  onSelect,
  onClose
}: {
  visible: boolean;
  selected: Mode;
  onSelect: (mode: Mode) => void;
  onClose: () => void;
}) {
  const options: Array<{ mode: Mode; copy: string }> = [
    { mode: "Vent", copy: "Speak freely. I’ll listen." },
    { mode: "Advice", copy: "Get practical guidance." },
    { mode: "Calm", copy: "Find peace and relaxation." },
    { mode: "Clarity", copy: "Think through clearly." }
  ];
  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={styles.sheetBackdrop} onPress={onClose} />
      <View style={styles.sheet}>
        <View style={styles.sheetHandle} />
        <Text style={styles.sheetTitle}>Choose mode</Text>
        {options.map((item) => (
          <TouchableOpacity
            key={item.mode}
            style={styles.sheetRow}
            onPress={() => {
              onSelect(item.mode);
              onClose();
            }}
          >
            <View>
              <Text style={styles.sheetMode}>{item.mode}</Text>
              <Text style={styles.sheetCopy}>{item.copy}</Text>
            </View>
            <Text style={styles.checkmark}>{selected === item.mode ? "✓" : ""}</Text>
          </TouchableOpacity>
        ))}
      </View>
    </Modal>
  );
}

export function VoiceOrb({ active = false }: { active?: boolean }) {
  return (
    <View style={styles.orbWrap}>
      <View style={[styles.ring, styles.ringOuter]} />
      <View style={[styles.ring, styles.ringMiddle]} />
      <View style={[styles.orb, active && styles.orbActive]}>
        <AppIcon name="mic" color={colors.text} size={34} />
      </View>
    </View>
  );
}

export function VoiceRecordingState() {
  return (
    <View style={styles.stateCard}>
      <Text style={styles.stateTimer}>00:18</Text>
      <VoiceOrb active />
      <Text style={styles.stateTitle}>Release to send</Text>
    </View>
  );
}

export function SendingAudioState() {
  return (
    <View style={styles.statePill}>
      <AppIcon name="send" color={colors.accentBright} size={20} />
      <View>
        <Text style={styles.stateTitle}>Sending...</Text>
        <Text style={styles.stateCopy}>Tap to cancel</Text>
      </View>
    </View>
  );
}

export function ForgeThinkingState() {
  return (
    <View style={styles.statePill}>
      <Text style={styles.dots}>•••</Text>
      <Text style={styles.stateTitle}>Forge is thinking...</Text>
    </View>
  );
}

export function ResponseStreamingState() {
  return (
    <View style={styles.audioCard}>
      <View style={styles.waveform}>
        {[18, 32, 22, 40, 26, 34, 20, 30, 24].map((height, index) => (
          <View key={`${height}-${index}`} style={[styles.waveBar, { height }]} />
        ))}
      </View>
      <Text style={styles.cardBody}>Forge is shaping this into one clear next step.</Text>
    </View>
  );
}

export function SettingsRow({ label, value, icon }: { label: string; value?: string; icon?: IconName }) {
  return (
    <TouchableOpacity style={styles.settingsRow} activeOpacity={0.84}>
      <View style={styles.settingsLabelWrap}>
        {icon ? <AppIcon name={icon} color={colors.secondaryText} size={18} /> : null}
        <Text style={styles.settingsLabel}>{label}</Text>
      </View>
      <Text style={styles.settingsValue}>{value ?? "›"}</Text>
    </TouchableOpacity>
  );
}

export function Card({ children, style }: { children: React.ReactNode; style?: object }) {
  return <View style={[styles.card, style]}>{children}</View>;
}

export function SectionTitle({ children }: { children: React.ReactNode }) {
  return <Text style={styles.sectionTitle}>{children}</Text>;
}

export function MessageInput() {
  return (
    <View style={styles.inputWrap}>
      <TextInput placeholder="Type a message..." placeholderTextColor={colors.muted} style={styles.input} />
      <TouchableOpacity style={styles.micButton}>
        <AppIcon name="mic" color={colors.text} size={20} />
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: colors.background
  },
  screen: {
    paddingHorizontal: spacing.md,
    paddingTop: spacing.xs,
    paddingBottom: 96,
    gap: 16
  },
  bottomBar: {
    position: "absolute",
    left: 14,
    right: 14,
    bottom: 10,
    minHeight: 68,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-around",
    borderRadius: 22,
    backgroundColor: "rgba(17,24,39,0.96)",
    borderColor: colors.border,
    borderWidth: 1,
    ...shadow
  },
  bottomItem: {
    flex: 1,
    minHeight: 58,
    alignItems: "center",
    justifyContent: "center",
    gap: 3
  },
  bottomLabel: {
    fontSize: 11,
    lineHeight: 15,
    fontWeight: "700"
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm
  },
  headerSide: {
    width: 38,
    minHeight: 38,
    alignItems: "center",
    justifyContent: "center"
  },
  headerCopy: {
    flex: 1
  },
  headerTitle: {
    color: colors.text,
    fontSize: 22,
    lineHeight: 28,
    fontWeight: "700"
  },
  headerSubtitle: {
    color: colors.secondaryText,
    fontSize: 15,
    lineHeight: 22,
    marginTop: 4
  },
  heroCard: {
    minHeight: 92,
    overflow: "hidden",
    borderRadius: 16,
    backgroundColor: colors.elevated,
    borderColor: colors.border,
    borderWidth: 1,
    padding: 12,
    flexDirection: "row",
    alignItems: "flex-end",
    ...shadow
  },
  heroGlow: {
    position: "absolute",
    right: -26,
    top: -28,
    width: 142,
    height: 142,
    borderRadius: 71,
    backgroundColor: colors.accent,
    opacity: 0.34
  },
  heroGlowSecond: {
    position: "absolute",
    right: 42,
    bottom: -48,
    width: 150,
    height: 118,
    borderRadius: 40,
    backgroundColor: "#1E3A8A",
    opacity: 0.32,
    transform: [{ rotate: "-16deg" }]
  },
  heroRidge: {
    position: "absolute",
    right: 22,
    bottom: -24,
    width: 170,
    height: 70,
    borderRadius: 18,
    backgroundColor: "#172554",
    opacity: 0.45,
    transform: [{ rotate: "20deg" }]
  },
  heroCopy: {
    flex: 1
  },
  heroTitle: {
    color: colors.text,
    fontSize: 18,
    lineHeight: 23,
    fontWeight: "700"
  },
  heroSubtitle: {
    color: colors.secondaryText,
    fontSize: 14,
    lineHeight: 20,
    marginTop: 5
  },
  heroAction: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.accentBright
  },
  quickCard: {
    width: 82,
    minHeight: 88,
    borderRadius: 13,
    backgroundColor: colors.elevated,
    borderColor: colors.border,
    borderWidth: 1,
    padding: 9,
    justifyContent: "space-between"
  },
  iconBadge: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.secondary,
    alignItems: "center",
    justifyContent: "center"
  },
  quickIconBadge: {
    alignSelf: "center"
  },
  resetIconBadge: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: "rgba(79,125,255,0.14)"
  },
  quickTitle: {
    color: colors.text,
    fontSize: 12,
    lineHeight: 16,
    textAlign: "center",
    fontWeight: "700"
  },
  resetCard: {
    width: "48%",
    minHeight: 124,
    borderRadius: 13,
    backgroundColor: colors.elevated,
    borderColor: colors.border,
    borderWidth: 1,
    padding: 14,
    gap: 12
  },
  resetTitleRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8
  },
  card: {
    borderRadius: 16,
    backgroundColor: colors.elevated,
    borderColor: colors.border,
    borderWidth: 1,
    padding: 16
  },
  cardTitle: {
    color: colors.text,
    flex: 1,
    fontSize: 13,
    lineHeight: 17,
    fontWeight: "700"
  },
  cardBody: {
    color: colors.secondaryText,
    fontSize: 14,
    lineHeight: 20
  },
  duration: {
    color: colors.muted,
    fontSize: 13,
    marginTop: "auto"
  },
  sectionTitle: {
    color: colors.text,
    fontSize: 17,
    fontWeight: "700"
  },
  progressRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 14
  },
  progressIconBadge: {
    width: 44,
    height: 44,
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center"
  },
  progressBody: {
    flex: 1,
    gap: 6
  },
  progressHeader: {
    flexDirection: "row",
    justifyContent: "space-between"
  },
  progressLabel: {
    color: colors.text,
    fontSize: 15,
    fontWeight: "700"
  },
  progressTone: {
    color: colors.secondaryText,
    fontSize: 15,
    fontWeight: "500"
  },
  progressTrack: {
    height: 7,
    borderRadius: 5,
    backgroundColor: colors.secondary,
    overflow: "hidden"
  },
  progressFill: {
    height: "100%",
    borderRadius: 5,
    backgroundColor: colors.accent
  },
  chatBubble: {
    maxWidth: "86%",
    borderRadius: 14,
    paddingVertical: 9,
    paddingHorizontal: 11
  },
  forgeBubble: {
    alignSelf: "flex-start",
    backgroundColor: colors.elevated
  },
  userBubble: {
    alignSelf: "flex-end",
    backgroundColor: colors.accent
  },
  chatText: {
    color: colors.text,
    fontSize: 14,
    lineHeight: 20
  },
  userChatText: {
    fontWeight: "600"
  },
  modeRow: {
    flexDirection: "row",
    gap: 8
  },
  modeRowCompact: {
    justifyContent: "center"
  },
  modeChip: {
    flex: 1,
    minHeight: 38,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: radii.pill,
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    paddingHorizontal: 10
  },
  modeChipActive: {
    backgroundColor: colors.accent,
    borderColor: colors.accentBright
  },
  modeText: {
    color: colors.secondaryText,
    fontSize: 13,
    fontWeight: "700"
  },
  modeTextActive: {
    color: colors.text
  },
  sheetBackdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.55)"
  },
  sheet: {
    position: "absolute",
    left: 0,
    right: 0,
    bottom: 0,
    borderTopLeftRadius: 28,
    borderTopRightRadius: 28,
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    padding: spacing.xl,
    gap: spacing.sm
  },
  sheetHandle: {
    alignSelf: "center",
    width: 42,
    height: 5,
    borderRadius: 3,
    backgroundColor: colors.secondary,
    marginBottom: spacing.sm
  },
  sheetTitle: {
    color: colors.text,
    fontSize: 18,
    fontWeight: "700",
    marginBottom: spacing.sm
  },
  sheetRow: {
    minHeight: 72,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    borderBottomColor: colors.border,
    borderBottomWidth: 1
  },
  sheetMode: {
    color: colors.text,
    fontSize: 15,
    fontWeight: "700"
  },
  sheetCopy: {
    color: colors.secondaryText,
    fontSize: 13,
    marginTop: 5
  },
  checkmark: {
    color: colors.accentBright,
    fontSize: 22
  },
  orbWrap: {
    height: 220,
    alignItems: "center",
    justifyContent: "center"
  },
  ring: {
    position: "absolute",
    borderColor: colors.accent,
    borderWidth: 1,
    opacity: 0.2
  },
  ringOuter: {
    width: 210,
    height: 210,
    borderRadius: 105
  },
  ringMiddle: {
    width: 154,
    height: 154,
    borderRadius: 77
  },
  orb: {
    width: 96,
    height: 96,
    borderRadius: 48,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.accent,
    ...shadow
  },
  orbActive: {
    backgroundColor: colors.warning
  },
  stateCard: {
    alignItems: "center",
    gap: spacing.sm
  },
  stateTimer: {
    color: colors.secondaryText,
    fontSize: 13,
    fontWeight: "700"
  },
  stateTitle: {
    color: colors.text,
    fontSize: 14,
    fontWeight: "700"
  },
  stateCopy: {
    color: colors.secondaryText,
    fontSize: 12,
    marginTop: 3
  },
  statePill: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    borderRadius: radii.md,
    backgroundColor: colors.elevated,
    borderColor: colors.border,
    borderWidth: 1,
    padding: spacing.md
  },
  dots: {
    color: colors.accentBright,
    fontSize: 24,
    letterSpacing: 2
  },
  audioCard: {
    gap: spacing.md,
    borderRadius: radii.md,
    backgroundColor: colors.elevated,
    borderColor: colors.border,
    borderWidth: 1,
    padding: spacing.md
  },
  waveform: {
    height: 48,
    flexDirection: "row",
    alignItems: "center",
    gap: 7
  },
  waveBar: {
    width: 5,
    borderRadius: 3,
    backgroundColor: colors.accentBright
  },
  settingsRow: {
    minHeight: 52,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    borderBottomColor: colors.border,
    borderBottomWidth: 1
  },
  settingsLabel: {
    color: colors.text,
    fontSize: 15,
    fontWeight: "700"
  },
  settingsLabelWrap: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10
  },
  settingsValue: {
    color: colors.secondaryText,
    fontSize: 15
  },
  inputWrap: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    borderRadius: 20,
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    padding: 6
  },
  input: {
    flex: 1,
    minHeight: 36,
    color: colors.text,
    paddingHorizontal: spacing.md
  },
  micButton: {
    width: 42,
    height: 42,
    borderRadius: 21,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.accent
  },
  micIcon: {
    color: colors.text,
    fontSize: 18
  }
});
