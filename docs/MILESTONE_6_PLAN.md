# Milestone 6: Final Polish & Documentation

## Executive Summary

**Goal**: Complete production readiness with comprehensive testing, security hardening, performance optimization, and documentation.

**Timeline**: Estimated 2-3 days
**Priority**: Critical for production deployment

---

## Phase 1: Testing Infrastructure

### 1.1 Vitest Unit Testing Setup
**Purpose**: Component and utility unit testing
**Dependencies**: vitest, @testing-library/react, @testing-library/jest-dom, jsdom

**Deliverables**:
- `vitest.config.ts` - Test configuration
- `src/__tests__/setup.ts` - Test setup file
- `src/__tests__/utils.tsx` - Test utilities (render with providers)

**Test Coverage Targets**:
| Module | Coverage Target | Priority |
|--------|-----------------|----------|
| `lib/gst-engine.ts` | 100% | Critical |
| `lib/utils.ts` | 100% | High |
| `components/ui/button.tsx` | 90% | High |
| `components/ui/input.tsx` | 90% | High |
| `hooks/use-toast.ts` | 85% | Medium |
| `hooks/use-invoices.ts` | 80% | Medium |

### 1.2 GST Engine Test Suite
**Purpose**: Validate IRAS-compliant GST calculations
**Test Cases**:
1. Standard-rated (SR) GST calculation
2. Zero-rated (ZR) export
3. Exempt (ES) supplies
4. BCRS deposit exclusion from GST
5. Discount application before GST
6. Precision handling (4dp internal, 2dp display)
7. Invoice totals aggregation
8. Server validation reconciliation

**Critical Test Scenarios**:
```typescript
// Scenario 1: Standard 9% GST
qty: 10, price: 100, discount: 0, tax_code: "SR"
Expected: subtotal=1000.00, gst=90.00, total=1090.00

// Scenario 2: BCRS deposit (no GST)
qty: 5, price: 0.10, discount: 0, tax_code: "SR", is_bcrs_deposit: true
Expected: subtotal=0.50, gst=0.00, total=0.50

// Scenario 3: With discount
qty: 1, price: 1000, discount: 10, tax_code: "SR"
Expected: subtotal=900.00, gst=81.00, total=981.00
```

### 1.3 Component Unit Tests
**Components to Test**:
- `Button` - variants, sizes, click handlers, disabled state
- `Input` - value binding, error states, ARIA attributes
- `MoneyInput` - currency formatting, validation
- `Badge` - variant rendering
- `Card` - structure, accessibility
- `Skeleton` - rendering, animation states
- `Toast` - appearance, dismissal, variants

### 1.4 Playwright E2E Test Suite
**Purpose**: End-to-end critical user flow validation
**Current Status**: Basic navigation tests exist

**New Test Files**:
1. `e2e/auth.spec.ts` - Authentication flows
2. `e2e/invoice-create.spec.ts` - Invoice creation workflow
3. `e2e/invoice-workflow.spec.ts` - Approve, void, send workflows
4. `e2e/dashboard.spec.ts` - Dashboard navigation and metrics
5. `e2e/accessibility.spec.ts` - WCAG AAA compliance scans

**Critical Flows to Test**:
1. Login → Dashboard navigation
2. Create invoice → Add line items → Save
3. Create invoice → Approve → Verify journal created
4. Create invoice → Void → Verify reversal
5. GST calculation accuracy in UI
6. Mobile responsive design
7. Accessibility (axe-core scans)

---

## Phase 2: Security Hardening

### 2.1 Content Security Policy (CSP)
**Purpose**: Prevent XSS and content injection attacks
**Implementation**: Next.js headers configuration

**CSP Directives**:
```
default-src 'self'
script-src 'self' 'nonce-{nonce}' https://vercel.live
style-src 'self' 'nonce-{nonce}' https://fonts.googleapis.com
img-src 'self' data: blob:
font-src 'self' https://fonts.gstatic.com
connect-src 'self' https://api.peppol.sg https://api.iras.gov.sg
frame-ancestors 'none'
base-uri 'self'
form-action 'self'
```

### 2.2 Security Headers
**Headers to Configure**:
| Header | Value | Purpose |
|--------|-------|---------|
| Strict-Transport-Security | max-age=31536000; includeSubDomains; preload | HSTS |
| X-Frame-Options | DENY | Clickjacking prevention |
| X-Content-Type-Options | nosniff | MIME sniffing prevention |
| Referrer-Policy | strict-origin-when-cross-origin | Privacy |
| Permissions-Policy | camera=(), microphone=(), geolocation=() | Feature restriction |
| X-XSS-Protection | 0 | Modern browsers (CSP replaces) |

### 2.3 Security Audit Checklist
- [ ] No hardcoded secrets in code
- [ ] API endpoints validate all inputs
- [ ] Authentication tokens handled securely
- [ ] LocalStorage only for non-sensitive data
- [ ] XSS prevention in dynamic content
- [ ] CSRF protection on mutations
- [ ] Secure cookie attributes
- [ ] Dependency vulnerability scan

---

## Phase 3: Performance Optimization

