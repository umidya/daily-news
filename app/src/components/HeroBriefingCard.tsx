import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { BriefingArtwork } from './BriefingArtwork';
import { useApp } from '@/state/AppContext';
import { colors, radii, shadows, spacing, typography } from '@/theme';

interface Props {
  totalDuration: string;
  currentTime: string;
  remaining: string;
  hookCopy: string;
}

export function HeroBriefingCard({ totalDuration, currentTime, remaining, hookCopy }: Props) {
  const { playback, togglePlay } = useApp();
  const isPlaying = playback.isPlaying;

  const progress = useProgressFromTimes(currentTime, totalDuration);

  return (
    <View style={[styles.card, shadows.card]}>
      <LinearGradient
        colors={[...colors.heroGradient]}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={StyleSheet.absoluteFill}
      />

      <View style={styles.artworkWrap} pointerEvents="none">
        <BriefingArtwork width={220} height={220} rounded={0} />
      </View>

      <View style={styles.contentRow}>
        <View style={styles.todayBadge}>
          <Text style={styles.todayBadgeText}>TODAY'S</Text>
        </View>

        <Text style={styles.title}>10-min Briefing</Text>
        <Text style={styles.copy}>{hookCopy}</Text>

        <View style={styles.playRow}>
          <Pressable onPress={togglePlay} style={({ pressed }) => [styles.playBtn, shadows.play, pressed && styles.playBtnPressed]}>
            <Ionicons
              name={isPlaying ? 'pause' : 'play'}
              size={26}
              color={colors.textInverse}
              style={!isPlaying ? { marginLeft: 3 } : undefined}
            />
          </Pressable>
          <View style={styles.progressArea}>
            <Text style={styles.timeText}>
              {currentTime} / {totalDuration}
            </Text>
            <View style={styles.progressTrack}>
              <View style={[styles.progressFill, { width: `${progress * 100}%` }]} />
              <View style={[styles.progressKnob, { left: `${progress * 100}%` }]} />
            </View>
            <Text style={styles.remaining}>{remaining}</Text>
          </View>
        </View>
      </View>
    </View>
  );
}

function useProgressFromTimes(curr: string, total: string) {
  const cs = parseTime(curr);
  const ts = parseTime(total);
  if (!ts) return 0;
  return Math.min(1, Math.max(0, cs / ts));
}

function parseTime(t: string) {
  const [m, s] = t.split(':').map(Number);
  return (m || 0) * 60 + (s || 0);
}

const styles = StyleSheet.create({
  card: {
    borderRadius: radii.xxl,
    overflow: 'hidden',
    backgroundColor: '#FBE5DA',
    minHeight: 230,
  },
  artworkWrap: {
    position: 'absolute',
    right: -20,
    top: 0,
    bottom: 0,
    opacity: 0.95,
  },
  contentRow: {
    padding: spacing.xl,
    paddingRight: spacing.xxl,
  },
  todayBadge: {
    alignSelf: 'flex-start',
    backgroundColor: colors.coral,
    paddingHorizontal: spacing.md,
    paddingVertical: 4,
    borderRadius: radii.pill,
    marginBottom: spacing.md,
  },
  todayBadgeText: {
    ...typography.pillLabel,
    color: colors.textInverse,
    fontSize: 10,
  },
  title: {
    ...typography.heroTitle,
    color: colors.textPrimary,
    marginBottom: spacing.xs,
  },
  copy: {
    ...typography.body,
    color: colors.textSecondary,
    maxWidth: '70%',
    marginBottom: spacing.lg,
  },
  playRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
  },
  playBtn: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: colors.coral,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 4,
    borderColor: '#FFFFFFE6',
  },
  playBtnPressed: {
    transform: [{ scale: 0.95 }],
  },
  progressArea: {
    flex: 1,
    paddingTop: 2,
  },
  timeText: {
    ...typography.bodyStrong,
    color: colors.textPrimary,
    marginBottom: 6,
  },
  progressTrack: {
    height: 4,
    backgroundColor: '#FFFFFFAA',
    borderRadius: 2,
    overflow: 'visible',
    marginBottom: 6,
    position: 'relative',
  },
  progressFill: {
    height: 4,
    backgroundColor: colors.coral,
    borderRadius: 2,
  },
  progressKnob: {
    position: 'absolute',
    top: -3,
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: colors.coral,
    marginLeft: -5,
    borderWidth: 2,
    borderColor: '#FFFFFF',
  },
  remaining: {
    ...typography.bodySmall,
    color: colors.textSecondary,
  },
});
