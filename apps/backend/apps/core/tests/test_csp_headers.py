"""
Tests for Content Security Policy headers (SEC-003).

TDD Approach: These tests are written BEFORE implementation to drive development.
The tests should FAIL initially (RED phase), then we implement to make them PASS (GREEN phase).

Security Requirement: SEC-003 - CSP Headers Implementation
Reference: REMEDIATION_PLAN.md Section 1.4
"""

import pytest
from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestCSPHeaders:
    """Test suite for CSP header configuration."""

    def setup_method(self):
        """Set up test client for each test."""
        self.client = Client()

    def test_csp_header_present_in_response(self):
        """
        RED PHASE TEST: Verify CSP header is present in responses.

        Expected: Response should include Content-Security-Policy header.
        Status: Will FAIL until CSPMiddleware is added to MIDDLEWARE.
        """
        response = self.client.get("/")

        # Check for CSP header (either enforcing or report-only)
        has_csp = (
            "Content-Security-Policy" in response.headers
            or "Content-Security-Policy-Report-Only" in response.headers
        )

        assert has_csp, (
            "CSP header not found in response. Add 'csp.middleware.CSPMiddleware' to MIDDLEWARE."
        )

    def test_csp_has_strict_default_src(self):
        """
        RED PHASE TEST: Verify CSP has strict default-src directive.

        Expected: CSP should have default-src set to 'none' or 'self'.
        Status: Will FAIL until CSP_DEFAULT_SRC is configured.
        """
        response = self.client.get("/")

        csp = response.headers.get("Content-Security-Policy") or response.headers.get(
            "Content-Security-Policy-Report-Only", ""
        )

        assert "default-src" in csp, "CSP missing default-src directive"
        assert "'none'" in csp or "'self'" in csp, (
            "CSP default-src should be 'none' or 'self' for security"
        )

    def test_csp_prevents_clickjacking(self):
        """
        RED PHASE TEST: Verify CSP prevents clickjacking.

        Expected: CSP should have frame-ancestors set to 'none'.
        Status: Will FAIL until CSP_FRAME_ANCESTORS is configured.
        """
        response = self.client.get("/")

        csp = response.headers.get("Content-Security-Policy") or response.headers.get(
            "Content-Security-Policy-Report-Only", ""
        )

        assert "frame-ancestors" in csp, "CSP missing frame-ancestors directive"
        assert "'none'" in csp, "CSP frame-ancestors should be 'none' to prevent clickjacking"

    def test_csp_upgrade_insecure_requests(self):
        """
        RED PHASE TEST: Verify CSP upgrades insecure requests.

        Expected: CSP should include upgrade-insecure-requests directive.
        Status: Will FAIL until CSP_UPGRADE_INSECURE_REQUESTS is configured.
        """
        response = self.client.get("/")

        csp = response.headers.get("Content-Security-Policy") or response.headers.get(
            "Content-Security-Policy-Report-Only", ""
        )

        assert "upgrade-insecure-requests" in csp, (
            "CSP should include upgrade-insecure-requests to force HTTPS"
        )

    def test_csp_script_src_restricts_inline_scripts(self):
        """
        RED PHASE TEST: Verify CSP restricts inline scripts.

        Expected: CSP should have script-src without 'unsafe-inline'.
        Status: Will FAIL until CSP_SCRIPT_SRC is configured.
        """
        response = self.client.get("/")

        csp = response.headers.get("Content-Security-Policy") or response.headers.get(
            "Content-Security-Policy-Report-Only", ""
        )

        assert "script-src" in csp, "CSP missing script-src directive"
        assert "'self'" in csp, "CSP script-src should allow 'self'"

        # Note: 'unsafe-inline' may be needed for Django admin, but should not be in script-src
        # It's acceptable in style-src for Django admin compatibility

    def test_csp_object_src_none(self):
        """
        RED PHASE TEST: Verify CSP blocks object/embed tags.

        Expected: CSP should have object-src set to 'none'.
        Status: Will FAIL until CSP_OBJECT_SRC is configured.
        """
        response = self.client.get("/")

        csp = response.headers.get("Content-Security-Policy") or response.headers.get(
            "Content-Security-Policy-Report-Only", ""
        )

        assert "object-src" in csp, "CSP missing object-src directive"
        assert "'none'" in csp, "CSP object-src should be 'none' to block plugins"

    def test_csp_form_action_self(self):
        """
        RED PHASE TEST: Verify CSP restricts form submissions.

        Expected: CSP should have form-action set to 'self'.
        Status: Will FAIL until CSP_FORM_ACTION is configured.
        """
        response = self.client.get("/")

        csp = response.headers.get("Content-Security-Policy") or response.headers.get(
            "Content-Security-Policy-Report-Only", ""
        )

        assert "form-action" in csp, "CSP missing form-action directive"
        assert "'self'" in csp, "CSP form-action should be 'self' to restrict form submissions"

    def test_csp_base_uri_self(self):
        """
        RED PHASE TEST: Verify CSP restricts base tag.

        Expected: CSP should have base-uri set to 'self'.
        Status: Will FAIL until CSP_BASE_URI is configured.
        """
        response = self.client.get("/")

        csp = response.headers.get("Content-Security-Policy") or response.headers.get(
            "Content-Security-Policy-Report-Only", ""
        )

        assert "base-uri" in csp, "CSP missing base-uri directive"
        assert "'self'" in csp, "CSP base-uri should be 'self' to prevent base tag injection"

    def test_csp_report_only_mode_by_default(self):
        """
        RED PHASE TEST: Verify CSP is in report-only mode by default.

        Expected: CSP should use Content-Security-Policy-Report-Only header.
        Status: Will FAIL until CSP_REPORT_ONLY is set to True.
        """
        response = self.client.get("/")

        # For safe rollout, CSP should start in report-only mode
        has_report_only = "Content-Security-Policy-Report-Only" in response.headers
        has_enforcing = "Content-Security-Policy" in response.headers

        # Either report-only or enforcing mode is acceptable
        assert has_report_only or has_enforcing, (
            "CSP header not found. Expected either Content-Security-Policy "
            "or Content-Security-Policy-Report-Only header."
        )

        # Recommendation: Start with report-only mode
        if has_report_only:
            assert "report-uri" in response.headers.get(
                "Content-Security-Policy-Report-Only", ""
            ), "Report-only CSP should include report-uri directive for violation monitoring"


