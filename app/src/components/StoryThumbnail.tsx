import React from 'react';
import { View } from 'react-native';
import Svg, { Circle, Defs, LinearGradient, Path, Polyline, Rect, Stop } from 'react-native-svg';
import type { ThumbnailKind } from '@/types/news';

interface Props {
  kind: ThumbnailKind;
  size?: number;
  rounded?: number;
}

export function StoryThumbnail({ kind, size = 84, rounded = 14 }: Props) {
  return (
    <View style={{ width: size, height: size, borderRadius: rounded, overflow: 'hidden' }}>
      <Svg width={size} height={size} viewBox="0 0 100 100">
        <Defs>
          <LinearGradient id="t-mountains" x1="0" y1="0" x2="0" y2="1">
            <Stop offset="0" stopColor="#CFE0FF" />
            <Stop offset="1" stopColor="#F4A8B3" />
          </LinearGradient>
          <LinearGradient id="t-leaf" x1="0" y1="0" x2="0" y2="1">
            <Stop offset="0" stopColor="#FFE0A0" />
            <Stop offset="1" stopColor="#F0967B" />
          </LinearGradient>
          <LinearGradient id="t-chip" x1="0" y1="0" x2="0" y2="1">
            <Stop offset="0" stopColor="#3B2C7A" />
            <Stop offset="1" stopColor="#7B5BD8" />
          </LinearGradient>
          <LinearGradient id="t-bars" x1="0" y1="0" x2="0" y2="1">
            <Stop offset="0" stopColor="#E8F0FF" />
            <Stop offset="1" stopColor="#F8DCE5" />
          </LinearGradient>
          <LinearGradient id="t-house" x1="0" y1="0" x2="0" y2="1">
            <Stop offset="0" stopColor="#FFE08A" />
            <Stop offset="1" stopColor="#FFB95A" />
          </LinearGradient>
          <LinearGradient id="t-mega" x1="0" y1="0" x2="0" y2="1">
            <Stop offset="0" stopColor="#FFD0CC" />
            <Stop offset="1" stopColor="#FF9080" />
          </LinearGradient>
          <LinearGradient id="t-globe" x1="0" y1="0" x2="0" y2="1">
            <Stop offset="0" stopColor="#FFE9C9" />
            <Stop offset="1" stopColor="#A6C8FF" />
          </LinearGradient>
          <LinearGradient id="t-univ" x1="0" y1="0" x2="0" y2="1">
            <Stop offset="0" stopColor="#EFEAFF" />
            <Stop offset="1" stopColor="#C9B8FF" />
          </LinearGradient>
          <LinearGradient id="t-city" x1="0" y1="0" x2="0" y2="1">
            <Stop offset="0" stopColor="#9CC0FF" />
            <Stop offset="1" stopColor="#5E78D6" />
          </LinearGradient>
        </Defs>

        {kind === 'mountains' && (
          <>
            <Rect width="100" height="100" fill="url(#t-mountains)" />
            <Circle cx="35" cy="35" r="14" fill="#FFB95A" />
            <Path d="M0 70 L25 50 L45 65 L70 40 L100 70 L100 100 L0 100 Z" fill="#2B3E78" />
            <Path d="M0 80 L20 70 L50 80 L80 65 L100 80 L100 100 L0 100 Z" fill="#1B2A57" />
          </>
        )}

        {kind === 'leaf' && (
          <>
            <Rect width="100" height="100" fill="url(#t-leaf)" />
            <Path d="M30 60 L35 30 L40 62" stroke="#FFFFFF" strokeWidth={3} fill="none" />
            <Circle cx="35" cy="28" r="6" fill="#FFFFFF" />
            <Path d="M55 60 L60 25 L65 62" stroke="#FFFFFF" strokeWidth={3} fill="none" />
            <Circle cx="60" cy="23" r="6" fill="#FFFFFF" />
            <Path d="M75 62 L80 38 L85 64" stroke="#FFFFFF" strokeWidth={3} fill="none" />
            <Circle cx="80" cy="36" r="5" fill="#FFFFFF" />
            <Path d="M0 70 Q50 55 100 70 L100 100 L0 100 Z" fill="#D87B95" opacity={0.7} />
          </>
        )}

        {kind === 'chip' && (
          <>
            <Rect width="100" height="100" fill="url(#t-chip)" />
            <Rect x="28" y="28" width="44" height="44" rx="6" fill="#1B1448" />
            <Rect x="36" y="36" width="28" height="28" rx="2" fill="#7B5BD8" opacity={0.9} />
            <Polyline points="20,40 28,40" stroke="#7B5BD8" strokeWidth={2} />
            <Polyline points="20,55 28,55" stroke="#7B5BD8" strokeWidth={2} />
            <Polyline points="20,70 28,70" stroke="#7B5BD8" strokeWidth={2} />
            <Polyline points="72,40 80,40" stroke="#7B5BD8" strokeWidth={2} />
            <Polyline points="72,55 80,55" stroke="#7B5BD8" strokeWidth={2} />
            <Polyline points="72,70 80,70" stroke="#7B5BD8" strokeWidth={2} />
            <Polyline points="40,20 40,28" stroke="#7B5BD8" strokeWidth={2} />
            <Polyline points="60,20 60,28" stroke="#7B5BD8" strokeWidth={2} />
          </>
        )}

        {kind === 'bars' && (
          <>
            <Rect width="100" height="100" fill="url(#t-bars)" />
            <Rect x="20" y="60" width="10" height="25" rx="2" fill="#FF9080" />
            <Rect x="35" y="50" width="10" height="35" rx="2" fill="#FFB95A" />
            <Rect x="50" y="40" width="10" height="45" rx="2" fill="#5E78D6" />
            <Rect x="65" y="28" width="10" height="57" rx="2" fill="#7B5BD8" />
            <Polyline points="20,55 35,45 50,35 65,22 80,15" stroke="#247CFF" strokeWidth={2.5} fill="none" />
            <Polyline points="76,18 82,12 78,12 78,18" stroke="#247CFF" strokeWidth={2.5} fill="none" />
          </>
        )}

        {kind === 'house' && (
          <>
            <Rect width="100" height="100" fill="url(#t-house)" />
            <Path d="M50 25 L78 50 L72 50 L72 78 L28 78 L28 50 L22 50 Z" fill="#FFFFFF" opacity={0.95} />
            <Rect x="44" y="58" width="12" height="20" fill="#FFB95A" />
            <Rect x="34" y="55" width="8" height="8" fill="#FFE08A" />
            <Rect x="58" y="55" width="8" height="8" fill="#FFE08A" />
          </>
        )}

        {kind === 'megaphone' && (
          <>
            <Rect width="100" height="100" fill="url(#t-mega)" />
            <Path d="M25 60 L25 40 L60 25 L60 75 Z" fill="#FFFFFF" />
            <Path d="M60 30 L75 40 L75 60 L60 70 Z" fill="#FFFFFF" />
            <Path d="M80 38 L88 32" stroke="#FFFFFF" strokeWidth={3} />
            <Path d="M80 50 L90 50" stroke="#FFFFFF" strokeWidth={3} />
            <Path d="M80 62 L88 68" stroke="#FFFFFF" strokeWidth={3} />
          </>
        )}

        {kind === 'globe' && (
          <>
            <Rect width="100" height="100" fill="url(#t-globe)" />
            <Circle cx="50" cy="50" r="28" fill="#FFFFFF" opacity={0.9} />
            <Path d="M22 50 Q50 30 78 50 Q50 70 22 50" stroke="#247CFF" strokeWidth={1.5} fill="none" />
            <Path d="M50 22 Q40 50 50 78" stroke="#247CFF" strokeWidth={1.5} fill="none" />
            <Path d="M50 22 Q60 50 50 78" stroke="#247CFF" strokeWidth={1.5} fill="none" />
            <Circle cx="50" cy="50" r="28" stroke="#247CFF" strokeWidth={1.5} fill="none" />
          </>
        )}

        {kind === 'university' && (
          <>
            <Rect width="100" height="100" fill="url(#t-univ)" />
            <Path d="M50 25 L82 38 L18 38 Z" fill="#7B5BD8" />
            <Rect x="22" y="42" width="56" height="36" fill="#FFFFFF" />
            <Rect x="30" y="50" width="6" height="20" fill="#7B5BD8" />
            <Rect x="42" y="50" width="6" height="20" fill="#7B5BD8" />
            <Rect x="54" y="50" width="6" height="20" fill="#7B5BD8" />
            <Rect x="66" y="50" width="6" height="20" fill="#7B5BD8" />
            <Rect x="18" y="78" width="64" height="6" fill="#3B2C7A" />
          </>
        )}

        {kind === 'city' && (
          <>
            <Rect width="100" height="100" fill="url(#t-city)" />
            <Rect x="20" y="50" width="14" height="40" fill="#1B2A57" />
            <Rect x="36" y="35" width="16" height="55" fill="#2B3E78" />
            <Rect x="54" y="42" width="14" height="48" fill="#1B2A57" />
            <Rect x="70" y="55" width="12" height="35" fill="#2B3E78" />
          </>
        )}
      </Svg>
    </View>
  );
}
