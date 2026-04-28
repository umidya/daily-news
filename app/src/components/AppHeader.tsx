import React from 'react';
import { StyleSheet, Text, View, ViewStyle } from 'react-native';
import { SunriseLogo } from './SunriseLogo';
import { colors, spacing, typography } from '@/theme';

interface Props {
  style?: ViewStyle;
  // Kept for API stability — bell was removed but callers may still pass these.
  showBell?: boolean;
  hasNotifications?: boolean;
  onBellPress?: () => void;
}

export function AppHeader({ style }: Props) {
  return (
    <View style={[styles.row, style]}>
      <View style={styles.brand}>
        <SunriseLogo size={36} />
        <Text style={styles.brandText}>Daily News</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingTop: spacing.sm,
  },
  brand: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  brandText: {
    ...typography.sectionTitle,
    color: colors.textPrimary,
    fontSize: 22,
  },
});
