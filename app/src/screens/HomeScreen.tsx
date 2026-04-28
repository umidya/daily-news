import React from 'react';
import { Pressable, RefreshControl, StyleSheet, Text, View } from 'react-native';
import { Feather } from '@expo/vector-icons';
import { AppHeader } from '@/components/AppHeader';
import { ScreenContainer } from '@/components/ScreenContainer';
import { HeroBriefingCard } from '@/components/HeroBriefingCard';
import { StoryCard } from '@/components/StoryCard';
import { DigestPreviewCard } from '@/components/DigestPreviewCard';
import { useApp } from '@/state/AppContext';
import { formatMs } from '@/services/audio';
import { colors, spacing, typography } from '@/theme';

export function HomeScreen() {
  const { setActiveTab, briefing, playback, briefingLoading, refreshBriefing } = useApp();
  const b = briefing;
  const currentTime = playback.isLoaded ? formatMs(playback.positionMs) : b.currentTime;
  const totalDuration = playback.isLoaded ? formatMs(playback.durationMs) : b.totalDuration;
  const remaining = playback.isLoaded
    ? `About ${Math.max(0, Math.round((playback.durationMs - playback.positionMs) / 60000))} min left`
    : b.remaining;

  return (
    <ScreenContainer
      refreshControl={
        <RefreshControl refreshing={briefingLoading} onRefresh={refreshBriefing} tintColor={colors.accentBlue} />
      }
    >
      <AppHeader />

      <View style={styles.greetingBlock}>
        <Text style={styles.greeting}>{b.greeting}</Text>
        <Text style={styles.date}>{b.date}</Text>
      </View>

      <HeroBriefingCard
        totalDuration={totalDuration}
        currentTime={currentTime}
        remaining={remaining}
        hookCopy={b.hookCopy}
      />

      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>Top Stories</Text>
        <Pressable hitSlop={6}>
          <View style={styles.seeAll}>
            <Text style={styles.seeAllText}>See all</Text>
            <Feather name="chevron-right" size={16} color={colors.accentBlue} />
          </View>
        </Pressable>
      </View>

      <View style={{ gap: spacing.md }}>
        {b.topStories.map((s) => (
          <StoryCard key={s.id} story={s} />
        ))}
      </View>

      <View style={[styles.sectionHeader, { marginTop: spacing.xxl }]}>
        <View style={styles.titleWithIcon}>
          <View style={styles.miniDigestIcon}>
            <Feather name="file-text" size={16} color={colors.lavender} />
          </View>
          <Text style={styles.sectionTitle}>Written Digest</Text>
        </View>
        <Pressable hitSlop={6} onPress={() => setActiveTab('digest')}>
          <View style={styles.seeAll}>
            <Text style={[styles.seeAllText, { color: colors.lavender }]}>Read full digest</Text>
            <Feather name="chevron-right" size={16} color={colors.lavender} />
          </View>
        </Pressable>
      </View>

      <DigestPreviewCard
        intro={b.digestIntro}
        readingTime={b.digestReadingTime}
        onPress={() => setActiveTab('digest')}
      />
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  greetingBlock: {
    marginTop: spacing.lg,
    marginBottom: spacing.lg,
  },
  greeting: {
    ...typography.screenTitle,
    color: colors.textPrimary,
  },
  date: {
    ...typography.body,
    color: colors.textMuted,
    marginTop: 4,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: spacing.xxl,
    marginBottom: spacing.md,
  },
  sectionTitle: {
    ...typography.sectionTitle,
    color: colors.textPrimary,
  },
  seeAll: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 2,
  },
  seeAllText: {
    ...typography.bodySmall,
    color: colors.accentBlue,
    fontWeight: '600',
  },
  titleWithIcon: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  miniDigestIcon: {
    width: 32,
    height: 32,
    borderRadius: 8,
    backgroundColor: colors.lavenderSoft,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
