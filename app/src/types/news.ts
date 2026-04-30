import type { CategoryName } from '@/theme/colors';

export interface Story {
  id: string;
  category: CategoryName;
  headline: string;
  summary: string;
  source: string;
  url?: string;
  readingTime: string;
  audioSegmentLength: string;
  thumbnailKind: ThumbnailKind;
  imageUrl?: string;
}

export type ThumbnailKind =
  | 'mountains'
  | 'city'
  | 'chip'
  | 'bars'
  | 'leaf'
  | 'house'
  | 'megaphone'
  | 'globe'
  | 'university';

export interface Briefing {
  schemaVersion?: number;
  date: string;
  dateIso?: string;
  greeting: string;
  totalDuration: string;
  currentTime: string;
  remaining: string;
  hookCopy: string;
  digestIntro: string;
  digestReadingTime: string;
  whyItMatters: string;
  audioUrl?: string;
  audioDurationSeconds?: number;
  audioScript?: string;
  heroImageUrl?: string;
  topStories: Story[];
  digestStories: Story[];
  audioChapters: Chapter[];
  upNext: Story | null;
  mainStory?: Story | null;
}

export interface Chapter {
  id: string;
  title: string;
  category?: CategoryName;
  duration: string;
  startSeconds?: number;
}

export interface Voice {
  id: 'onyx' | 'nova' | 'alloy';
  name: string;
  description: string;
}

export type TabKey = 'home' | 'audio' | 'digest' | 'saved' | 'settings';
