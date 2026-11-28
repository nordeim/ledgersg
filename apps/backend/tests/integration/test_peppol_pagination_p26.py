"""
P26 contract gates — the Peppol transmission-log pagination (BE-P26-M4).

The transmission log was the last unbounded backend list (the P25/I1
register): no limit/offset, no `id` tiebreaker on the -transmitted_at
order (the cross-page skip/dup hazard the P24 tiebreaker rule closed on
every other surface), and the three status counters
(pending/failed/completed) each a separate COUNT query per request.

This file pins the additive contract:

- `?limit=&offset=` paginates: next/previous absolute URLs, `count` the
  TOTAL matching rows, the counters still present in BOTH modes.
- `limit` absent: the envelope stays byte-identical
  {results, count, pending, failed, completed} (every existing consumer
  keeps working).
- The P25 rules ride along: garbage limit 400, huge offset 400,
  offset-without-limit 400.
- The `-transmitted_at, -id` tiebreaker: two rows sharing transmitted_at
  paginate without skip or dup (the forced-tie test).
- The counters stay within a `?status=` filter (the current semantics).
"""

from datetime import datetime, timedelta
from decimal import Decimal
from urllib.parse import parse_qs, urlparse

import pytest
from rest_framework import status

from apps.peppol.models import PeppolTransmissionLog

# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def peppol_fx(test_organisation, test_user, test_accounts, test_tax_codes, test_fiscal_period):
    """5 transmission-log rows for the org: 2 DELIVERED, 2 PENDING,
    1 FAILED — with rows 3 and 4 sharing one transmitted_at (the forced
    tie the tiebreaker test walks) and row 5 carrying NULL transmitted_at
    (the real-world PENDING shape). A second org's row proves isolation.
    All 5 attempts hang off ONE real document (the retry-trail shape —
    the FK demands a real invoicing.document row)."""
    fx = {"org": test_organisation, "user": test_user}

    from datetime import date

    from apps.core.models import DocumentSequence, Organisation
    from apps.invoicing.services import ContactService, DocumentService

    other_org = Organisation.objects.create(
        name="P26 Other Org",
        uen="T26OTHER888X",
        entity_type="PRIVATE_LIMITED",
        gst_registered=True,
        gst_reg_number="M26OTHER78K",
        gst_reg_date=date(2024, 1, 1),
        base_currency="SGD",
    )
    for org in (fx["org"], other_org):
        for doc_type, prefix in [("SALES_INVOICE", "INV-"), ("SALES_CREDIT_NOTE", "CN-")]:
            DocumentSequence.objects.get_or_create(
                org=org, document_type=doc_type, defaults={"prefix": prefix, "next_number": 1}
            )
    contact = ContactService.create_contact(
        org_id=fx["org"].id, name="P26 Peppol Customer", email="", is_customer=True
    )
    document = DocumentService.create_document(
        org_id=fx["org"].id,
        document_type="SALES_INVOICE",
        contact_id=contact.id,
        issue_date=date(2026, 2, 1),
        lines=[
            {
                "description": "P26 transmission-log probe",
                "account_id": str(test_accounts["4000"].id),
                "quantity": "1.0000",
                "unit_price": "100.00",
                "tax_code_id": str(test_tax_codes["SR"].id),
            }
        ],
        user_id=fx["user"].id,
    )
    fx["document_id"] = document.id

    # The other org's minimal chart (the test_accounts fixture's shape) —
    # create_contact resolves the 1200 AR control account, and the
    # document line needs a revenue account.
    from apps.core.models import Account
    from apps.core.models.tax_code import TaxCode

    Account.objects.create(
        org=other_org,
        code="1200",
        name="Accounts Receivable",
        account_type="ASSET_CURRENT",
        is_system=True,
        is_active=True,
    )
    other_revenue = Account.objects.create(
        org=other_org,
        code="4000",
        name="Sales Revenue",
        account_type="REVENUE",
        is_system=True,
        is_active=True,
    )
    other_sr = TaxCode.objects.create(
        org=other_org,
        code="SR",
        name="Standard-Rated",
        description="Standard-Rated Supply",
        rate=Decimal("0.09"),
        is_gst_charged=True,
        is_input=False,
        is_output=True,
        is_claimable=True,
        f5_supply_box=1,
        f5_purchase_box=None,
        f5_tax_box=6,
        is_active=True,
        effective_from=date(2024, 1, 1),
    )
    other_contact = ContactService.create_contact(
        org_id=other_org.id, name="P26 Other Customer", email="", is_customer=True
    )
    other_document = DocumentService.create_document(
        org_id=other_org.id,
        document_type="SALES_INVOICE",
        contact_id=other_contact.id,
        issue_date=date(2026, 2, 1),
        lines=[
            {
                "description": "P26 other-org probe",
                "account_id": str(other_revenue.id),
                "quantity": "1.0000",
                "unit_price": "100.00",
                "tax_code_id": str(other_sr.id),
            }
        ],
        user_id=fx["user"].id,
    )
    fx["other_org"] = other_org

    base = datetime(2026, 3, 1, 12, 0, 0)
    rows = [
        # (status, minutes-offset-from-base, document-seed)
        ("DELIVERED", 0, "11111111"),
        ("PENDING", 10, "22222222"),
        ("FAILED", 20, "33333333"),  # shares transmitted_at with the next row
        ("DELIVERED", 20, "44444444"),
        ("PENDING", None, "55555555"),  # NULL transmitted_at (never sent)
    ]
    for status_value, _minutes, _seed in rows:
        PeppolTransmissionLog.objects.create(
            org=fx["org"],
            document_id=document.id,
            status=status_value,
            attempt_number=1,
        )
    # The bulk UPDATE bypasses auto_now_add: pin exact transmitted_at
    # values (row i lands at base + minutes; the NULL row stays NULL).
    rows_qs = PeppolTransmissionLog.objects.filter(org=fx["org"]).order_by("id")
    for row, (_, minutes, _seed) in zip(rows_qs, rows, strict=True):
        if minutes is not None:
            PeppolTransmissionLog.objects.filter(pk=row.pk).update(
                transmitted_at=base + timedelta(minutes=minutes)
            )
    # The other org's row must never leak through the org-scoped view.
    PeppolTransmissionLog.objects.create(
        org=other_org,
        document_id=other_document.id,
        status="DELIVERED",
        attempt_number=1,
    )
    return fx


