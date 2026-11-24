import { describe, expect, it } from 'vitest'
import { publishedDate, safeCoverUrl } from './articlePresentation'
describe('article presentation', () => {
  it('allows HTTP URLs only', () => {
    expect(safeCoverUrl('https://example.com/photo.jpg')).toBe('https://example.com/photo.jpg')
    expect(safeCoverUrl('javascript:alert(1)')).toBeUndefined()
    expect(safeCoverUrl('data:text/html,abc')).toBeUndefined()
  })
  it('ignores invalid dates', () => {
    expect(publishedDate('invalid')).toBe('')
    expect(publishedDate(null)).toBe('')
  })
})
