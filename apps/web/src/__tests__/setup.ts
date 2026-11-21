/**
 * LEDGERSG TEST SETUP
 *
 * Configures testing environment with Jest DOM matchers
 * and global test utilities
 */

import "@testing-library/jest-dom";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

// Cleanup after each test
afterEach(() => {
  cleanup();
});

// Mock matchMedia for responsive design tests
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock IntersectionObserver
class MockIntersectionObserver {
  observe = vi.fn();
  disconnect = vi.fn();
  unobserve = vi.fn();
}

Object.defineProperty(window, "IntersectionObserver", {
  writable: true,
  value: MockIntersectionObserver,
});

// Mock ResizeObserver
class MockResizeObserver {
  observe = vi.fn();
  disconnect = vi.fn();
  unobserve = vi.fn();
}

Object.defineProperty(window, "ResizeObserver", {
  writable: true,
  value: MockResizeObserver,
});

// Radix UI pointer-capture APIs missing in jsdom (Select/Menu/Dropdown
// throw `target.hasPointerCapture is not a function` mid-interaction,
// which can abort option rendering — masks real assertions)
if (!Element.prototype.hasPointerCapture) {
  Object.defineProperties(Element.prototype, {
    hasPointerCapture: { value: vi.fn(() => false) },
    setPointerCapture: { value: vi.fn() },
    releasePointerCapture: { value: vi.fn() },
    scrollIntoView: { value: vi.fn() },
  });
}

// Suppress console errors during tests (optional)
// vi.spyOn(console, "error").mockImplementation(() => {});
// vi.spyOn(console, "warn").mockImplementation(() => {});
