import '@testing-library/jest-dom/vitest'
import { afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'

// We don't use vitest's `globals: true` mode (this codebase favors explicit
// imports), so Testing Library's automatic afterEach(cleanup) never
// registers on its own — wire it up here instead.
afterEach(() => {
  cleanup()
})
