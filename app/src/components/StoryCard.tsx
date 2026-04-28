import React from 'react';
import { Linking, Pressable, StyleSheet, Text, View } from 'react-native';
import { Feather, Ionicons } from '@expo/vector-icons';
import { CategoryPill } from './CategoryPill';
import { StoryThumbnail } from './StoryThumbnail';
import { useApp } from '@/state/AppContext';
import { colors, radii, shadows, spacing, typography } from '@/theme';
import type { Story } from '@/types/news';

interface Props {
  story: Story;
  onPress?: () => void;
  variant?: 'card' | 'flat';
  thumbnailSize?: number;
  showBookmark?: boolean;
}

export function StoryCard({ story, onPress, variant = 'card', thumbnailSize = 84, showBookmark = true }: Props) {
  const isCard = variant === 'card';
  const { savedStoryIds, toggleSaved } = useApp();
  const isSaved = savedStoryIds.has(story.id);

  const handlePress = () => {
    if (onPress) {
      onPress();
      return;
    }
    if (story.url) {
      Linking.openURL(story.url).catch(() => {});
    }
  };

  return (
    <Pressable
      onPress={handlePress}
      style={({ pressed }) => [
        isCard ? styles.card : styles.flat,
        isCard && shadows.cardSoft,
        pressed && { opacity: 0.85 },
      ]}
    >
      <StoryThumbnail
        kind={story.thumbnailKind}
        size={thumbnailSize}
        rounded={isCard ? 12 : 14}
        imageUrl={story.imageUrl}
      />
      <View style={styles.body}>
        <CategoryPill category={story.category} />
        <Text style={styles.headline} numberOfLines={2}>
          {story.headline}
        </Text>
        <Text style={styles.summary} numberOfLines={2}>
          {story.summary}
        </Text>
      </View>
      {showBookmark ? (
        <Pressable
          onPress={(e) => {
            e.stopPropagation?.();
            toggleSaved(story);
          }}
          hitSlop={10}
          style={styles.bookmarkBtn}
        >
          <Ionicons
            name={isSaved ? 'bookmark' : 'bookmark-outline'}
            size={22}
            color={isSaved ? colors.lavender : colors.textMuted}
          />
        </Pressable>
      ) : (
        <Feather name="chevron-right" size={20} color={colors.textMuted} style={styles.chevron} />
      )}
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
  bookmarkBtn: {
    padding: spacing.xs,
    marginLeft: spacing.xs,
  },
});
