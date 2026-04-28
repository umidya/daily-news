import React from 'react';
import { ScrollView, StyleSheet, View, ViewStyle } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors, screenPadding, spacing } from '@/theme';

interface Props {
  children: React.ReactNode;
  scroll?: boolean;
  contentStyle?: ViewStyle;
  bottomInset?: number;
}

export function ScreenContainer({ children, scroll = true, contentStyle, bottomInset = 96 }: Props) {
  const Inner = scroll ? ScrollView : View;
  return (
    <SafeAreaView edges={['top']} style={styles.safe}>
      <Inner
        contentContainerStyle={[
          styles.content,
          { paddingBottom: bottomInset + spacing.lg },
          contentStyle,
        ]}
        showsVerticalScrollIndicator={false}
        style={scroll ? styles.scroll : undefined}
      >
        {children}
      </Inner>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: colors.background,
  },
  scroll: {
    flex: 1,
  },
  content: {
    paddingHorizontal: screenPadding,
    paddingTop: spacing.sm,
  },
});
