import React from 'react';
import Svg, { Circle, Defs, Ellipse, LinearGradient, Path, Rect, Stop } from 'react-native-svg';

export function PersonalizeArtwork({ width = 220, height = 140 }: { width?: number; height?: number }) {
  return (
    <Svg width={width} height={height} viewBox="0 0 220 140" fill="none">
      <Defs>
        <LinearGradient id="psun" x1="0" y1="0" x2="0" y2="1">
          <Stop offset="0" stopColor="#FFE08A" />
          <Stop offset="1" stopColor="#FFB95A" />
        </LinearGradient>
        <LinearGradient id="pHill" x1="0" y1="0" x2="0" y2="1">
          <Stop offset="0" stopColor="#F4A8B3" />
          <Stop offset="1" stopColor="#D87B95" />
        </LinearGradient>
        <LinearGradient id="pBack" x1="0" y1="0" x2="0" y2="1">
          <Stop offset="0" stopColor="#9CC0FF" />
          <Stop offset="1" stopColor="#C7B5E8" />
        </LinearGradient>
        <LinearGradient id="cup" x1="0" y1="0" x2="0" y2="1">
          <Stop offset="0" stopColor="#7C7CD6" />
          <Stop offset="1" stopColor="#4F4FA0" />
        </LinearGradient>
      </Defs>
      <Circle cx="110" cy="70" r="60" fill="url(#pBack)" opacity={0.55} />
      <Circle cx="80" cy="65" r="28" fill="url(#psun)" />
      <Path d="M10 100 Q60 70 110 100 T220 100 L220 140 L10 140 Z" fill="url(#pHill)" opacity={0.85} />

      {/* Coffee cup */}
      <Rect x="135" y="78" width="50" height="38" rx="4" fill="url(#cup)" />
      <Rect x="135" y="78" width="50" height="6" rx="2" fill="#3B3B7A" />
      <Path d="M185 86 Q200 88 198 100 Q196 110 185 108" stroke="#4F4FA0" strokeWidth={3} fill="none" />
      <Rect x="125" y="116" width="70" height="6" rx="2" fill="#8E6C58" />

      {/* Steam */}
      <Path d="M148 70 Q152 64 148 58 Q144 52 150 46" stroke="#FFFFFF" strokeWidth={2} strokeOpacity={0.9} fill="none" />
      <Path d="M162 70 Q166 64 162 58 Q158 52 164 46" stroke="#FFFFFF" strokeWidth={2} strokeOpacity={0.9} fill="none" />
      <Path d="M175 72 Q179 66 175 60" stroke="#FFFFFF" strokeWidth={2} strokeOpacity={0.85} fill="none" />

      {/* small leaves */}
      <Path d="M195 100 Q205 90 215 100 Q205 105 195 100" fill="#F4A8B3" opacity={0.85} />
      <Path d="M205 95 L205 105" stroke="#D87B95" strokeWidth={1} />
    </Svg>
  );
}
