import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { Feather } from '@expo/vector-icons';
import { CategoryPill } from './CategoryPill';
import { StoryThumbnail } from './StoryThumbnail';
import { colors, radii, shadows, spacing, typography } from '@/theme';
import type { Story } from '@/types/news';

interface Props {
  story: Story;
  onPress?: () => void;
  variant?: 'card' | 'flat';
  thumbnailSize?: number;
}

export function StoryCard({ story, onPress, variant = 'card', thumbnailSize = 84 }: Props) {
  const isCard = variant === 'card';
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        isCard ? styles.card : styles.flat,
        isCard && shadows.cardSoft,
        pressed && { opacity: 0.85 },
      ]}
    >
      <StoryThumbnail kind={story.thumbnailKind} size={thumbnailSize} rounded={isCard ? 12 : 14} />
      <View style={styles.body}>
        <CategoryPill category={story.category} />
        <Text style={styles.headline} numberOfLines={2}>
          {story.headline}
        </Text>
        <Text style={styles.summary} numberOfLines={2}>
          {story.summary}
        </Text>
      </View>
      <Feather name="chevron-right" size={20} color={colors.textMuted} style={styles.chevron} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderRadius: radii.xl,
    padding: spacing.md,
    gap: spacing.md,
  },
  flat: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing.md,
    gap: spacing.lg,
  },
  body: {
    flex: 1,
    gap: 6,
  },
  headline: {
    ...typography.storyHeadline,
    color: colors.textPrimary,
  },
  summary: {
    ...typography.bodySmall,
    color: colors.textMuted,
  },
  chevron: {
    marginLeft: spacing.xs,
  },
});
