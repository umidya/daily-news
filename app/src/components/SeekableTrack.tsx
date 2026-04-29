import React, { useRef, useState } from 'react';
import { LayoutChangeEvent, PanResponder, StyleSheet, View, ViewStyle } from 'react-native';

interface Props {
  progress: number; // 0..1; controlled value while not dragging
  onSeek: (ratio: number) => void; // commit on release
  trackStyle?: ViewStyle;
  fillStyle?: ViewStyle;
  knobStyle?: ViewStyle;
  containerStyle?: ViewStyle;
  knobSize?: number;
}

// A track that supports both single tap and drag-to-scrub. The displayed
// position follows the finger during a drag (`dragRatio`); on release it
// hands back to the controlled `progress` from the audio engine.
export function SeekableTrack({
  progress,
  onSeek,
  trackStyle,
  fillStyle,
  knobStyle,
  containerStyle,
  knobSize = 14,
}: Props) {
  const [width, setWidth] = useState(0);
  const widthRef = useRef(0);
  const [dragging, setDragging] = useState(false);
  const [dragRatio, setDragRatio] = useState(0);

  const onLayout = (e: LayoutChangeEvent) => {
    const w = e.nativeEvent.layout.width;
    setWidth(w);
    widthRef.current = w;
  };

  const ratioFromX = (x: number) => {
    const w = widthRef.current;
    if (!w) return 0;
    return Math.max(0, Math.min(1, x / w));
  };

  const responder = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onMoveShouldSetPanResponder: () => true,
      onPanResponderGrant: (e) => {
        setDragging(true);
        setDragRatio(ratioFromX(e.nativeEvent.locationX));
      },
      onPanResponderMove: (e) => {
        setDragRatio(ratioFromX(e.nativeEvent.locationX));
      },
      onPanResponderRelease: (e) => {
        const ratio = ratioFromX(e.nativeEvent.locationX);
        setDragging(false);
        onSeek(ratio);
      },
      onPanResponderTerminate: () => {
        setDragging(false);
      },
    }),
  ).current;

  const visibleRatio = dragging ? dragRatio : Math.max(0, Math.min(1, progress));
  const pct: `${number}%` = `${visibleRatio * 100}%`;

  return (
    <View
      onLayout={onLayout}
      style={[styles.container, containerStyle]}
      {...responder.panHandlers}
    >
      <View style={[styles.track, trackStyle]}>
        <View style={[styles.fill, fillStyle, { width: pct }]} />
      </View>
      <View
        style={[
          styles.knob,
          knobStyle,
          {
            width: knobSize,
            height: knobSize,
            borderRadius: knobSize / 2,
            marginLeft: -knobSize / 2,
            left: pct,
            transform: dragging ? [{ scale: 1.15 }] : undefined,
          },
        ]}
        pointerEvents="none"
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingVertical: 12,
    justifyContent: 'center',
  },
  track: {
    height: 4,
    borderRadius: 2,
    backgroundColor: '#FFFFFFCC',
    overflow: 'visible',
    position: 'relative',
  },
  fill: {
    height: 4,
    borderRadius: 2,
    backgroundColor: '#FF6B5F',
  },
  knob: {
    position: 'absolute',
    top: '50%',
    marginTop: -7,
    backgroundColor: '#FF6B5F',
    borderWidth: 2,
    borderColor: '#FFFFFF',
  },
});
