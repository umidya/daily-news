import React, { useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { Feather } from '@expo/vector-icons';
import { AppHeader } from '@/components/AppHeader';
import { ScreenContainer } from '@/components/ScreenContainer';
import { PersonalizeArtwork } from '@/components/PersonalizeArtwork';
import { ToggleRow } from '@/components/ToggleRow';
import { AddTopicChip, MutedTopicChip, TopicChip } from '@/components/TopicChip';
import { VoiceCard } from '@/components/VoiceCard';
import { voices } from '@/data/mockNews';
import { useApp } from '@/state/AppContext';
import { colors, radii, shadows, spacing, typography } from '@/theme';

const ALL_TOPICS = [
  'Canada',
  'Kamloops',
  'Sun Peaks',
  'AI',
  'Business',
  'Real Estate',
  'Marketing',
  'Higher Ed',
  'AirBnb in BC',
  'Global',
];

export function SettingsScreen() {
  const {
    selectedTopics,
    toggleTopic,
    addTopic,
    mutedTopics,
    removeMuted,
    addMuted,
    selectedVoice,
    setSelectedVoice,
    deliveryHour,
    deliveryMinute,
    setDeliveryHour,
    setDeliveryMinute,
    audioOn,
    setAudioOn,
    digestOn,
    setDigestOn,
    highQualityOnly,
    setHighQualityOnly,
    reduceDuplicates,
    setReduceDuplicates,
  } = useApp();
  const [addingTopic, setAddingTopic] = useState(false);
  const [topicInput, setTopicInput] = useState('');
  const [addingMuted, setAddingMuted] = useState(false);
  const [mutedInput, setMutedInput] = useState('');

  const handleAddTopicSubmit = () => {
    const t = topicInput.trim();
    if (t) addTopic(t);
    setTopicInput('');
    setAddingTopic(false);
  };
  const handleAddMutedSubmit = () => {
    const t = mutedInput.trim();
    if (t) addMuted(t);
    setMutedInput('');
    setAddingMuted(false);
  };
  const allTopicChoices = Array.from(new Set([...ALL_TOPICS, ...selectedTopics]));

  return (
    <ScreenContainer>
      <AppHeader />

      <View style={styles.heroBlock}>
        <View style={{ flex: 1 }}>
          <Text style={styles.title}>Personalize</Text>
          <Text style={styles.subtitle}>Tailor your briefing to what matters most.</Text>
          <Text style={styles.tzNote}>
            Notification fires at your phone's local time — auto-adjusts when you travel.
          </Text>
        </View>
        <PersonalizeArtwork width={170} height={120} />
      </View>

      {/* Morning delivery */}
      <SectionCard
        icon={<Feather name="clock" size={18} color={colors.lavender} />}
        iconBg={colors.lavenderSoft}
        title="Morning delivery"
        subtitle="Choose when and how you get your briefing."
      >
        <View style={styles.deliveryRow}>
          <View style={styles.timeBox}>
            <Text style={styles.timeLabel}>Delivery time</Text>
            <View style={styles.timeRow}>
              <NumberStepper
                value={deliveryHour}
                min={1}
                max={12}
                onChange={setDeliveryHour}
              />
              <Text style={styles.timeColon}>:</Text>
              <NumberStepper
                value={deliveryMinute}
                min={0}
                max={59}
                step={15}
                pad
                onChange={setDeliveryMinute}
              />
              <Text style={styles.ampm}>AM</Text>
            </View>
          </View>

          <View style={{ flex: 1, gap: spacing.sm }}>
            <ToggleRow
              title="Audio briefing"
              subtitle="Play my 10-min briefing"
              value={audioOn}
              onToggle={setAudioOn}
              tint="lavender"
            />
            <ToggleRow
              title="Written digest"
              subtitle="Send me the full digest"
              value={digestOn}
              onToggle={setDigestOn}
              tint="lavender"
            />
          </View>
        </View>
      </SectionCard>

      {/* Topics */}
      <SectionCard
        icon={<Feather name="hash" size={18} color={colors.accentBlue} />}
        iconBg={colors.accentBlueSoft}
        title="Topics I care about"
        subtitle="We'll prioritize these in your briefing."
      >
        <View style={styles.chipWrap}>
          {allTopicChoices.map((t) => (
            <TopicChip
              key={t}
              label={t}
              selected={selectedTopics.includes(t)}
              onPress={() => toggleTopic(t)}
            />
          ))}
          {addingTopic ? (
            <TextInput
              autoFocus
              value={topicInput}
              onChangeText={setTopicInput}
              onSubmitEditing={handleAddTopicSubmit}
              onBlur={handleAddTopicSubmit}
              placeholder="New topic"
              placeholderTextColor={colors.textMuted}
              returnKeyType="done"
              style={styles.inlineInput}
            />
          ) : (
            <AddTopicChip onPress={() => setAddingTopic(true)} />
          )}
        </View>
      </SectionCard>

      {/* Mute */}
      <SectionCard
        icon={<Feather name="volume-x" size={18} color={colors.coral} />}
        iconBg={colors.coralSoft}
        title="Mute topics"
        subtitle="We'll skip these unless major breaking news."
      >
        <View style={styles.chipWrap}>
          {mutedTopics.map((t) => (
            <MutedTopicChip key={t} label={t} onRemove={() => removeMuted(t)} />
          ))}
          {addingMuted ? (
            <TextInput
              autoFocus
              value={mutedInput}
              onChangeText={setMutedInput}
              onSubmitEditing={handleAddMutedSubmit}
              onBlur={handleAddMutedSubmit}
              placeholder="Topic to mute"
              placeholderTextColor={colors.textMuted}
              returnKeyType="done"
              style={styles.inlineInput}
            />
          ) : (
            <AddTopicChip onPress={() => setAddingMuted(true)} />
          )}
        </View>
      </SectionCard>

      {/* Voice */}
      <SectionCard
        icon={<Feather name="mic" size={18} color={colors.lavender} />}
        iconBg={colors.lavenderSoft}
        title="Choose your voice"
        subtitle="Tap to hear a sample. Voice change applies to tomorrow's briefing."
      >
        <View style={styles.voiceRow}>
          {voices.map((v) => (
            <VoiceCard
              key={v.id}
              voice={v}
              selected={selectedVoice === v.id}
              onPress={() => setSelectedVoice(v.id)}
            />
          ))}
        </View>
      </SectionCard>

      {/* Source quality */}
      <SectionCard
        icon={<Feather name="shield" size={18} color={colors.mint} />}
        iconBg={colors.mintSoft}
        title="Source quality"
        subtitle="Control the quality and relevance of your news."
      >
        <ToggleRow
          title="Only high-quality sources"
          subtitle="Prioritize trusted publishers"
          value={highQualityOnly}
          onToggle={setHighQualityOnly}
          tint="mint"
        />
        <View style={styles.thinDivider} />
        <ToggleRow
          title="Reduce duplicates"
          subtitle="Avoid repeating similar stories"
          value={reduceDuplicates}
          onToggle={setReduceDuplicates}
          tint="mint"
        />
      </SectionCard>
    </ScreenContainer>
  );
}

function SectionCard({
  icon,
  iconBg,
  title,
  subtitle,
  children,
}: {
  icon: React.ReactNode;
  iconBg: string;
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <View style={[sectionStyles.card, shadows.cardSoft]}>
      <View style={sectionStyles.head}>
        <View style={[sectionStyles.iconWrap, { backgroundColor: iconBg }]}>{icon}</View>
        <View style={{ flex: 1 }}>
          <Text style={sectionStyles.title}>{title}</Text>
          <Text style={sectionStyles.subtitle}>{subtitle}</Text>
        </View>
      </View>
      <View style={sectionStyles.body}>{children}</View>
    </View>
  );
}

function NumberStepper({
  value,
  onChange,
  min,
  max,
  step = 1,
  pad = false,
}: {
  value: number;
  onChange: (v: number) => void;
  min: number;
  max: number;
  step?: number;
  pad?: boolean;
}) {
  // Largest valid stepped value <= max so 0→down with step=15 wraps to 45 not 59.
  const lastStep = min + Math.floor((max - min) / step) * step;
  const inc = () => {
    let next = value + step;
    if (next > max) next = min;
    onChange(next);
  };
  const dec = () => {
    let next = value - step;
    if (next < min) next = lastStep;
    onChange(next);
  };
  return (
    <View style={stepperStyles.col}>
      <Pressable onPress={inc} hitSlop={6}>
        <Feather name="chevron-up" size={20} color={colors.lavender} />
      </Pressable>
      <Text style={stepperStyles.value}>{pad ? String(value).padStart(2, '0') : value}</Text>
      <Pressable onPress={dec} hitSlop={6}>
        <Feather name="chevron-down" size={20} color={colors.lavender} />
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  heroBlock: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    marginTop: spacing.md,
    marginBottom: spacing.lg,
  },
  title: {
    ...typography.screenTitle,
    color: colors.textPrimary,
  },
  subtitle: {
    ...typography.body,
    color: colors.textMuted,
    marginTop: 2,
  },
  tzNote: {
    ...typography.caption,
    color: colors.textMuted,
    marginTop: 6,
    fontStyle: 'italic',
  },
  deliveryRow: {
    flexDirection: 'row',
    gap: spacing.md,
  },
  timeBox: {
    width: 130,
    backgroundColor: colors.surfaceTint,
    borderRadius: radii.lg,
    padding: spacing.md,
    alignItems: 'flex-start',
  },
  timeLabel: {
    ...typography.caption,
    color: colors.textMuted,
    marginBottom: spacing.sm,
  },
  timeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  timeColon: {
    ...typography.cardTitle,
    fontSize: 28,
    color: colors.textPrimary,
  },
  ampm: {
    ...typography.caption,
    color: colors.textPrimary,
    fontWeight: '700',
    marginLeft: 4,
  },
  chipWrap: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  inlineInput: {
    minWidth: 120,
    paddingHorizontal: spacing.md,
    paddingVertical: 8,
    borderRadius: radii.pill,
    borderWidth: 1,
    borderColor: colors.accentBlue,
    backgroundColor: colors.surface,
    ...typography.bodySmall,
    color: colors.textPrimary,
    fontWeight: '600',
  },
  voiceRow: {
    flexDirection: 'row',
    gap: spacing.sm,
  },
  thinDivider: {
    height: StyleSheet.hairlineWidth,
    backgroundColor: colors.divider,
    marginVertical: spacing.xs,
  },
});

const sectionStyles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderRadius: radii.xxl,
    padding: spacing.lg,
    marginBottom: spacing.lg,
  },
  head: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    marginBottom: spacing.md,
  },
  iconWrap: {
    width: 38,
    height: 38,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  title: {
    ...typography.bodyStrong,
    fontSize: 18,
    color: colors.textPrimary,
    fontWeight: '700',
  },
  subtitle: {
    ...typography.bodySmall,
    color: colors.textMuted,
    marginTop: 2,
  },
  body: {
    gap: spacing.sm,
  },
});

const stepperStyles = StyleSheet.create({
  col: {
    alignItems: 'center',
    gap: 2,
  },
  value: {
    ...typography.cardTitle,
    fontSize: 28,
    color: colors.textPrimary,
  },
});
