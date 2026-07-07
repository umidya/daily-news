/**
 * Daily local notification scheduling.
 *
 * No remote push, no APNs, no developer-account dependency for this layer —
 * the OS fires it on the configured time. The notification doesn't deliver
 * the audio itself; it nudges Midya to open the app, which then fetches and
 * plays today's briefing.
 *
 * Permission is requested lazily the first time we try to schedule.
 */

import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';

const NOTIFICATION_ID = 'daily-briefing-morning';

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
    shouldShowBanner: true,
    shouldShowList: true,
  }),
});

export async function ensurePermission(): Promise<boolean> {
  const settings = await Notifications.getPermissionsAsync();
  if (settings.granted || settings.ios?.status === Notifications.IosAuthorizationStatus.PROVISIONAL) {
    return true;
  }
  const req = await Notifications.requestPermissionsAsync({
    ios: { allowAlert: true, allowBadge: false, allowSound: true },
  });
  return !!req.granted || req.ios?.status === Notifications.IosAuthorizationStatus.PROVISIONAL;
}

export async function scheduleDailyBriefing(hour24: number, minute: number): Promise<void> {
  const ok = await ensurePermission();
  if (!ok) return;

  // Clear any prior schedule of ours so we don't pile up triggers when settings change.
  await Notifications.cancelScheduledNotificationAsync(NOTIFICATION_ID).catch(() => {});

  const trigger: Notifications.DailyTriggerInput = {
    type: Notifications.SchedulableTriggerInputTypes.DAILY,
    hour: hour24,
    minute,
  };

  await Notifications.scheduleNotificationAsync({
    identifier: NOTIFICATION_ID,
    content: {
      title: "Today's briefing is ready",
      body: 'Tap to listen — your 10-min morning news.',
      sound: Platform.OS === 'ios' ? 'default' : undefined,
    },
    trigger,
  });
}

export async function cancelDailyBriefing(): Promise<void> {
  await Notifications.cancelScheduledNotificationAsync(NOTIFICATION_ID).catch(() => {});
}
