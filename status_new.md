## Goal Primary Goal: Create a comprehensive onboarding guide (API_workflow_examples_and_tips_guide.md) for an accounting AI agent to help a small Singapore business (not GST registered) use LedgerSG effectively.
Specific Requirements:
- Design a typical/sample workflow for non-GST registered SMB
- Include step-by-step examples with curl and Playwright code snippets
- Cover uploading accounting data to PostgreSQL
- Cover generating P&L and IRAS-required outputs as PDFs
- Include CORS and backend requirement tips
- Supplement (not replace) existing API_CLI_Usage_Guide.md
- Target user shouldn't need to study actual codebase
Secondary Goal: Validate the implementation plan against actual codebase before execution.
---
Instructions Meticulous Approach Required: User emphasized maintaining rigorous and meticulous approach to all planning and execution.
Key Requirements:
1. Research Singapore IRAS requirements for non-GST registered businesses
2. Design realistic workflow for small Singapore business (e.g., sole proprietorship)
3. Create implementation plan before executing
4. Validate plan against actual codebase
5. Use web searches to clarify Singapore-specific requirements
6. Include both CLI (curl) and browser automation (Playwright) examples
Content Requirements:
- Quick-start format (practical over comprehensive)
- Realistic example: Small retail shop or service business
- Non-GST registered (so no GST F5 filing needed)
- Focus on: Chart of Accounts setup, Journal Entries, Bank Reconciliation, P&L generation
- IRAS compliance: Income Tax filing requirements (not GST)
---
Discoveries ### 1. Existing Documentation Architecture Current State:
- API_CLI_Usage_Guide.md - Comprehensive reference (1,060 lines, validated)
- AUTHENTICATION_MILESTONE_SUMMARY.md - Authentication docs (500+ lines)
- API_CLI_USAGE_GUIDE_VALIDATION_REPORT.md - Validation evidence
- All endpoints verified against codebase (95% accuracy)
2. API Endpoint Capabilities Verified Available:
- Authentication: Login/refresh working perfectly
- Chart of Accounts: Full CRUD (8 endpoints)
- Journal Entries: Double-entry validation (9 endpoints)
- Banking: Reconciliation workflow (13 endpoints)
- Reports: Dashboard metrics, financial reports (3 endpoints)
- Invoicing: OS (Out-of-Scope) for non-GST (16 endpoints)
Not Needed for Non-GST:
- GST returns/filing endpoints (can be skipped)
- Peppol/InvoiceNow (optional for non-GST)
3. Singapore Business Context IRAS Requirements for Non-GST Registered:
- Annual Income Tax Return (Form C-S or C)
- Record keeping: 5 years minimum
- Financial statements: P&L, Balance Sheet
- No GST registration needed if turnover < S$1M
- Digital submissions accepted
Typical Small Business Profile:
- Sole proprietorship or small Pte Ltd
- Annual turnover: S$200K-800K
- Transactions: 50-200/month
- Bank accounts: 1-2 (business checking, maybe savings)
- Chart of Accounts: Simple (Revenue, Expenses, Assets)
4. Validation Findings From Previous Work:
- API guide is 95% accurate after fixes
- Decimal precision: Must use 4 decimals (e.g., "100.0000")
- UUID format required for all IDs
- CORSJWTAuthentication handles OPTIONS requests properly
- Rate limiting: 10/min login, 100/min authenticated
---
Accomplished ### ✅ Completed Work:
1. Documentation Updates (Previous Phase)
- Updated README.md with authentication milestone (lines 66-78)
- Updated AGENTS.md version to 1.7.0 with defense-in-depth section
- Created AUTHENTICATION_MILESTONE_SUMMARY.md (500+ lines)
- Fixed API_CLI_Usage_Guide.md minor issues (endpoint counts, duplicates)
2. API_CLI_Usage_Guide Validation
- Analyzed 9 URL configuration files (94 total patterns)
- Live tested login endpoint (confirmed working)
- Verified rate limiting implementation
- Created API_CLI_USAGE_GUIDE_VALIDATION_REPORT.md (comprehensive)
- Created API_CLI_VALIDATION_SUMMARY.md (executive summary)
- Fixed: Authentication count (9→10), total endpoints (87→~90), duplicate dashboard entry
3. Research Phase (Current)
- Read API_CLI_Usage_Guide.md (1,060 lines reviewed)
- Identified relevant endpoints for accounting workflow
- Understood target audience (accounting AI agent)
🔄 In Progress:
Implementation Plan Creation for API_workflow_examples_and_tips_guide.md
- Planning document structure
- Designing workflow steps
- Preparing to validate against codebase
⏳ Pending:
1. Validate Implementation Plan
- Verify each endpoint exists and works as expected
- Test sample payloads for non-GST scenario
- Confirm PDF generation endpoints
2. Create the Guide
- Write introduction and prerequisites
- Create step-by-step workflow sections
- Add curl examples for each step
- Add Playwright examples for browser automation
- Include CORS troubleshooting section
- Add IRAS-specific compliance notes
3. Web Search (if needed)
- Singapore IRAS requirements for non-GST businesses
- Common accounting workflows for small Singapore businesses
- Best practices for P&L generation for tax filing
---
Relevant files / directories Core Documentation (Source Material):
- /home/project/Ledger-SG/API_CLI_Usage_Guide.md - Primary reference (1,060 lines, validated)
- /home/project/Ledger-SG/API_CLI_USAGE_GUIDE_VALIDATION_REPORT.md - Validation evidence (500+ lines)
- /home/project/Ledger-SG/API_CLI_VALIDATION_SUMMARY.md - Executive summary
Backend URL Configs (To Validate Against):
- /home/project/Ledger-SG/apps/backend/apps/core/urls.py - Auth & org endpoints
- /home/project/Ledger-SG/apps/backend/apps/coa/urls.py - Chart of Accounts endpoints
- /home/project/Ledger-SG/apps/backend/apps/journal/urls.py - Journal entry endpoints
- /home/project/Ledger-SG/apps/backend/apps/banking/urls.py - Banking endpoints
- /home/project/Ledger-SG/apps/backend/apps/reporting/urls.py - Reports/dashboard
- /home/project/Ledger-SG/apps/backend/config/urls.py - Root URL config
Existing Documentation (Reference Style):
- /home/project/Ledger-SG/README.md - Updated with auth milestone
- /home/project/Ledger-SG/AGENTS.md - Architecture patterns
- /home/project/Ledger-SG/AUTHENTICATION_MILESTONE_SUMMARY.md - Security patterns
Files To Create:
- /home/project/Ledger-SG/API_WORKFLOW_IMPLEMENTATION_PLAN.md - Implementation plan (next step)
- /home/project/Ledger-SG/API_workflow_examples_and_tips_guide.md - Final deliverable
---
Next Steps Immediate (Next Action):
1. Create Implementation Plan
   - Design 5-7 step workflow for small non-GST business
   - Map each step to specific API endpoints
   - Identify required vs optional endpoints
   - Plan curl and Playwright examples
2. Validate Plan Against Codebase
   - Verify each endpoint exists
   - Test sample payloads
   - Confirm response structures
   - Check permissions
3. Research Singapore Requirements
   - Web search: IRAS non-GST business requirements
   - Web search: Small business accounting workflows Singapore
   - Document findings
4. Execute Implementation
   - Write the guide following plan
   - Include practical examples
   - Add troubleshooting section
   - Review and finalize
Template for New Document Structure:
1. Introduction & Prerequisites
2. Scenario: Small Retail Shop (Non-GST)
3. Step-by-Step Workflow:
   - Step 1: Authentication
   - Step 2: Organization Setup
   - Step 3: Chart of Accounts Setup
   - Step 4: Import Opening Balances
   - Step 5: Daily Transactions (Journal Entries)
   - Step 6: Bank Reconciliation
   - Step 7: Generate P&L and Reports
4. curl Examples (for each step)
5. Playwright Examples (for each step)
6. CORS & Backend Tips
7. IRAS Compliance Checklist
8. Troubleshooting
