import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { Feather } from '@expo/vector-icons';
import { categoryStyles } from '@/theme/colors';
import { colors, radii, shadows, spacing, typography } from '@/theme';
import type { Chapter } from '@/types/news';

interface Props {
  chapters: Chapter[];
  onChapterPress?: (id: string) => void;
}

export function ChapterList({ chapters, onChapterPress }: Props) {
  return (
    <View style={[styles.card, shadows.cardSoft]}>
      {chapters.map((c, i) => (
        <Pressable
          key={c.id}
          onPress={() => onChapterPress?.(c.id)}
          style={({ pressed }) => [styles.row, i < chapters.length - 1 && styles.rowDivider, pressed && { opacity: 0.7 }]}
        >
          <View style={styles.left}>
            <View style={[styles.dot, { backgroundColor: categoryStyles[c.title].dot }]} />
            <Text style={styles.title}>{c.title}</Text>
          </View>
          <View style={styles.right}>
            <Text style={styles.duration}>{c.duration}</Text>
            <Feather name="chevron-right" size={18} color={colors.textMuted} />
          </View>
        </Pressable>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderRadius: radii.xl,
    paddingHorizontal: spacing.lg,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: spacing.md + 2,
  },
  rowDivider: {
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.divider,
  },
  left: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
  },
  dot: {
    width: 10,
    height: 10,
    borderRadius: 5,
  },
  title: {
    ...typography.bodyStrong,
    color: colors.textPrimary,
  },
  right: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  duration: {
    ...typography.monoTime,
    color: colors.textSecondary,
  },
});
