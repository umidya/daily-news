import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { Feather, Ionicons } from '@expo/vector-icons';
import { AppHeader } from '@/components/AppHeader';
import { ScreenContainer } from '@/components/ScreenContainer';
import { BriefingArtwork } from '@/components/BriefingArtwork';
import { AudioPlayer } from '@/components/AudioPlayer';
import { ChapterList } from '@/components/ChapterList';
import { CategoryPill } from '@/components/CategoryPill';
import { StoryThumbnail } from '@/components/StoryThumbnail';
import { useApp } from '@/state/AppContext';
import { formatMs } from '@/services/audio';
import { colors, radii, shadows, spacing, typography } from '@/theme';

export function AudioScreen() {
  const { briefing, playback, playbackSpeed, cyclePlaybackSpeed, savedStoryIds, toggleSaved } = useApp();
  const b = briefing;
  const isSaved = savedStoryIds.has('briefing-today');
  const currentTime = playback.isLoaded ? formatMs(playback.positionMs) : '00:00';
  const totalDuration = playback.isLoaded ? formatMs(playback.durationMs) : b.totalDuration;

  return (
    <ScreenContainer>
      <AppHeader />

      <View style={styles.titleBlock}>
        <Text style={styles.title}>Audio</Text>
        <Text style={styles.subtitle}>Listen to today's briefing</Text>
      </View>

      <View style={[styles.artwork, shadows.cardSoft]}>
        <BriefingArtwork width={360} height={210} rounded={radii.xl} />
      </View>

      <View style={styles.headerRow}>
        <View style={{ flex: 1 }}>
          <View style={styles.todayBadge}>
            <Text style={styles.todayBadgeText}>TODAY'S BRIEFING</Text>
          </View>
          <Text style={styles.cardTitle}>Today's 10-min Briefing</Text>
          <Text style={styles.desc}>
            Your essential updates on BC, AI, marketing, business, and the world.
          </Text>
        </View>
        <Pressable
          onPress={() => toggleSaved('briefing-today')}
          style={styles.saveBtn}
          hitSlop={6}
        >
          <Feather name={isSaved ? 'check' : 'download'} size={22} color={colors.textPrimary} />
          <Text style={styles.saveLabel}>{isSaved ? 'Saved' : 'Save'}</Text>
        </Pressable>
      </View>

      <AudioPlayer
        currentTime={currentTime}
        totalDuration={totalDuration}
        isSaved={isSaved}
        onSave={() => toggleSaved('briefing-today')}
      />

      <View style={{ marginTop: spacing.lg }}>
        <ChapterList chapters={b.audioChapters} />
      </View>

      <View style={styles.footRow}>
        <Pressable onPress={cyclePlaybackSpeed} style={styles.footBtn}>
          <Feather name="zap" size={16} color={colors.textSecondary} />
          <Text style={styles.footLabel}>Speed</Text>
          <Text style={styles.footValue}>{playbackSpeed.toFixed(2).replace(/0$/, '')}×</Text>
        </Pressable>

        <Pressable style={[styles.footBtn, { backgroundColor: colors.accentBlueSoft }]}>
          <Feather name="file-text" size={16} color={colors.accentBlue} />
          <Text style={[styles.footLabel, { color: colors.accentBlue, fontWeight: '600' }]}>
            View full transcript
          </Text>
        </Pressable>
      </View>

      {b.upNext && (
        <>
          <Text style={[styles.upNextTitle]}>Up next</Text>
          <View style={[styles.upNextCard, shadows.cardSoft]}>
            <StoryThumbnail kind={b.upNext.thumbnailKind} size={64} />
            <View style={{ flex: 1, gap: 4 }}>
              <CategoryPill category={b.upNext.category} />
              <Text style={styles.upHeadline} numberOfLines={2}>
                {b.upNext.headline}
              </Text>
              <Text style={styles.upSummary} numberOfLines={2}>
                {b.upNext.summary}
              </Text>
            </View>
            <Pressable style={styles.upPlay}>
              <Ionicons name="play" size={18} color={colors.lavender} style={{ marginLeft: 2 }} />
            </Pressable>
          </View>
        </>
      )}
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  titleBlock: {
    marginTop: spacing.lg,
    marginBottom: spacing.md,
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
  artwork: {
    borderRadius: radii.xl,
    overflow: 'hidden',
    marginBottom: spacing.lg,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing.md,
    marginBottom: spacing.sm,
  },
  todayBadge: {
    alignSelf: 'flex-start',
    backgroundColor: colors.coral,
    paddingHorizontal: spacing.md,
    paddingVertical: 4,
    borderRadius: radii.pill,
    marginBottom: spacing.sm,
  },
  todayBadgeText: {
    ...typography.pillLabel,
    color: colors.textInverse,
    fontSize: 10,
  },
  cardTitle: {
    ...typography.cardTitle,
    color: colors.textPrimary,
  },
  desc: {
    ...typography.body,
    color: colors.textMuted,
    marginTop: 4,
  },
  saveBtn: {
    width: 56,
    alignItems: 'center',
    paddingTop: 4,
  },
  saveLabel: {
    ...typography.caption,
    color: colors.textSecondary,
    marginTop: 4,
  },
  footRow: {
    flexDirection: 'row',
    gap: spacing.md,
    marginTop: spacing.lg,
  },
  footBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingVertical: spacing.md,
    backgroundColor: colors.surface,
    borderRadius: radii.lg,
    borderWidth: 1,
    borderColor: colors.border,
  },
  footLabel: {
    ...typography.bodySmall,
    color: colors.textSecondary,
    fontWeight: '500',
  },
  footValue: {
    ...typography.bodySmall,
    color: colors.accentBlue,
    fontWeight: '700',
  },
  upNextTitle: {
    ...typography.sectionTitle,
    color: colors.textPrimary,
    marginTop: spacing.xxl,
    marginBottom: spacing.md,
  },
  upNextCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    backgroundColor: colors.surface,
    borderRadius: radii.xl,
    padding: spacing.md,
  },
  upHeadline: {
    ...typography.storyHeadline,
    color: colors.textPrimary,
  },
  upSummary: {
    ...typography.bodySmall,
    color: colors.textMuted,
  },
  upPlay: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.lavenderSoft,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
