import React from 'react';
import { View } from 'react-native';
import Svg, { Circle, Defs, Ellipse, LinearGradient, Path, Rect, Stop } from 'react-native-svg';

interface Props {
  width?: number;
  height?: number;
  rounded?: number;
}

export function BriefingArtwork({ width = 360, height = 220, rounded = 20 }: Props) {
  return (
    <View style={{ width, height, borderRadius: rounded, overflow: 'hidden' }}>
      <Svg width={width} height={height} viewBox="0 0 360 220" preserveAspectRatio="xMidYMid slice">
        <Defs>
          <LinearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
            <Stop offset="0" stopColor="#BFD9FF" />
            <Stop offset="0.45" stopColor="#FFD3C0" />
            <Stop offset="1" stopColor="#FFC1CB" />
          </LinearGradient>
          <LinearGradient id="sun" x1="0" y1="0" x2="0" y2="1">
            <Stop offset="0" stopColor="#FFE08A" />
            <Stop offset="1" stopColor="#FFB95A" />
          </LinearGradient>
          <LinearGradient id="mountainBack" x1="0" y1="0" x2="0" y2="1">
            <Stop offset="0" stopColor="#F4A8B3" />
            <Stop offset="1" stopColor="#D87B95" />
          </LinearGradient>
          <LinearGradient id="mountainMid" x1="0" y1="0" x2="0" y2="1">
            <Stop offset="0" stopColor="#7C8FD6" />
            <Stop offset="1" stopColor="#4A5FA8" />
          </LinearGradient>
          <LinearGradient id="mountainFront" x1="0" y1="0" x2="0" y2="1">
            <Stop offset="0" stopColor="#2B3E78" />
            <Stop offset="1" stopColor="#1B2A57" />
          </LinearGradient>
          <LinearGradient id="water" x1="0" y1="0" x2="0" y2="1">
            <Stop offset="0" stopColor="#FFC2C5" />
            <Stop offset="0.5" stopColor="#C7B5E8" />
            <Stop offset="1" stopColor="#7E92D6" />
          </LinearGradient>
          <LinearGradient id="city" x1="0" y1="0" x2="0" y2="1">
            <Stop offset="0" stopColor="#5C6FB1" />
            <Stop offset="1" stopColor="#2C3D77" />
          </LinearGradient>
        </Defs>

        {/* sky */}
        <Rect x="0" y="0" width="360" height="220" fill="url(#sky)" />

        {/* clouds */}
        <Ellipse cx="60" cy="40" rx="22" ry="6" fill="#FFFFFF" opacity={0.85} />
        <Ellipse cx="80" cy="38" rx="14" ry="5" fill="#FFFFFF" opacity={0.85} />
        <Ellipse cx="280" cy="32" rx="18" ry="5" fill="#FFFFFF" opacity={0.85} />
        <Ellipse cx="298" cy="34" rx="12" ry="4" fill="#FFFFFF" opacity={0.85} />

        {/* sun */}
        <Circle cx="155" cy="100" r="38" fill="url(#sun)" />
        <Circle cx="155" cy="100" r="48" fill="#FFE08A" opacity={0.25} />

        {/* back mountains */}
        <Path d="M0 145 L40 105 L75 130 L120 95 L170 135 L220 100 L260 130 L310 105 L360 140 L360 220 L0 220 Z" fill="url(#mountainBack)" />

        {/* mid mountains */}
        <Path d="M0 165 L50 130 L95 155 L150 120 L200 155 L240 130 L290 165 L360 145 L360 220 L0 220 Z" fill="url(#mountainMid)" opacity={0.85} />

        {/* city silhouette right */}
        <Path d="M230 150 L240 150 L240 130 L250 130 L250 150 L260 150 L260 115 L272 115 L272 150 L284 150 L284 100 L294 100 L294 150 L306 150 L306 125 L316 125 L316 150 L328 150 L328 110 L340 110 L340 150 L355 150 L355 220 L230 220 Z" fill="url(#city)" />
        <Rect x="288" y="108" width="2" height="6" fill="#FFE08A" opacity={0.9} />
        <Rect x="295" y="135" width="2" height="6" fill="#FFE08A" opacity={0.9} />
        <Rect x="320" y="118" width="2" height="6" fill="#FFE08A" opacity={0.9} />

        {/* front mountains */}
        <Path d="M0 185 L40 160 L80 180 L130 150 L185 185 L235 165 L290 195 L360 175 L360 220 L0 220 Z" fill="url(#mountainFront)" />

        {/* water */}
        <Path d="M0 195 L360 195 L360 220 L0 220 Z" fill="url(#water)" />

        {/* sun reflection on water */}
        <Ellipse cx="155" cy="200" rx="28" ry="4" fill="#FFE08A" opacity={0.4} />
        <Ellipse cx="155" cy="206" rx="40" ry="3" fill="#FFD08F" opacity={0.3} />

        {/* sailboat */}
        <Path d="M170 192 L170 205 L175 205 Z" fill="#FFFFFF" />
        <Path d="M165 205 L185 205 L182 210 L168 210 Z" fill="#FFFFFF" opacity={0.95} />
      </Svg>
    </View>
  );
}
