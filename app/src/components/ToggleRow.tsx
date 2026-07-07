import React from 'react';
import { Pressable, StyleSheet, Text, View, ViewStyle } from 'react-native';
import { colors, radii, spacing, typography } from '@/theme';

interface Props {
  title: string;
  subtitle?: string;
  value: boolean;
  onToggle: (v: boolean) => void;
  tint?: 'lavender' | 'mint' | 'coral' | 'blue';
  containerStyle?: ViewStyle;
}

const TINTS = {
  lavender: colors.lavender,
  mint: colors.mint,
  coral: colors.coral,
  blue: colors.accentBlue,
};

export function ToggleRow({ title, subtitle, value, onToggle, tint = 'lavender', containerStyle }: Props) {
  const color = TINTS[tint];
  return (
    <View style={[styles.row, containerStyle]}>
      <View style={styles.text}>
        <Text style={styles.title}>{title}</Text>
        {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
      </View>
      <Pressable
        onPress={() => onToggle(!value)}
        style={[
          styles.toggle,
          { backgroundColor: value ? color : '#D1D5DB' },
        ]}
      >
        <View style={[styles.knob, value ? styles.knobOn : styles.knobOff]} />
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: spacing.sm,
    gap: spacing.lg,
  },
  text: {
    flex: 1,
  },
  title: {
    ...typography.bodyStrong,
    color: colors.textPrimary,
  },
  subtitle: {
    ...typography.bodySmall,
    color: colors.textMuted,
    marginTop: 2,
  },
  toggle: {
    width: 50,
    height: 30,
    borderRadius: radii.pill,
    padding: 3,
    justifyContent: 'center',
  },
  knob: {
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: '#FFFFFF',
    shadowColor: '#0B1C40',
    shadowOpacity: 0.15,
    shadowRadius: 2,
    shadowOffset: { width: 0, height: 1 },
    elevation: 2,
  },
  knobOn: { alignSelf: 'flex-end' },
  knobOff: { alignSelf: 'flex-start' },
});
