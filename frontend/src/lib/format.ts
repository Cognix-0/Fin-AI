const currency = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' });
const compactCurrency = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  notation: 'compact',
  maximumFractionDigits: 1,
});
const shortDate = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric' });

export const formatMoney = (n: number) => currency.format(n);
export const formatMoneyCompact = (n: number) => compactCurrency.format(n);
// Parse YYYY-MM-DD as a local date so it doesn't shift a day in negative UTC offsets
export const formatShortDate = (iso: string) => shortDate.format(new Date(`${iso}T00:00:00`));
