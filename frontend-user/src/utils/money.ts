export function multiplyMoney(amount: string, quantity: number): string {
  const [whole, fraction = ''] = amount.split('.')
  const cents = BigInt(whole) * 100n + BigInt(fraction.padEnd(2, '0').slice(0, 2))
  const total = cents * BigInt(quantity)
  return `${total / 100n}.${String(total % 100n).padStart(2, '0')}`
}
