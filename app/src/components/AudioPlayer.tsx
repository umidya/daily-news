import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { useApp } from '@/state/AppContext';
import { colors, radii, shadows, spacing, typography } from '@/theme';

interface Props {
  currentTime: string;
  totalDuration: string;
  onSave?: () => void;
  isSaved?: boolean;
}

export function AudioPlayer({ currentTime, totalDuration, onSave, isSaved }: Props) {
  const { playback, togglePlay, skipBack, skipForward } = useApp();
  const isPlaying = playback.isPlaying;
  const progress = progressFrom(currentTime, totalDuration);

  return (
    <View>
      <View style={styles.controlsRow}>
        <Pressable onPress={skipBack} style={styles.circleBtn} hitSlop={6}>
          <MaterialCommunityIcons name="rewind-15" size={26} color={colors.textPrimary} />
        </Pressable>

        <Pressable onPress={togglePlay} style={({ pressed }) => [styles.playBtn, shadows.play, pressed && { transform: [{ scale: 0.96 }] }]}>
          <Ionicons
            name={isPlaying ? 'pause' : 'play'}
            size={36}
            color={colors.textInverse}
            style={!isPlaying ? { marginLeft: 4 } : undefined}
          />
        </Pressable>

        <Pressable onPress={skipForward} style={styles.circleBtn} hitSlop={6}>
          <MaterialCommunityIcons name="fast-forward-30" size={26} color={colors.textPrimary} />
        </Pressable>
      </View>

      <View style={styles.progressRow}>
        <Text style={styles.time}>{currentTime}</Text>
        <View style={styles.track}>
          <View style={[styles.fill, { width: `${progress * 100}%` }]} />
          <View style={[styles.knob, { left: `${progress * 100}%` }]} />
        </View>
        <Text style={styles.time}>{totalDuration}</Text>
      </View>
    </View>
  );
}

function progressFrom(curr: string, total: string) {
  const [cm, cs] = curr.split(':').map(Number);
  const [tm, ts] = total.split(':').map(Number);
  const c = (cm || 0) * 60 + (cs || 0);
  const t = (tm || 0) * 60 + (ts || 0);
  if (!t) return 0;
  return Math.min(1, Math.max(0, c / t));
}

const styles = StyleSheet.create({
  controlsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.xxxl,
    paddingVertical: spacing.lg,
  },
  circleBtn: {
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: colors.surfaceTint,
    alignItems: 'center',
    justifyContent: 'center',
  },
  playBtn: {
    width: 84,
    height: 84,
    borderRadius: 42,
    backgroundColor: colors.coral,
    alignItems: 'center',
    justifyContent: 'center',
  },
  progressRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    paddingTop: spacing.sm,
  },
  time: {
    ...typography.bodySmall,
    color: colors.textPrimary,
    fontWeight: '600',
    width: 44,
    textAlign: 'center',
  },
  track: {
    flex: 1,
    height: 4,
    backgroundColor: colors.borderSoft,
    borderRadius: 2,
    position: 'relative',
  },
  fill: {
    height: 4,
    backgroundColor: colors.coral,
    borderRadius: 2,
  },
  knob: {
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
});
