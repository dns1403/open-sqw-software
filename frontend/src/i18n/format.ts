/** Presentation-only formatting. Never use formatted output in API payloads. */
export function formatNumber(value: number, language: string, digits = 4): string {
  return new Intl.NumberFormat(language, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
    useGrouping: false,
  }).format(value);
}
