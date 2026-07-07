import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { categoryStyles, type CategoryName } from '@/theme/colors';
import { radii, spacing, typography } from '@/theme';

interface Props {
  category: CategoryName;
  size?: 'sm' | 'md';
}

export function CategoryPill({ category, size = 'sm' }: Props) {
  const s = categoryStyles[category];
  return (
    <View
      style={[
        styles.pill,
        { backgroundColor: s.bg, paddingVertical: size === 'md' ? 6 : 4, paddingHorizontal: size === 'md' ? 12 : 10 },
      ]}
    >
      <Text style={[typography.pillLabel, { color: s.text }]}>
        {category.toUpperCase()}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  pill: {
    alignSelf: 'flex-start',
    borderRadius: radii.pill,
  },
});
