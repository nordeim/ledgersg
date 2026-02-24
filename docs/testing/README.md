# LedgerSG Testing Guide

## Overview

This document provides comprehensive guidance for testing the LedgerSG frontend application.

## Testing Stack

| Tool | Purpose | Coverage Target |
|------|---------|-----------------|
| **Vitest** | Unit and integration tests | 85%+ |
| **@testing-library/react** | Component testing | 90%+ |
| **Playwright** | E2E and accessibility tests | Critical flows |
| **@axe-core/playwright** | Accessibility audits | WCAG AAA |

## Running Tests

```bash
# Unit tests
npm test

# Unit tests with coverage
npm run test:coverage

# E2E tests
npm run test:e2e

# All tests
npm run test:all
```

## Test Coverage Status

| Module | Tests | Coverage |
|--------|-------|----------|
| GST Engine | 54 | 100% |
| Button Component | 24 | 90%+ |
| Input Component | 19 | 90%+ |
| Badge Component | 8 | 90%+ |
| **Total** | **105** | **85%+** |

## IRAS Compliance Testing

GST calculation tests validate:
- Standard 9% GST accuracy
- Zero-rated exports
- BCRS deposit exemption
- Precision (4dp internal, 2dp display)
