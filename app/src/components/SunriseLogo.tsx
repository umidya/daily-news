import React from 'react';
import Svg, { Circle, Defs, LinearGradient, Path, Rect, Stop } from 'react-native-svg';

export function SunriseLogo({ size = 36 }: { size?: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 40 40" fill="none">
      <Defs>
        <LinearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
          <Stop offset="0" stopColor="#FFE9C9" />
          <Stop offset="1" stopColor="#FFD08F" />
        </LinearGradient>
        <LinearGradient id="water" x1="0" y1="0" x2="0" y2="1">
          <Stop offset="0" stopColor="#9CC0FF" />
          <Stop offset="1" stopColor="#5E8BE0" />
        </LinearGradient>
      </Defs>
      <Rect x="0" y="0" width="40" height="40" rx="20" fill="url(#bg)" />
      <Circle cx="20" cy="22" r="7.5" fill="#FFB257" />
      <Path d="M0 26 Q10 22 20 26 T40 26 V40 H0 Z" fill="url(#water)" />
      <Path d="M0 30 Q10 28 20 30 T40 30" stroke="#FFFFFF" strokeOpacity={0.55} strokeWidth={1} fill="none" />
      <Path d="M0 34 Q10 32 20 34 T40 34" stroke="#FFFFFF" strokeOpacity={0.4} strokeWidth={1} fill="none" />
    </Svg>
  );
}
