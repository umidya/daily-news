import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { Feather } from '@expo/vector-icons';
import Svg, { Defs, LinearGradient, Path, Rect, Stop } from 'react-native-svg';
import { colors, radii, shadows, spacing, typography } from '@/theme';

interface Props {
  intro: string;
  readingTime: string;
  onPress?: () => void;
}

export function DigestPreviewCard({ intro, readingTime, onPress }: Props) {
  return (
    <Pressable onPress={onPress} style={({ pressed }) => [styles.card, shadows.cardSoft, pressed && { opacity: 0.95 }]}>
      <View style={styles.row}>
        <View style={styles.body}>
          <Text style={styles.copy}>{intro}</Text>
          <View style={styles.readPill}>
            <Feather name="clock" size={12} color={colors.lavender} />
            <Text style={styles.readPillText}>{readingTime}</Text>
          </View>
        </View>
        <DigestDoodle />
      </View>
    </Pressable>
  );
}

function DigestDoodle() {
  return (
    <Svg width={88} height={104} viewBox="0 0 88 104">
      <Defs>
        <LinearGradient id="doc" x1="0" y1="0" x2="0" y2="1">
          <Stop offset="0" stopColor="#FFFFFF" />
          <Stop offset="1" stopColor="#EFEAFF" />
        </LinearGradient>
      </Defs>
      <Path d="M14 6 L62 6 L80 24 L80 92 L14 92 Z" fill="url(#doc)" stroke="#C9B8FF" strokeWidth={1} />
      <Path d="M62 6 L62 24 L80 24 Z" fill="#EFEAFF" />
      <Rect x="22" y="34" width="46" height="3" rx="1.5" fill="#8B6CFF" opacity={0.7} />
      <Rect x="22" y="42" width="38" height="3" rx="1.5" fill="#8B6CFF" opacity={0.5} />
      <Rect x="22" y="50" width="46" height="3" rx="1.5" fill="#8B6CFF" opacity={0.4} />
      <Rect x="22" y="58" width="32" height="3" rx="1.5" fill="#8B6CFF" opacity={0.3} />
      <Rect x="60" y="76" width="14" height="14" rx="3" fill="#8B6CFF" />
      <Path d="M64 84 L66 86 L70 80" stroke="#FFFFFF" strokeWidth={1.5} fill="none" />
    </Svg>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.lavenderSoft,
    borderRadius: radii.xl,
    padding: spacing.lg,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
  },
  body: {
    flex: 1,
    paddingRight: spacing.sm,
  },
  copy: {
    ...typography.body,
    color: colors.textPrimary,
    marginBottom: spacing.md,
  },
  readPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    alignSelf: 'flex-start',
    backgroundColor: '#FFFFFFC0',
    paddingHorizontal: spacing.sm + 2,
    paddingVertical: 4,
    borderRadius: radii.pill,
  },
  readPillText: {
    ...typography.caption,
    color: colors.lavender,
  },
});
