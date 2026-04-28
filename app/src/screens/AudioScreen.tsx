import React, { useState } from 'react';
import { Linking, Modal, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
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
  const {
    briefing,
    playback,
    playbackSpeed,
    cyclePlaybackSpeed,
    seekTo,
    togglePlay,
    savedStoryIds,
    toggleSaved,
  } = useApp();
  const b = briefing;
  const [transcriptOpen, setTranscriptOpen] = useState(false);
  const upSaved = b.upNext ? savedStoryIds.has(b.upNext.id) : false;
  const currentTime = playback.isLoaded ? formatMs(playback.positionMs) : '00:00';
  const totalDuration = playback.isLoaded ? formatMs(playback.durationMs) : b.totalDuration;

  const handleChapterPress = (chapterId: string) => {
    const chapter = b.audioChapters.find((c) => c.id === chapterId);
    if (!chapter || chapter.startSeconds == null) return;
    void seekTo(chapter.startSeconds * 1000);
    if (!playback.isPlaying) void togglePlay();
  };

  const handleUpNextPress = () => {
    if (b.upNext?.url) Linking.openURL(b.upNext.url).catch(() => {});
  };

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
          <Text style={styles.cardTitle}>Today's Briefing</Text>
          <Text style={styles.desc}>
            Your essential updates on BC, AI, marketing, business, and the world.
          </Text>
        </View>
      </View>

      <AudioPlayer currentTime={currentTime} totalDuration={totalDuration} />

      <View style={{ marginTop: spacing.lg }}>
        <ChapterList chapters={b.audioChapters} onChapterPress={handleChapterPress} />
      </View>

      <View style={styles.footRow}>
        <Pressable onPress={cyclePlaybackSpeed} style={styles.footBtn}>
          <Feather name="zap" size={16} color={colors.textSecondary} />
          <Text style={styles.footLabel}>Speed</Text>
          <Text style={styles.footValue}>{playbackSpeed.toFixed(2).replace(/0$/, '')}×</Text>
        </Pressable>

        <Pressable
          onPress={() => setTranscriptOpen(true)}
          style={[styles.footBtn, { backgroundColor: colors.accentBlueSoft }]}
        >
          <Feather name="file-text" size={16} color={colors.accentBlue} />
          <Text style={[styles.footLabel, { color: colors.accentBlue, fontWeight: '600' }]}>
            View full transcript
          </Text>
        </Pressable>
      </View>

      {b.upNext && (
        <>
          <Text style={[styles.upNextTitle]}>Up next</Text>
          <Pressable
            onPress={handleUpNextPress}
            style={({ pressed }) => [styles.upNextCard, shadows.cardSoft, pressed && { opacity: 0.85 }]}
          >
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
            <Pressable
              onPress={(e) => {
                e.stopPropagation?.();
                if (b.upNext) toggleSaved(b.upNext);
              }}
              hitSlop={10}
              style={styles.upBookmark}
            >
              <Ionicons
                name={upSaved ? 'bookmark' : 'bookmark-outline'}
                size={20}
                color={upSaved ? colors.lavender : colors.textMuted}
              />
            </Pressable>
          </Pressable>
        </>
      )}

      <TranscriptModal
        open={transcriptOpen}
        onClose={() => setTranscriptOpen(false)}
        text={b.audioScript ?? b.whyItMatters}
        date={b.date}
      />
    </ScreenContainer>
  );
}

function TranscriptModal({
  open,
  onClose,
  text,
  date,
}: {
  open: boolean;
  onClose: () => void;
  text: string;
  date: string;
}) {
  return (
    <Modal visible={open} animationType="slide" presentationStyle="pageSheet" onRequestClose={onClose}>
      <View style={modalStyles.container}>
        <View style={modalStyles.header}>
          <Pressable onPress={onClose} hitSlop={10} style={modalStyles.iconBtn}>
            <Feather name="x" size={24} color={colors.textPrimary} />
          </Pressable>
          <Text style={modalStyles.headerTitle}>Transcript</Text>
          <View style={{ width: 36 }} />
        </View>
        <ScrollView contentContainerStyle={modalStyles.body} showsVerticalScrollIndicator={false}>
          <Text style={modalStyles.date}>{date}</Text>
          <Text style={modalStyles.text}>{text}</Text>
        </ScrollView>
      </View>
    </Modal>
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
  upBookmark: {
    padding: spacing.xs,
  },
});

const modalStyles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.lg,
    paddingBottom: spacing.md,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.divider,
  },
  iconBtn: {
    width: 36,
    height: 36,
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerTitle: {
    ...typography.cardTitle,
    fontSize: 20,
    color: colors.textPrimary,
  },
  body: {
    padding: spacing.xl,
    paddingBottom: spacing.huge,
  },
  date: {
    ...typography.bodySmall,
    color: colors.textMuted,
    marginBottom: spacing.md,
  },
  text: {
    ...typography.body,
    color: colors.textPrimary,
    lineHeight: 24,
    fontSize: 16,
  },
});
