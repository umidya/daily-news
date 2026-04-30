/**
 * Headless playback service. RN Track Player calls this when the user taps
 * play / pause / skip from the iOS lock screen, Control Center, or Android
 * notification — even when the JS context is otherwise asleep. Keep the
 * handlers small and side-effect-only; do not import anything heavy.
 */
import TrackPlayer, { Event } from 'react-native-track-player';

export async function playbackService(): Promise<void> {
  TrackPlayer.addEventListener(Event.RemotePlay, () => {
    TrackPlayer.play();
  });

  TrackPlayer.addEventListener(Event.RemotePause, () => {
    TrackPlayer.pause();
  });

  TrackPlayer.addEventListener(Event.RemoteStop, () => {
    TrackPlayer.stop();
  });

  TrackPlayer.addEventListener(Event.RemoteJumpForward, async (event) => {
    const position = (await TrackPlayer.getProgress()).position;
    const interval = event?.interval ?? 30;
    await TrackPlayer.seekTo(position + interval);
  });

  TrackPlayer.addEventListener(Event.RemoteJumpBackward, async (event) => {
    const position = (await TrackPlayer.getProgress()).position;
    const interval = event?.interval ?? 15;
    await TrackPlayer.seekTo(Math.max(0, position - interval));
  });

  TrackPlayer.addEventListener(Event.RemoteSeek, ({ position }) => {
    TrackPlayer.seekTo(position);
  });
}
