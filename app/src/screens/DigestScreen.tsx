import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { Feather } from '@expo/vector-icons';
import { ScreenContainer } from '@/components/ScreenContainer';
import { CategoryPill } from '@/components/CategoryPill';
import { StoryThumbnail } from '@/components/StoryThumbnail';
import { useApp } from '@/state/AppContext';
import { colors, radii, shadows, spacing, typography } from '@/theme';

export function DigestScreen() {
  const { briefing, savedStoryIds, toggleSaved, setActiveTab } = useApp();
  const b = briefing;
  const digestId = 'digest-today';
  const isSaved = savedStoryIds.has(digestId);

  return (
    <View style={{ flex: 1, backgroundColor: colors.background }}>
      <ScreenContainer>
        {/* Header row */}
        <View style={styles.topRow}>
          <Pressable hitSlop={10} style={styles.iconBtn} onPress={() => setActiveTab('home')}>
            <Feather name="chevron-left" size={24} color={colors.textPrimary} />
          </Pressable>
          <Text style={styles.headerTitle}>Written Digest</Text>
          <Pressable hitSlop={10} style={styles.iconBtn}>
            <Feather name="share" size={20} color={colors.textPrimary} />
          </Pressable>
        </View>

        <View style={styles.metaRow}>
          <View style={[styles.metaPill, { backgroundColor: colors.lavenderSoft }]}>
            <Feather name="calendar" size={14} color={colors.lavender} />
            <Text style={[styles.metaText, { color: colors.lavender }]}>{b.date}</Text>
          </View>
          <View style={[styles.metaPill, { backgroundColor: colors.accentBlueSoft }]}>
            <Feather name="clock" size={14} color={colors.accentBlue} />
            <Text style={[styles.metaText, { color: colors.accentBlue }]}>{b.digestReadingTime}</Text>
          </View>
        </View>

        <Text style={styles.title}>Your Morning Briefing</Text>
        <Text style={styles.intro}>{b.digestIntro}</Text>

        <View style={styles.divider} />

        {b.digestStories.map((s, idx) => (
          <View key={s.id}>
            <Pressable style={({ pressed }) => [styles.storyRow, pressed && { opacity: 0.85 }]}>
              <StoryThumbnail kind={s.thumbnailKind} size={92} rounded={14} />
              <View style={styles.storyText}>
                <CategoryPill category={s.category} />
                <Text style={styles.storyHeadline}>{s.headline}</Text>
                <Text style={styles.storySummary} numberOfLines={2}>
                  {s.summary}
                </Text>
              </View>
              <Feather name="chevron-right" size={20} color={colors.textMuted} />
            </Pressable>
            {idx < b.digestStories.length - 1 && <View style={styles.divider} />}
          </View>
        ))}

        <View style={styles.callout}>
          <View style={styles.calloutIcon}>
            <Feather name="zap" size={18} color="#FFFFFF" />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.calloutTitle}>Why it matters</Text>
            <Text style={styles.calloutBody}>{b.whyItMatters}</Text>
          </View>
        </View>
      </ScreenContainer>

      <Pressable
        onPress={() => toggleSaved(digestId)}
        style={[styles.fab, shadows.fab]}
      >
        <Feather
          name="bookmark"
          size={22}
          color="#FFFFFF"
          style={isSaved ? { transform: [{ scale: 1 }] } : undefined}
        />
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  topRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingTop: spacing.sm,
    marginBottom: spacing.lg,
  },
  iconBtn: {
    width: 36,
    height: 36,
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerTitle: {
    ...typography.cardTitle,
    fontSize: 22,
    color: colors.textPrimary,
  },
  metaRow: {
    flexDirection: 'row',
    gap: spacing.sm,
    marginBottom: spacing.lg,
  },
  metaPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: spacing.md,
    paddingVertical: 8,
    borderRadius: radii.pill,
  },
  metaText: {
    ...typography.bodySmall,
    fontWeight: '600',
  },
  title: {
    ...typography.heroTitle,
    color: colors.textPrimary,
    marginBottom: spacing.md,
  },
  intro: {
    ...typography.body,
    color: colors.textSecondary,
    lineHeight: 24,
  },
  divider: {
    height: StyleSheet.hairlineWidth,
    backgroundColor: colors.border,
    marginVertical: spacing.lg,
  },
  storyRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
  },
  storyText: {
    flex: 1,
    gap: 4,
  },
  storyHeadline: {
    ...typography.storyHeadline,
    fontSize: 18,
    lineHeight: 24,
    color: colors.textPrimary,
  },
  storySummary: {
    ...typography.bodySmall,
    color: colors.textMuted,
  },
  callout: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    padding: spacing.lg,
    borderRadius: radii.xl,
    backgroundColor: colors.warmYellowSoft,
    marginTop: spacing.md,
  },
  calloutIcon: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: colors.amber,
    alignItems: 'center',
    justifyContent: 'center',
  },
  calloutTitle: {
    ...typography.bodyStrong,
    color: colors.textPrimary,
    marginBottom: 2,
  },
  calloutBody: {
    ...typography.bodySmall,
    color: colors.textSecondary,
  },
  fab: {
    position: 'absolute',
    right: spacing.xl,
    bottom: 96 + spacing.lg,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: colors.lavender,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
