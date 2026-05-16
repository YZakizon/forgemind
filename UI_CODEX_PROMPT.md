Update ForgeMind mobile UI to match the attached dark modern Android mockup.

Design target:
A premium, native-feeling Android app using React Native CLI + TypeScript. The UI should feel like Material 3 dark mode: rounded cards, bottom navigation, calm spacing, dark surfaces, subtle blue accents, and low visual noise. Material 3 navigation bars are intended for switching between top-level views on handheld screens, and cards should be used to group related content/actions. Use those patterns heavily.
Reference: Material 3 bottom navigation and card principles.

Do not make the UI look like:
- a generic chatbot
- a therapy clinic
- a meditation clone
- a web dashboard
- a social media app

Brand:
- Product name: ForgeMind
- AI companion name: Forge

Visual system:
- Background: #070B12 or #0B0F14
- Surface: #111827
- Elevated card: #151D2A
- Secondary surface: #1B2433
- Border: rgba(255,255,255,0.08)
- Primary text: #F8FAFC
- Secondary text: #94A3B8
- Muted text: #64748B
- Accent blue: #4F7DFF
- Accent blue bright: #5B8CFF
- Danger red: #EF4444
- Warning orange: #F97316
- Success green: #22C55E
- Purple accent: #8B5CF6

Typography:
- Use clean Android-style typography.
- Large titles: 22–28px, semi-bold.
- Section titles: 14–16px, semi-bold.
- Body text: 13–15px.
- Labels: 11–12px.
- Use generous line height.
- Avoid dense text.

Layout:
- Dark full-screen background.
- Use SafeAreaView.
- Use 16–20px horizontal padding.
- Use 16–24px screen spacing.
- Cards should use 18–24px border radius.
- Use subtle borders and shadows.
- Bottom tab bar should be floating/dark with 5 tabs.

Navigation:
Bottom tabs:
1. Home
2. Talk
3. Reset
4. Progress
5. Profile

Use icons for each tab:
- Home
- Talk/chat bubble
- Reset/refresh or target
- Progress/bar chart
- Profile/user

Screen 1: Home
Create a calm dashboard.

Content:
- Header with greeting:
  “Good evening, Yeffry”
  “What’s taking most of your headspace right now?”
- Notification icon on the right.
- Large hero card:
  Title: “Talk to Forge”
  Subtitle: “I’m here. Let’s talk.”
  Right side: circular arrow button.
  Use subtle blue gradient background.
- Quick check-in section:
  Horizontal action cards:
  Angry
  Burned out
  Lonely
  Breakup
- Two small cards below:
  Insight:
  “You’ve mentioned work stress several times this week.”
  CTA: “View details →”
  Reset:
  “2-minute reset to clear your mind.”
  CTA: “Start →”

Screen 2: Talk
Create a modern chat screen.

Header:
- Back arrow
- Title: “Forge”
- Settings/sliders icon

Conversation:
- Forge bubble:
  “I’m here, Yeffry. What’s on your mind?”
- User bubble in blue:
  “I feel so overwhelmed with work and life right now.”
- Forge bubble:
  “That’s a lot to carry. Let’s slow it down. What’s been the hardest part today?”
- Suggested reply chips:
  “It’s the pressure”
  “No time for myself”
  “I don’t know”

Input:
- Rounded text input: “Type a message…”
- Circular mic button on the right.
- Mode selector row:
  Vent
  Advice
  Calm
  Clarity
Highlight selected mode.

Screen 3: Listening / Voice
Create tap-to-talk listening screen.

Header:
- Back arrow
- Title: “Forge”
- Settings/sliders icon

Center:
- Text: “Listening…”
- Large circular glowing mic/waveform button.
- Concentric rings around button.
- Caption:
  “Tap to stop”
  “Speak naturally. I’m listening.”

Bottom:
- Mode selector:
  Vent
  Advice
  Calm
  Clarity

Important:
This is Tap-to-Talk MVP, not realtime phone-call mode.

