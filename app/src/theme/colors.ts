export const colors = {
  background: '#F7FAFC',
  backgroundAlt: '#FAFBFF',
  surface: '#FFFFFF',
  surfaceTint: '#F2F4F9',

  textPrimary: '#071A44',
  textSecondary: '#3F4A66',
  textMuted: '#6B7280',
  textInverse: '#FFFFFF',

  accentBlue: '#247CFF',
  accentBlueSoft: '#E8F0FF',
  coral: '#FF6B5F',
  coralSoft: '#FFE3DE',
  lavender: '#8B6CFF',
  lavenderSoft: '#EFEAFF',
  mint: '#47C8A5',
  mintSoft: '#DDF4EB',
  warmYellow: '#FFD166',
  warmYellowSoft: '#FFF1CC',
  amber: '#F59E0B',
  amberSoft: '#FFE4B5',

  border: '#E5E7EB',
  borderSoft: '#EEF1F5',
  divider: '#EEF1F5',

  heroGradient: ['#FFE4D6', '#FCD2DA', '#E5DAF5'] as const,
  heroPlayShadow: '#FF6B5F',
  outerScreen: '#EFF4FB',
} as const;

export type CategoryName =
  | 'Canada & BC'
  | 'AI & Tech'
  | 'Business'
  | 'Real Estate'
  | 'Marketing'
  | 'Higher Ed'
  | 'Global'
  | 'AirBnb Policy';

export const categoryStyles: Record<
  CategoryName,
  { bg: string; text: string; dot: string }
> = {
  'Canada & BC':   { bg: colors.accentBlueSoft, text: colors.accentBlue, dot: colors.accentBlue },
  'AI & Tech':     { bg: colors.lavenderSoft,   text: colors.lavender,   dot: colors.lavender },
  'Business':      { bg: colors.mintSoft,       text: '#1F8E70',         dot: colors.mint },
  'Real Estate':   { bg: colors.warmYellowSoft, text: '#A87000',         dot: colors.warmYellow },
  'Marketing':     { bg: colors.coralSoft,      text: colors.coral,      dot: colors.coral },
  'Higher Ed':     { bg: colors.lavenderSoft,   text: colors.lavender,   dot: colors.lavender },
  'Global':        { bg: '#FFE9D6',             text: '#C2541C',         dot: '#E07B30' },
  'AirBnb Policy': { bg: colors.mintSoft,       text: '#1F8E70',         dot: colors.mint },
};