def _url(fx):
    return f"/api/v1/{fx['org'].id}/peppol/transmission-log/"


# ---------------------------------------------------------------------------
# The paginated mode (BE-P26-M4)
# ---------------------------------------------------------------------------


class TestPeppolPaginationP26:
    @pytest.mark.django_db
    def test_limit_slices_and_count_is_the_total(self, auth_client, peppol_fx):
        response = auth_client.get(_url(peppol_fx) + "?limit=2")
        assert response.status_code == status.HTTP_200_OK, response.data
        assert len(response.data["results"]) == 2
        assert response.data["count"] == 5
        assert response.data["next"] is not None
        assert response.data["previous"] is None

    @pytest.mark.django_db
    def test_next_previous_boundaries(self, auth_client, peppol_fx):
        response = auth_client.get(_url(peppol_fx) + "?limit=2&offset=4")
        assert response.status_code == status.HTTP_200_OK, response.data
        assert len(response.data["results"]) == 1
        assert response.data["count"] == 5
        assert response.data["next"] is None
        assert response.data["previous"] is not None
        # The previous URL carries limit+offset (DRF semantics).
        parsed = urlparse(response.data["previous"])
        assert parse_qs(parsed.query)["offset"] == ["2"]
        assert parse_qs(parsed.query)["limit"] == ["2"]

    @pytest.mark.django_db
    def test_next_is_an_absolute_url_carrying_the_callers_filter(
        self, auth_client, peppol_fx
    ):
        response = auth_client.get(_url(peppol_fx) + "?status=DELIVERED&limit=1")
        assert response.status_code == status.HTTP_200_OK, response.data
        parsed = urlparse(response.data["next"])
        assert parsed.scheme and parsed.netloc  # absolute
        query = parse_qs(parsed.query)
        assert query["limit"] == ["1"]
        assert query["offset"] == ["1"]
        assert query["status"] == ["DELIVERED"]  # the filter survives paging

    @pytest.mark.django_db
    def test_the_paginated_mode_still_carries_the_counters(
        self, auth_client, peppol_fx
    ):
        response = auth_client.get(_url(peppol_fx) + "?limit=2")
        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["pending"] == 2
        assert response.data["failed"] == 1
        assert response.data["completed"] == 2

    @pytest.mark.django_db
    def test_the_paginated_mode_never_leaks_other_orgs_rows(
        self, auth_client, peppol_fx
    ):
        response = auth_client.get(_url(peppol_fx) + "?limit=50")
        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["count"] == 5
        org_ids = {str(peppol_fx["org"].id)}
        assert all(
            str(PeppolTransmissionLog.objects.get(id=r["id"]).org_id) in org_ids
            for r in response.data["results"]
        )


