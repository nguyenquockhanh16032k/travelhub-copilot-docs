import { describe, expect, it } from 'vitest'

import { multiplyMoney } from './money'

describe('multiplyMoney', () => {
  it('multiplies decimal amounts without floating-point rounding', () => {
    expect(multiplyMoney('1234.56', 3)).toBe('3703.68')
    expect(multiplyMoney('0.10', 3)).toBe('0.30')
  })
})