Screen 4: Reset
Create a reset tools grid.

Header:
- Title: “Reset”
- Info icon

Filter chips:
- All
- Emotions
- Life Events
- Sleep
- Relationships

Grid cards:
1. Anger Reset
   “Release tension and cool down”
   “3 min”
2. Burnout Reset
   “Recharge your energy”
   “4 min”
3. Breakup Reset
   “Heal and move forward”
   “5 min”
4. Divorce Support
   “Navigate with strength”
   “5–10 min”
5. Wedding Stress
   “Stay calm during big moments”
   “3 min”
6. Sleep Reset
   “Quiet your mind for deep sleep”
   “3 min”
7. Confidence Boost
   “Rebuild your inner strength”
8. Family Conflict
   “Handle tough conversations”

Each card:
- rounded rectangle
- icon badge
- title
- short description
- duration

Screen 5: Progress
Create emotionally safe insights, not medical dashboard.

Header:
- Title: “Progress”
- Info icon

Sections:
- “This week’s themes”
  Work pressure — High
  Relationship stress — Medium
  Sleep — Medium
  Use horizontal progress bars.
- Pattern card:
  “Sunday nights seem harder for you. You often feel more stressed.”
  CTA: “View pattern →”
- Wins card:
  “You paused before reacting 3 times this week.”
  “Keep it up! 👍”

Screen 6: Profile
Create trust/privacy-focused settings screen.

Header:
- Avatar with ForgeMind logo
- Name: Yeffry
- “Member since May 2025”
- Premium badge
- Settings gear

Cards:
1. Your privacy, your control
   - Memory controls
   - Delete my data
   - Export my data
   - Privacy settings

2. Preferences
   - AI tone: Calm & Grounded
   - Notifications
   - Appearance: Dark

3. Support
   - Emergency resources

Screen 7: Mode Selector Bottom Sheet
Create a bottom sheet/modal with modes:
- Vent: “Speak freely. I’ll listen.”
- Advice: “Get practical guidance.”
- Calm: “Find peace and relaxation.”
- Clarity: “Think through clearly.”

Selected mode should show a checkmark.

Screen 8: Voice State Components
Create reusable components/states:
- VoiceRecordingState
  Shows timer, circular mic button, “Release to send”
- SendingAudioState
  Shows paper-plane icon, “Sending…”, “Tap to cancel”
- ForgeThinkingState
  Shows animated dots, “Forge is thinking…”
- ResponseStreamingState
  Shows waveform/audio card and message cards.

Implementation requirements:
- Use React Native CLI + TypeScript.
- Do not use Expo.
- Use componentized structure.
- Create reusable components:
  AppScreen
  AppHeader
  BottomTabBar
  GradientCard
  QuickActionCard
  ResetToolCard
  ProgressBar
  ChatBubble
  ModeSelector
  VoiceOrb
  SettingsRow
- If gradients are needed, use react-native-linear-gradient.
- If icons are needed, use lucide-react-native or react-native-vector-icons.
- Use React Navigation for bottom tabs and stack navigation.
- Keep the UI responsive for Android screen sizes.
- Prioritize Android native feel.
- Do not implement backend logic in this task.
- Mock data is acceptable for UI preview.
- Keep all copy aligned with ForgeMind tone: calm, grounded, practical.
- Do not use therapy/diagnosis language.
- Do not include fake human backstory for Forge.

Deliverables:
- Updated mobile UI screens.
- Reusable design system constants.
- Component library.
- Navigation structure.
- Mock state examples for Home, Talk, Voice, Reset, Progress, and Profile.
- README note explaining how to run the mobile app.

Acceptance criteria:
- App visually resembles the provided mockup.
- Dark theme is consistent.
- Bottom navigation works.
- Each major screen exists.
- Cards, typography, and spacing feel premium.
- Voice screen uses Tap-to-Talk style.
- Reset screen includes breakup, divorce, wedding stress, and family conflict tools.
