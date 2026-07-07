import type { Briefing, Story, Voice } from '@/types/news';

export const todayDate = 'Tuesday, April 28, 2026';

const senateStory: Story = {
  id: 'story-1',
  category: 'Canada & BC',
  headline: 'BC Premier signals new short-term rental rules for the Interior',
  summary:
    "Province hints at extending Vancouver-style restrictions to Kamloops and Sun Peaks, with operators given a six-month runway.",
  source: 'CBC News',
  readingTime: '2 min read',
  audioSegmentLength: '02:10',
  thumbnailKind: 'mountains',
};

const climateStory: Story = {
  id: 'story-2',
  category: 'Global',
  headline: 'G7 leaders commit to a new climate financing target',
  summary:
    'A pledge aimed at clean energy and resilience in developing economies — early reactions split between welcome and skepticism.',
  source: 'Reuters',
  readingTime: '2 min read',
  audioSegmentLength: '01:45',
  thumbnailKind: 'leaf',
};

const aiStory: Story = {
  id: 'story-3',
  category: 'AI & Tech',
  headline: 'AI startup raises $150M to build smarter, safer agent tools',
  summary:
    'New round will accelerate enterprise rollouts and a research push into evaluation and oversight.',
  source: 'TechCrunch',
  readingTime: '3 min read',
  audioSegmentLength: '02:05',
  thumbnailKind: 'chip',
};

const businessStory: Story = {
  id: 'story-4',
  category: 'Business',
  headline: 'Markets rise on stronger earnings and easing inflation data',
  summary:
    'Investors responded positively to signs of a soft landing — though megacap tech still drives most of the gains.',
  source: 'Bloomberg',
  readingTime: '2 min read',
  audioSegmentLength: '02:00',
  thumbnailKind: 'bars',
};

const realEstateStory: Story = {
  id: 'story-5',
  category: 'Real Estate',
  headline: 'Sun Peaks listings tighten as remote workers anchor demand',
  summary:
    'Inventory in alpine communities continues to lag long-term averages, even as urban markets soften.',
  source: 'Storeys',
  readingTime: '2 min read',
  audioSegmentLength: '01:30',
  thumbnailKind: 'house',
};

const marketingStory: Story = {
  id: 'story-6',
  category: 'Marketing',
  headline: 'Brands pivot from polish to point-of-view as AI floods feeds',
  summary:
    'CMOs are leaning into founder-led, opinion-rich content as a counterweight to generative sameness.',
  source: 'Marketing Brew',
  readingTime: '3 min read',
  audioSegmentLength: '01:50',
  thumbnailKind: 'megaphone',
};

const higherEdStory: Story = {
  id: 'story-7',
  category: 'Higher Ed',
  headline: 'Canadian universities draft shared AI-in-classroom guidelines',
  summary:
    'A working group is converging on disclosure standards and shared rubrics — adoption is voluntary but widely watched.',
  source: 'University Affairs',
  readingTime: '2 min read',
  audioSegmentLength: '01:20',
  thumbnailKind: 'university',
};

const airbnbStory: Story = {
  id: 'story-8',
  category: 'AirBnb Policy',
  headline: 'Langley adds principal-residence rule to short-term rentals',
  summary:
    'Council vote brings the township closer to the provincial framework — exemptions remain narrower than expected.',
  source: 'Langley Advance Times',
  readingTime: '2 min read',
  audioSegmentLength: '01:10',
  thumbnailKind: 'house',
};

export const mockBriefing: Briefing = {
  date: todayDate,
  greeting: 'Good morning, Midya',
  totalDuration: '10:00',
  currentTime: '7:24',
  remaining: 'About 2 min 36 sec left',
  hookCopy: 'Your personalized audio news briefing for Tuesday',
  digestIntro:
    "Here's what you need to know today. The big stories in BC, AI, marketing, and the world — curated to save you time and keep you informed.",
  digestReadingTime: '4 min read',
  whyItMatters:
    'These stories shape the day ahead — from policy moves close to home to global decisions that ripple into business and tech.',
  topStories: [senateStory, climateStory, aiStory],
  digestStories: [senateStory, climateStory, aiStory, businessStory],
  audioChapters: [
    { id: 'c1', title: 'Canada & BC', duration: '02:10' },
    { id: 'c2', title: 'AI & Tech', duration: '02:05' },
    { id: 'c3', title: 'Marketing', duration: '01:50' },
    { id: 'c4', title: 'Business', duration: '02:00' },
    { id: 'c5', title: 'Global', duration: '01:45' },
  ],
  upNext: senateStory,
};

export const allStories: Story[] = [
  senateStory,
  climateStory,
  aiStory,
  businessStory,
  realEstateStory,
  marketingStory,
  higherEdStory,
  airbnbStory,
];

export const voices: Voice[] = [
  { id: 'onyx', name: 'Onyx', description: 'Warm & confident' },
  { id: 'nova', name: 'Nova', description: 'Bright & friendly' },
  { id: 'alloy', name: 'Alloy', description: 'Neutral & clean' },
];

export const defaultTopics: string[] = [
  'Canada',
  'Kamloops',
  'Sun Peaks',
  'AI',
  'Business',
  'Real Estate',
  'Marketing',
  'Higher Ed',
  'AirBnb in BC',
  'Global',
];

export const defaultMutedTopics: string[] = ['Celebrity', 'Gossip'];
