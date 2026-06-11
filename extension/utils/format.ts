// "$39" for whole dollars, "$28.35" otherwise, "—" when unknown.
export function money(n: number | null | undefined): string {
  if (n == null) return '—';
  return '$' + (Number.isInteger(n) ? n : Number(n).toFixed(2));
}
