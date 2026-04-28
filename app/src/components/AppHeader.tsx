import React from 'react';
import { Pressable, StyleSheet, Text, View, ViewStyle } from 'react-native';
import { Feather } from '@expo/vector-icons';
import { SunriseLogo } from './SunriseLogo';
import { colors, radii, spacing, typography } from '@/theme';

interface Props {
  showBell?: boolean;
  hasNotifications?: boolean;
  style?: ViewStyle;
  onBellPress?: () => void;
}

export function AppHeader({ showBell = true, hasNotifications = true, style, onBellPress }: Props) {
  return (
    <View style={[styles.row, style]}>
      <View style={styles.brand}>
        <SunriseLogo size={36} />
        <Text style={styles.brandText}>Daily News</Text>
      </View>
      {showBell && (
        <Pressable onPress={onBellPress} hitSlop={10} style={styles.bellWrap}>
          <Feather name="bell" size={22} color={colors.textPrimary} />
          {hasNotifications && <View style={styles.dot} />}
        </Pressable>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
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
  bellWrap: {
    width: 36,
    height: 36,
    borderRadius: radii.pill,
    alignItems: 'center',
    justifyContent: 'center',
  },
  dot: {
    position: 'absolute',
    top: 6,
    right: 6,
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.coral,
    borderWidth: 1.5,
    borderColor: colors.surface,
  },
});
