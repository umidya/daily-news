import { registerRootComponent } from 'expo';
import TrackPlayer from 'react-native-track-player';
import App from './App';
import { playbackService } from './src/services/playbackService';

// Must be registered at the JS module top level (before any TrackPlayer
// methods are called) so iOS Control Center / lock-screen remote commands
// route into our service even when the app is backgrounded.
TrackPlayer.registerPlaybackService(() => playbackService);

registerRootComponent(App);