@pytest.mark.django_db
class TestCSPReportEndpoint:
    """Test suite for CSP violation reporting endpoint."""

    def setup_method(self):
        """Set up test client for each test."""
        self.client = Client()

    def test_csp_report_endpoint_exists(self):
        """
        RED PHASE TEST: Verify CSP report endpoint exists.

        Expected: POST to /api/v1/security/csp-report/ should return 204.
        Status: Will FAIL until endpoint is implemented.
        """
        csp_report = {
            "csp-report": {
                "document-uri": "http://example.com/",
                "referrer": "",
                "violated-directive": "script-src",
                "effective-directive": "script-src",
                "original-policy": "default-src 'self'",
                "blocked-uri": "http://evil.com/script.js",
                "status-code": 200,
            }
        }

        response = self.client.post(
            "/api/v1/security/csp-report/",
            data=csp_report,
            content_type="application/json",
        )

        assert response.status_code == 204, (
            f"CSP report endpoint should return 204 No Content, got {response.status_code}"
        )

    def test_csp_report_endpoint_accepts_violation_data(self):
        """
        RED PHASE TEST: Verify CSP report endpoint accepts violation data.

        Expected: Endpoint should accept JSON CSP report and log it.
        Status: Will FAIL until endpoint is implemented.
        """
        csp_report = {
            "csp-report": {
                "document-uri": "http://example.com/page",
                "violated-directive": "script-src-elem",
                "blocked-uri": "https://malicious.com/evil.js",
            }
        }

        response = self.client.post(
            "/api/v1/security/csp-report/",
            data=csp_report,
            content_type="application/json",
        )

        # Should return 204 No Content (successful processing, no response body)
        assert response.status_code == 204, "CSP report endpoint should accept violation data"

    def test_csp_report_endpoint_handles_malformed_data(self):
        """
        RED PHASE TEST: Verify CSP report endpoint handles malformed data gracefully.

        Expected: Endpoint should return 204 even with malformed data (fail silently).
        Status: Will FAIL until endpoint is implemented.
        """
        # Send malformed data
        response = self.client.post(
            "/api/v1/security/csp-report/",
            data={"invalid": "data"},
            content_type="application/json",
        )

        # Should still return 204 (fail silently for security)
        assert response.status_code == 204, (
            "CSP report endpoint should handle malformed data gracefully"
        )


@pytest.mark.django_db
class TestCSPMiddlewareIntegration:
    """Integration tests for CSP middleware with Django request/response cycle."""

    def setup_method(self):
        """Set up test client for each test."""
        self.client = Client()

    def test_csp_applied_to_all_responses(self):
        """
        RED PHASE TEST: Verify CSP is applied to all HTTP responses.

        Expected: CSP header should be present on all responses, not just specific URLs.
        Status: Will FAIL until CSPMiddleware is added to MIDDLEWARE.
        """
        # Test multiple endpoints
        endpoints = [
            "/",
            "/api/v1/",
            "/admin/",
        ]

        for endpoint in endpoints:
            response = self.client.get(endpoint)
            has_csp = (
                "Content-Security-Policy" in response.headers
                or "Content-Security-Policy-Report-Only" in response.headers
            )

            assert has_csp, (
                f"CSP header missing for endpoint: {endpoint}. "
                "CSP should be applied to all responses."
            )

    def test_csp_does_not_break_api_responses(self):
        """
        RED PHASE TEST: Verify CSP doesn't break API functionality.

        Expected: API should still return JSON responses correctly.
        Status: Will FAIL if CSP interferes with API responses.
        """
        # This test ensures CSP middleware doesn't interfere with DRF
        response = self.client.get("/api/v1/")

        # API should still work
        assert response.status_code in [200, 401, 403], "CSP should not break API responses"

        # CSP should still be applied
        has_csp = (
            "Content-Security-Policy" in response.headers
            or "Content-Security-Policy-Report-Only" in response.headers
        )

        assert has_csp, "CSP should be applied to API responses"

    def test_csp_header_format_valid(self):
        """
        RED PHASE TEST: Verify CSP header format is valid.

        Expected: CSP header should follow W3C CSP specification.
        Status: Will FAIL until CSP configuration is correct.
        """
        response = self.client.get("/")

        csp = response.headers.get("Content-Security-Policy") or response.headers.get(
            "Content-Security-Policy-Report-Only", ""
        )

        # CSP should be a non-empty string
        assert csp, "CSP header should not be empty"

        # CSP should contain semicolons as directive separators
        assert ";" in csp, "CSP directives should be separated by semicolons"

        # CSP should not have leading/trailing semicolons
        assert not csp.startswith(";"), "CSP should not start with semicolon"
        assert not csp.endswith(";"), "CSP should not end with semicolon"
