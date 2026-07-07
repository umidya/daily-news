import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { Feather } from '@expo/vector-icons';
import Svg, { Rect } from 'react-native-svg';
import { colors, radii, spacing, typography } from '@/theme';
import type { Voice } from '@/types/news';

interface Props {
  voice: Voice;
  selected: boolean;
  onPress: () => void;
}

const TINTS: Record<Voice['id'], string> = {
  onyx: colors.lavender,
  nova: colors.coral,
  alloy: colors.mint,
};

export function VoiceCard({ voice, selected, onPress }: Props) {
  const tint = TINTS[voice.id];
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        styles.card,
        selected && styles.cardSelected,
        pressed && { opacity: 0.95 },
      ]}
    >
      <View style={styles.row}>
        <View style={[styles.playIcon, { backgroundColor: selected ? tint : '#E5E7EB' }]}>
          <Feather name="play" size={12} color={selected ? '#FFFFFF' : colors.textPrimary} style={{ marginLeft: 1 }} />
        </View>
        <Waveform tint={tint} active={selected} />
        {selected && (
          <View style={styles.checkBubble}>
            <Feather name="check" size={12} color="#FFFFFF" />
          </View>
        )}
      </View>
      <Text style={styles.name}>{voice.name}</Text>
      <Text style={styles.desc}>{voice.description}</Text>
    </Pressable>
  );
}

function Waveform({ tint, active }: { tint: string; active: boolean }) {
  const heights = [6, 12, 8, 16, 10, 18, 8, 14, 6, 10, 14, 8];
  return (
    <Svg width={66} height={20} viewBox="0 0 66 20">
      {heights.map((h, i) => (
        <Rect
          key={i}
          x={i * 5.5}
          y={(20 - h) / 2}
          width={3}
          height={h}
          rx={1.5}
          fill={tint}
          opacity={active ? 0.85 : 0.35}
        />
      ))}
    </Svg>
  );
}

const styles = StyleSheet.create({
  card: {
    flex: 1,
    backgroundColor: colors.surface,
    borderRadius: radii.lg,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
    minWidth: 100,
  },
  cardSelected: {
    borderColor: colors.lavender,
    borderWidth: 2,
    backgroundColor: '#F8F4FF',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: spacing.sm,
    position: 'relative',
  },
  playIcon: {
    width: 22,
    height: 22,
    borderRadius: 11,
    alignItems: 'center',
    justifyContent: 'center',
  },
  checkBubble: {
    position: 'absolute',
    top: -10,
    right: -6,
    width: 18,
    height: 18,
    borderRadius: 9,
    backgroundColor: colors.lavender,
    alignItems: 'center',
    justifyContent: 'center',
  },
  name: {
    ...typography.bodyStrong,
    color: colors.textPrimary,
  },
  desc: {
    ...typography.bodySmall,
    color: colors.textMuted,
    marginTop: 2,
  },
});
