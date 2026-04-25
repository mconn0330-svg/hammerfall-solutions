// T0.A3 — vitest config for helm-ui.
// Spec: docs/stage1/Helm_T1_Launch_Spec_V2.md §T0.A3
//
// Tests run in jsdom so React components can mount without a real browser.
// Test files: *.test.jsx co-located with components, plus src/__tests__/.

import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.{js,jsx}', 'src/__tests__/**/*.{js,jsx}'],
  },
})
