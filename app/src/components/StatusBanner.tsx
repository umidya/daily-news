import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { Feather } from '@expo/vector-icons';
import { colors, spacing, typography } from '@/theme';

/**
 * Slim inline notice for degraded states: a stale briefing being shown as
 * "today's", or an audio playback failure. Neutral amber styling — a heads-up,
 * not an alarm.
 */
export function StatusBanner({ message }: { message: string }) {
  return (
    <View style={styles.banner}>
      <Feather name="alert-circle" size={14} color="#8A5A00" style={styles.icon} />
      <Text style={styles.text}>{message}</Text>
    </View>
  );
}

/** True when the briefing payload is not for the device's current date. */
export function briefingIsStale(dateIso?: string): boolean {
  if (!dateIso) return false; // mock/legacy payloads — nothing to compare
  const now = new Date();
  const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(
    now.getDate(),
  ).padStart(2, '0')}`;
  return dateIso !== today;
}

const styles = StyleSheet.create({
  banner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.warmYellowSoft,
    borderRadius: 12,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    marginBottom: spacing.md,
  },
  icon: {
    marginRight: spacing.sm,
  },
  text: {
    ...typography.caption,
    color: '#8A5A00',
    flex: 1,
  },
});
