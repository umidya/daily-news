import React from 'react';
import { RefreshControlProps, ScrollView, StyleSheet, View, ViewStyle } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors, screenPadding, spacing } from '@/theme';

interface Props {
  children: React.ReactNode;
  scroll?: boolean;
  contentStyle?: ViewStyle;
  bottomInset?: number;
  refreshControl?: React.ReactElement<RefreshControlProps>;
}

export function ScreenContainer({ children, scroll = true, contentStyle, bottomInset = 96, refreshControl }: Props) {
  if (!scroll) {
    return (
      <SafeAreaView edges={['top']} style={styles.safe}>
        <View
          style={[
            styles.content,
            { paddingBottom: bottomInset + spacing.lg },
            contentStyle,
          ]}
        >
          {children}
        </View>
      </SafeAreaView>
    );
  }
  return (
    <SafeAreaView edges={['top']} style={styles.safe}>
      <ScrollView
        contentContainerStyle={[
          styles.content,
          { paddingBottom: bottomInset + spacing.lg },
          contentStyle,
        ]}
        showsVerticalScrollIndicator={false}
        style={styles.scroll}
        refreshControl={refreshControl}
      >
        {children}
      </ScrollView>
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
