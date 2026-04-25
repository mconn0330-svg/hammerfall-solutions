// Smoke test — proves vitest + jsdom + React Testing Library wire up correctly.
// If this passes, the harness is good. Real coverage starts with T1.x components.

import React from 'react'
import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'

describe('smoke', () => {
  it('renders a basic React element into jsdom', () => {
    const { container } = render(<div>hello</div>)
    expect(container.textContent).toBe('hello')
  })
})
