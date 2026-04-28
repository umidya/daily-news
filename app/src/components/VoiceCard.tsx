import React, { useEffect, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { Feather } from '@expo/vector-icons';
import Svg, { Rect } from 'react-native-svg';
import { voiceSampleUrl } from '@/config';
import { playVoiceSample, subscribeSamplePlaying } from '@/services/audio';
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
  const [playingId, setPlayingId] = useState<string | null>(null);
  const isPlaying = playingId === voice.id;

  useEffect(() => subscribeSamplePlaying(setPlayingId), []);

  const handleSample = async () => {
    const url = voiceSampleUrl(voice.id);
    if (!url) return;
    await playVoiceSample(voice.id, url);
  };

  const handleCardPress = () => {
    onPress();
    void handleSample();
  };

  return (
    <Pressable
      onPress={handleCardPress}
      style={({ pressed }) => [
        styles.card,
        selected && styles.cardSelected,
        pressed && { opacity: 0.95 },
      ]}
    >
      <View style={styles.row}>
        <Pressable
          onPress={handleSample}
          hitSlop={8}
          style={[styles.playIcon, { backgroundColor: selected || isPlaying ? tint : '#E5E7EB' }]}
        >
          <Feather
            name={isPlaying ? 'pause' : 'play'}
            size={12}
            color={selected || isPlaying ? '#FFFFFF' : colors.textPrimary}
            style={!isPlaying ? { marginLeft: 1 } : undefined}
          />
        </Pressable>
        <Waveform tint={tint} active={selected || isPlaying} />
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
