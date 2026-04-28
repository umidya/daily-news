import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { Feather } from '@expo/vector-icons';
import { AppHeader } from '@/components/AppHeader';
import { ScreenContainer } from '@/components/ScreenContainer';
import { StoryCard } from '@/components/StoryCard';
import { useApp } from '@/state/AppContext';
import { colors, radii, spacing, typography } from '@/theme';

export function SavedScreen() {
  const { savedStories } = useApp();
  const saved = savedStories;

  return (
    <ScreenContainer>
      <AppHeader />

      <View style={styles.titleBlock}>
        <Text style={styles.title}>Saved</Text>
        <Text style={styles.subtitle}>Stories you've bookmarked for later.</Text>
      </View>

      {saved.length === 0 ? (
        <View style={styles.empty}>
          <View style={styles.emptyIcon}>
            <Feather name="bookmark" size={28} color={colors.lavender} />
          </View>
          <Text style={styles.emptyTitle}>Nothing saved yet</Text>
          <Text style={styles.emptyBody}>
            Tap the bookmark on any story or briefing and it lands here for later.
          </Text>
        </View>
      ) : (
        <View style={{ gap: spacing.md }}>
          {saved.map((s) => (
            <StoryCard key={s.id} story={s} />
          ))}
        </View>
      )}
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  titleBlock: {
    marginTop: spacing.lg,
    marginBottom: spacing.lg,
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
  empty: {
    backgroundColor: colors.surface,
    borderRadius: radii.xl,
    padding: spacing.xxl,
    alignItems: 'center',
    marginTop: spacing.lg,
    gap: spacing.md,
  },
  emptyIcon: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: colors.lavenderSoft,
    alignItems: 'center',
    justifyContent: 'center',
  },
  emptyTitle: {
    ...typography.cardTitle,
    fontSize: 20,
    color: colors.textPrimary,
  },
  emptyBody: {
    ...typography.body,
    color: colors.textMuted,
    textAlign: 'center',
    maxWidth: 260,
  },
});