# ---------------------------------------------------------------------------
# The unpaginated mode stays byte-identical (the back-compat contract)
# ---------------------------------------------------------------------------


class TestPeppolUnpaginatedContractP26:
    @pytest.mark.django_db
    def test_no_limit_returns_the_full_envelope_with_counters(
        self, auth_client, peppol_fx
    ):
        response = auth_client.get(_url(peppol_fx))
        assert response.status_code == status.HTTP_200_OK, response.data
        body = response.data
        assert set(body.keys()) == {
            "results",
            "count",
            "pending",
            "failed",
            "completed",
        }
        assert len(body["results"]) == 5
        assert body["count"] == 5
        assert body["pending"] == 2
        assert body["failed"] == 1
        assert body["completed"] == 2

    @pytest.mark.django_db
    def test_counters_stay_within_a_status_filter(self, auth_client, peppol_fx):
        """The current semantics: the counters count the FILTERED set —
        pinned here so the single-query rewrite cannot drift them."""
        response = auth_client.get(_url(peppol_fx) + "?status=PENDING")
        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["count"] == 2
        assert response.data["pending"] == 2
        assert response.data["failed"] == 0
        assert response.data["completed"] == 0


# ---------------------------------------------------------------------------
# The P25 rules ride along (typed 400s on this surface too)
# ---------------------------------------------------------------------------


class TestPeppolPagination400sP26:
    @pytest.mark.django_db
    def test_garbage_limit_is_a_typed_400(self, auth_client, peppol_fx):
        response = auth_client.get(_url(peppol_fx) + "?limit=abc")
        assert response.status_code == status.HTTP_400_BAD_REQUEST, (
            f"garbage limit must be a 400, got {response.status_code}: {getattr(response, 'data', '')}"
        )
        assert "limit" in str(response.data)

    @pytest.mark.django_db
    def test_huge_offset_is_a_typed_400(self, auth_client, peppol_fx):
        response = auth_client.get(
            _url(peppol_fx) + "?limit=1&offset=99999999999999999999"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST, (
            f"the huge offset must be a 400, got {response.status_code}"
        )
        assert "offset" in str(response.data)

    @pytest.mark.django_db
    def test_offset_without_limit_is_a_typed_400(self, auth_client, peppol_fx):
        response = auth_client.get(_url(peppol_fx) + "?offset=2")
        assert response.status_code == status.HTTP_400_BAD_REQUEST, (
            f"offset without limit must be a 400, got {response.status_code}"
        )
        assert "limit" in str(response.data)


# ---------------------------------------------------------------------------
# The id tiebreaker (the cross-page skip/dup hazard)
# ---------------------------------------------------------------------------


class TestPeppolTiebreakerP26:
    @pytest.mark.django_db
    def test_forced_tie_paginates_without_skip_or_dup(self, auth_client, peppol_fx):
        """Rows 3 and 4 share transmitted_at (the forced tie): paging
        limit=1 through the whole set must yield every row exactly once
        in a deterministic order — the `id` tiebreaker's contract."""
        seen: list[str] = []
        offset = 0
        while True:
            response = auth_client.get(_url(peppol_fx) + f"?limit=1&offset={offset}")
            assert response.status_code == status.HTTP_200_OK, response.data
            results = response.data["results"]
            if not results:
                break
            seen.append(results[0]["id"])
            offset += 1
            assert offset <= 10, "the walk must terminate"

        assert len(seen) == 5
        assert len(set(seen)) == 5  # no dup
        all_ids = set(
            PeppolTransmissionLog.objects.filter(
                org=peppol_fx["org"]
            ).values_list("id", flat=True)
        )
        assert set(seen) == {str(i) for i in all_ids}  # no skip

    @pytest.mark.django_db
    def test_same_tie_order_is_stable_across_identical_queries(
        self, auth_client, peppol_fx
    ):
        """Two identical paginated queries must return the same order —
        the pre-P26 order (-transmitted_at only) was tie-broken by
        Postgres whim, not contract."""
        first = auth_client.get(_url(peppol_fx) + "?limit=5")
        second = auth_client.get(_url(peppol_fx) + "?limit=5")
        ids_first = [r["id"] for r in first.data["results"]]
        ids_second = [r["id"] for r in second.data["results"]]
        assert ids_first == ids_second