### 3.1 Bundle Analysis
**Purpose**: Identify and reduce bundle size
**Tools**: @next/bundle-analyzer

**Analysis Targets**:
- Initial JS bundle < 300KB
- Vendor chunk optimization
- Dynamic import opportunities
- Tree-shaking verification

**Expected Optimizations**:
- Split Recharts to dashboard-only chunk
- Lazy load invoice form components
- Optimize Decimal.js import

### 3.2 Code Splitting Review
**Current Dynamic Imports**:
- ✅ `invoice-form-wrapper.tsx` - Already implemented

**Additional Opportunities**:
- Dashboard charts (Recharts)
- Ledger table (TanStack Table)
- PDF generation utilities
- Report components

### 3.3 Image Optimization
**Current**: `images.unoptimized: true` (required for static export)
**Actions**:
- Optimize all images in `public/`
- Use WebP format where possible
- Add responsive image sizes
- Implement lazy loading

### 3.4 Lighthouse CI Configuration
**Purpose**: Automated performance monitoring
**Configuration**: `.github/workflows/lighthouse.yml`

**Budgets**:
| Metric | Budget | Priority |
|--------|--------|----------|
| Performance | >90 | Critical |
| Accessibility | 100 | Critical |
| Best Practices | >95 | High |
| SEO | >90 | Medium |
| First Contentful Paint | <1.5s | Critical |
| Time to Interactive | <3s | High |

---

## Phase 4: Documentation

### 4.1 Component Documentation
**Purpose**: Storybook-style component showcase
**Format**: Markdown docs with usage examples

**Files to Create**:
- `docs/components/button.md`
- `docs/components/input.md`
- `docs/components/money-input.md`
- `docs/components/badge.md`
- `docs/components/card.md`
- `docs/components/skeleton.md`
- `docs/components/toast.md`

### 4.2 Testing Documentation
**Files to Create**:
- `docs/testing/README.md` - Testing overview
- `docs/testing/unit-tests.md` - Unit test guidelines
- `docs/testing/e2e-tests.md` - E2E test guidelines
- `docs/testing/gst-test-cases.md` - GST calculation test scenarios

### 4.3 Deployment Runbook
**Files to Create**:
- `docs/deployment/README.md` - Deployment overview
- `docs/deployment/static-export.md` - Static build deployment
- `docs/deployment/security-headers.md` - Security configuration
- `docs/deployment/performance.md` - Performance monitoring

### 4.4 API Integration Guide
**Files to Create**:
- `docs/api/README.md` - API overview
- `docs/api/authentication.md` - JWT + HttpOnly cookie flow
- `docs/api/error-handling.md` - Error codes and handling
- `docs/api/invoice-workflow.md` - Invoice state machine

---

## Implementation Order

```
Phase 1.1 → Phase 1.2 → Phase 1.3 → Phase 1.4
    ↓
Phase 2.1 → Phase 2.2 → Phase 2.3
    ↓
Phase 3.1 → Phase 3.2 → Phase 3.3 → Phase 3.4
    ↓
Phase 4.1 → Phase 4.2 → Phase 4.3 → Phase 4.4
```

**Dependencies**:
- Phase 1 must complete before Phase 4.2 (testing docs need test implementation)
- Phase 2 should complete before final deployment
- Phase 3.1 informs Phase 3.2 and 3.3

---

## Success Criteria

| Criterion | Target | Verification |
|-----------|--------|--------------|
| Unit Test Coverage | >85% | `npm run test:coverage` |
| E2E Test Pass Rate | 100% | `npx playwright test` |
| GST Calculation Tests | 100% | All IRAS scenarios pass |
| Security Headers | All A+ | securityheaders.com scan |
| Lighthouse Performance | >90 | Lighthouse CI |
| Bundle Size | <300KB initial | Bundle analyzer |
| Documentation Complete | 100% | All docs written |

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| GST test complexity | Medium | High | Extensive test scenarios, IRAS examples |
| Playwright flakiness | Medium | Medium | Retry config, stable selectors |
| Bundle size >300KB | Medium | Medium | Code splitting, tree shaking |
| CSP breaks features | Low | High | Test all functionality with CSP |

---

## Deliverables Checklist

### Testing
- [ ] Vitest configuration
- [ ] GST engine test suite (100% coverage)
- [ ] Component unit tests (Button, Input, MoneyInput)
- [ ] E2E: Authentication flows
- [ ] E2E: Invoice creation workflow
- [ ] E2E: Invoice approval/void workflow
- [ ] E2E: Accessibility scans

### Security
- [ ] CSP headers configured
- [ ] HSTS headers configured
- [ ] Security headers complete
- [ ] Security audit checklist passed
- [ ] Dependency audit clean

### Performance
- [ ] Bundle analysis report
- [ ] Code splitting optimized
- [ ] Images optimized
- [ ] Lighthouse CI configured
- [ ] Performance budgets met

### Documentation
- [ ] Component documentation
- [ ] Testing guide
- [ ] Deployment runbook
- [ ] API integration guide
- [ ] Security configuration guide

---

**Plan Created**: 2026-02-24
**Estimated Duration**: 2-3 days
**Status**: Ready for execution
