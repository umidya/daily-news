import { ViewStyle } from 'react-native';

export const shadows: Record<'card' | 'cardSoft' | 'fab' | 'play' | 'tabBar', ViewStyle> = {
  card: {
    shadowColor: '#0B1C40',
    shadowOpacity: 0.06,
    shadowRadius: 18,
    shadowOffset: { width: 0, height: 6 },
    elevation: 3,
  },
  cardSoft: {
    shadowColor: '#0B1C40',
    shadowOpacity: 0.04,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 2 },
    elevation: 1,
  },
  fab: {
    shadowColor: '#8B6CFF',
    shadowOpacity: 0.35,
    shadowRadius: 18,
    shadowOffset: { width: 0, height: 10 },
    elevation: 8,
  },
  play: {
    shadowColor: '#FF6B5F',
    shadowOpacity: 0.35,
    shadowRadius: 18,
    shadowOffset: { width: 0, height: 10 },
    elevation: 6,
  },
  tabBar: {
    shadowColor: '#0B1C40',
    shadowOpacity: 0.05,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: -2 },
    elevation: 8,
  },
};
