import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { Feather } from '@expo/vector-icons';
import { colors, radii, spacing, typography } from '@/theme';

interface BaseProps {
  label: string;
  onPress?: () => void;
}

export function TopicChip({ label, selected, onPress }: BaseProps & { selected: boolean }) {
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        styles.chip,
        selected ? styles.chipSelected : styles.chipUnselected,
        pressed && { opacity: 0.8 },
      ]}
    >
      <Text style={[styles.label, { color: selected ? colors.accentBlue : colors.textPrimary }]}>{label}</Text>
      {selected ? (
        <Feather name="check" size={14} color={colors.accentBlue} />
      ) : (
        <Feather name="plus" size={14} color={colors.accentBlue} />
      )}
    </Pressable>
  );
}

export function MutedTopicChip({ label, onRemove }: { label: string; onRemove: () => void }) {
  return (
    <View style={styles.muted}>
      <Text style={[styles.label, { color: colors.coral }]}>{label}</Text>
      <Pressable onPress={onRemove} hitSlop={6}>
        <Feather name="x" size={14} color={colors.coral} />
      </Pressable>
    </View>
  );
}

export function AddTopicChip({ onPress }: { onPress?: () => void }) {
  return (
    <Pressable onPress={onPress} style={({ pressed }) => [styles.add, pressed && { opacity: 0.7 }]}>
      <Feather name="plus" size={14} color={colors.textSecondary} />
      <Text style={[styles.label, { color: colors.textSecondary }]}>Add topic</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: spacing.md,
    paddingVertical: 8,
    borderRadius: radii.pill,
    borderWidth: 1,
  },
  chipSelected: {
    backgroundColor: colors.accentBlueSoft,
    borderColor: colors.accentBlueSoft,
  },
  chipUnselected: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
  },
  muted: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: spacing.md,
    paddingVertical: 8,
    borderRadius: radii.pill,
    backgroundColor: colors.coralSoft,
  },
  add: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: spacing.md,
    paddingVertical: 8,
    borderRadius: radii.pill,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
  },
  label: {
    ...typography.bodySmall,
    fontWeight: '600',
  },
});
