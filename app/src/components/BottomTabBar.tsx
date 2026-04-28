import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { Feather } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useApp } from '@/state/AppContext';
import { colors, shadows, spacing, typography } from '@/theme';
import type { TabKey } from '@/types/news';

const TABS: Array<{ key: TabKey; label: string; icon: keyof typeof Feather.glyphMap }> = [
  { key: 'home', label: 'Home', icon: 'home' },
  { key: 'audio', label: 'Audio', icon: 'headphones' },
  { key: 'digest', label: 'Digest', icon: 'file-text' },
  { key: 'saved', label: 'Saved', icon: 'bookmark' },
  { key: 'settings', label: 'Settings', icon: 'settings' },
];

export function BottomTabBar() {
  const { activeTab, setActiveTab } = useApp();
  return (
    <SafeAreaView edges={['bottom']} style={styles.safe}>
      <View style={[styles.bar, shadows.tabBar]}>
        {TABS.map((t) => {
          const active = t.key === activeTab;
          return (
            <Pressable
              key={t.key}
              onPress={() => setActiveTab(t.key)}
              style={styles.item}
              hitSlop={6}
            >
              <Feather name={t.icon} size={22} color={active ? colors.accentBlue : colors.textMuted} />
              <Text style={[styles.label, { color: active ? colors.accentBlue : colors.textMuted }]}>
                {t.label}
              </Text>
            </Pressable>
          );
        })}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    backgroundColor: colors.surface,
  },
  bar: {
    flexDirection: 'row',
    backgroundColor: colors.surface,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.sm,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.divider,
  },
  item: {
    flex: 1,
    alignItems: 'center',
    gap: 4,
    paddingVertical: spacing.xs,
  },
  label: {
    ...typography.navLabel,
  },
});
