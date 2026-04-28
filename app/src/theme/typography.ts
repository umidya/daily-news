import { Platform, TextStyle } from 'react-native';

const serif = Platform.select({
  ios: 'Georgia',
  android: 'serif',
  default: 'serif',
});

const sans = Platform.select({
  ios: 'System',
  android: 'sans-serif',
  default: 'System',
});

export const fonts = { serif, sans };

export const typography = {
  heroTitle:     { fontFamily: serif, fontSize: 38, fontWeight: '700', lineHeight: 44, letterSpacing: -0.5 } as TextStyle,
  screenTitle:   { fontFamily: serif, fontSize: 34, fontWeight: '700', lineHeight: 40, letterSpacing: -0.5 } as TextStyle,
  sectionTitle:  { fontFamily: serif, fontSize: 22, fontWeight: '700', lineHeight: 28 } as TextStyle,
  cardTitle:     { fontFamily: serif, fontSize: 26, fontWeight: '700', lineHeight: 32, letterSpacing: -0.3 } as TextStyle,

  storyHeadline: { fontFamily: sans,  fontSize: 17, fontWeight: '700', lineHeight: 22 } as TextStyle,
  body:          { fontFamily: sans,  fontSize: 15, fontWeight: '400', lineHeight: 22 } as TextStyle,
  bodyStrong:    { fontFamily: sans,  fontSize: 15, fontWeight: '600', lineHeight: 22 } as TextStyle,
  bodySmall:     { fontFamily: sans,  fontSize: 13, fontWeight: '400', lineHeight: 18 } as TextStyle,
  caption:       { fontFamily: sans,  fontSize: 12, fontWeight: '500', lineHeight: 16 } as TextStyle,

  pillLabel:     { fontFamily: sans,  fontSize: 11, fontWeight: '700', letterSpacing: 0.6 } as TextStyle,
  navLabel:      { fontFamily: sans,  fontSize: 11, fontWeight: '500' } as TextStyle,
  monoTime:      { fontFamily: Platform.select({ ios: 'Menlo', android: 'monospace', default: 'monospace' }), fontSize: 13, fontWeight: '600' } as TextStyle,
};
