import React, { useState } from 'react';
import { GestureResponderEvent, LayoutChangeEvent, Pressable, StyleSheet, Text, View } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Image } from 'expo-image';
import { Ionicons } from '@expo/vector-icons';
import { BriefingArtwork } from './BriefingArtwork';
import { useApp } from '@/state/AppContext';
import { colors, radii, shadows, spacing, typography } from '@/theme';

interface Props {
  totalDuration: string;
  currentTime: string;
  remaining: string;
  hookCopy: string;
  heroImageUrl?: string;
}

export function HeroBriefingCard({ totalDuration, currentTime, remaining, hookCopy, heroImageUrl }: Props) {
  const { playback, togglePlay, seekTo } = useApp();
  const isPlaying = playback.isPlaying;
  const [trackWidth, setTrackWidth] = useState(0);
  const [imageFailed, setImageFailed] = useState(false);

  const progress = useProgressFromTimes(currentTime, totalDuration);

  const onTrackLayout = (e: LayoutChangeEvent) => setTrackWidth(e.nativeEvent.layout.width);

  const onTrackPress = (e: GestureResponderEvent) => {
    if (!trackWidth || !playback.durationMs) return;
    const ratio = Math.max(0, Math.min(1, e.nativeEvent.locationX / trackWidth));
    void seekTo(ratio * playback.durationMs);
  };

  const showPhoto = heroImageUrl && !imageFailed;

  return (
    <View style={[styles.card, shadows.card]}>
      {showPhoto ? (
        <Image
          source={{ uri: heroImageUrl }}
          style={StyleSheet.absoluteFillObject}
          contentFit="cover"
          transition={200}
          onError={() => setImageFailed(true)}
        />
      ) : (
        <BriefingArtwork width={680} height={260} rounded={0} />
      )}

      {/* Scrim for text readability — stronger when over a photo */}
      <LinearGradient
        colors={
          showPhoto
            ? ["#0B1530E6", "#0B153099", "#0B153040"]
            : ["#FFE4D6F0", "#FFE4D680", "#FFE4D600"]
        }
        start={{ x: 0, y: 1 }}
        end={{ x: 1, y: 0 }}
        style={StyleSheet.absoluteFill}
        pointerEvents="none"
      />

      <View style={styles.content}>
        <View style={styles.todayBadge}>
          <Text style={styles.todayBadgeText}>TODAY'S</Text>
        </View>
        <Text style={[styles.title, showPhoto && styles.titleOnPhoto]}>Briefing</Text>
        <Text style={[styles.copy, showPhoto && styles.copyOnPhoto]} numberOfLines={2}>{hookCopy}</Text>

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
            <Text style={[styles.timeText, showPhoto && styles.timeTextOnPhoto]}>
              {currentTime} / {totalDuration}
            </Text>
            <Pressable onPress={onTrackPress} onLayout={onTrackLayout} style={styles.progressTouchTarget} hitSlop={{ top: 8, bottom: 8 }}>
              <View style={styles.progressTrack}>
                <View style={[styles.progressFill, { width: `${progress * 100}%` }]} />
                <View style={[styles.progressKnob, { left: `${progress * 100}%` }]} />
              </View>
            </Pressable>
            <Text style={[styles.remaining, showPhoto && styles.remainingOnPhoto]}>{remaining}</Text>
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
  content: {
    padding: spacing.xl,
    paddingRight: spacing.xxl,
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
  title: {
    ...typography.heroTitle,
    color: colors.textPrimary,
    marginBottom: spacing.xs,
    fontSize: 34,
  },
  titleOnPhoto: {
    color: '#FFFFFF',
    textShadowColor: '#000000AA',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 4,
  },
  copy: {
    ...typography.body,
    color: colors.textPrimary,
    maxWidth: '75%',
    marginBottom: spacing.lg,
    fontWeight: '500',
    textShadowColor: '#FFFFFF99',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 1,
  },
  copyOnPhoto: {
    color: '#F0F4FF',
    textShadowColor: '#000000AA',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 3,
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
  timeTextOnPhoto: {
    color: '#FFFFFF',
    textShadowColor: '#000000AA',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 3,
  },
  progressTouchTarget: {
    paddingVertical: 6,
    marginBottom: 0,
  },
  progressTrack: {
    height: 4,
    backgroundColor: '#FFFFFFCC',
    borderRadius: 2,
    overflow: 'visible',
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
    color: colors.textPrimary,
    marginTop: 6,
    fontWeight: '500',
  },
  remainingOnPhoto: {
    color: '#F0F4FF',
    textShadowColor: '#000000AA',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 3,
  },
});
