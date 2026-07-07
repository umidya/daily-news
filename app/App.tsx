import React from 'react';
import { StatusBar } from 'expo-status-bar';
import { StyleSheet, View } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { AppProvider, useApp } from '@/state/AppContext';
import { BottomTabBar } from '@/components/BottomTabBar';
import { HomeScreen } from '@/screens/HomeScreen';
import { AudioScreen } from '@/screens/AudioScreen';
import { DigestScreen } from '@/screens/DigestScreen';
import { SavedScreen } from '@/screens/SavedScreen';
import { SettingsScreen } from '@/screens/SettingsScreen';
import { colors } from '@/theme';

function CurrentScreen() {
  const { activeTab } = useApp();
  switch (activeTab) {
    case 'home':
      return <HomeScreen />;
    case 'audio':
      return <AudioScreen />;
    case 'digest':
      return <DigestScreen />;
    case 'saved':
      return <SavedScreen />;
    case 'settings':
      return <SettingsScreen />;
  }
}

export default function App() {
  return (
    <SafeAreaProvider>
      <AppProvider>
        <View style={styles.root}>
          <StatusBar style="dark" />
          <View style={styles.screen}>
            <CurrentScreen />
          </View>
          <BottomTabBar />
        </View>
      </AppProvider>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: colors.background,
  },
  screen: {
    flex: 1,
  },
});
