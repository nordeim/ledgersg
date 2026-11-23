"""
GST Calculation service for LedgerSG.

Handles all GST calculations including:
- Line-level GST calculation
- BCRS deposit exemption
- Document totals
- Rounding per IRAS standards
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from uuid import UUID

from common.decimal_utils import money


class GSTCalculationService:
    """Service class for GST calculations."""

    # Singapore GST rate
    DEFAULT_GST_RATE = Decimal("0.09")  # 9%

    @staticmethod
    def calculate_line_gst(
        amount: Decimal,
        rate: Decimal,
        is_bcrs_deposit: bool = False,
        rounding: int = 2
    ) -> dict[str, Decimal]:
        """
        Calculate GST for a single line item.
        
        Singapore IRAS rules:
        - GST is calculated per line and rounded to 2 decimal places
        - BCRS (beverage container) deposits are GST exempt
        
        Args:
            amount: Line amount (excluding GST)
            rate: GST rate (e.g., 0.09 for 9%)
            is_bcrs_deposit: Whether this is a BCRS deposit
            rounding: Decimal places for rounding (default: 2)
            
        Returns:
            Dictionary with gst_amount, total_amount, net_amount
        """
        amount = money(amount)

        # BCRS deposits are GST exempt
        if is_bcrs_deposit:
            return {
                "net_amount": amount,
                "gst_amount": Decimal("0.00"),
                "total_amount": amount,
                "is_bcrs_exempt": True,
            }

        # Calculate GST
        if rate and rate > 0:
            gst_amount = (amount * rate).quantize(
                Decimal(f"0.{('0' * rounding)}1"),
                rounding=ROUND_HALF_UP
            )
        else:
            gst_amount = Decimal("0.00")

        total_amount = amount + gst_amount

        return {
            "net_amount": amount,
            "gst_amount": gst_amount,
            "total_amount": total_amount,
            "is_bcrs_exempt": False,
        }

    @staticmethod
    def calculate_document_gst(
        lines: list[dict[str, Any]],
        default_rate: Decimal = DEFAULT_GST_RATE
    ) -> dict[str, Any]:
        """
        Calculate GST for a document with multiple lines.
        
        Args:
            lines: List of line dictionaries with:
                - amount: Line amount
                - rate: GST rate (optional, uses default)
                - is_bcrs_deposit: Whether BCRS exempt
            default_rate: Default GST rate if not specified per line
            
        Returns:
            Document totals with breakdown
        """
        total_net = Decimal("0.00")
        total_gst = Decimal("0.00")
        total_amount = Decimal("0.00")
        bcrs_total = Decimal("0.00")

        line_results = []

        for line in lines:
            amount = money(line.get("amount", 0))
            rate = Decimal(str(line.get("rate", default_rate)))
            is_bcrs = line.get("is_bcrs_deposit", False)

            result = GSTCalculationService.calculate_line_gst(
                amount=amount,
                rate=rate,
                is_bcrs_deposit=is_bcrs
            )

            line_results.append({
                "line_id": line.get("id"),
                "net_amount": str(result["net_amount"]),
                "gst_amount": str(result["gst_amount"]),
                "total_amount": str(result["total_amount"]),
                "is_bcrs_exempt": result["is_bcrs_exempt"],
            })

            total_net += result["net_amount"]
            total_gst += result["gst_amount"]
            total_amount += result["total_amount"]

            if result["is_bcrs_exempt"]:
                bcrs_total += result["net_amount"]

        return {
            "lines": line_results,
            "summary": {
                "total_net": str(total_net.quantize(Decimal("0.01"))),
                "total_gst": str(total_gst.quantize(Decimal("0.01"))),
                "total_amount": str(total_amount.quantize(Decimal("0.01"))),
                "bcrs_exempt_total": str(bcrs_total.quantize(Decimal("0.01"))),
                "taxable_amount": str((total_net - bcrs_total).quantize(Decimal("0.01"))),
            }
        }

    @staticmethod
    def calculate_tax_inclusive_gst(
        total_amount: Decimal,
        rate: Decimal = DEFAULT_GST_RATE
    ) -> dict[str, Decimal]:
        """
        Calculate GST from a tax-inclusive amount.
        
        Used when total includes GST and we need to back-calculate.
        
        Formula: GST = Total - (Total / (1 + rate))
        
        Args:
            total_amount: Total amount including GST
            rate: GST rate
            
        Returns:
            Dictionary with net_amount, gst_amount, total_amount
        """
        total_amount = money(total_amount)

        if rate <= 0:
            return {
                "net_amount": total_amount,
                "gst_amount": Decimal("0.00"),
                "total_amount": total_amount,
            }

        # Calculate net amount
        net_amount = (total_amount / (1 + rate)).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        gst_amount = total_amount - net_amount

        return {
            "net_amount": net_amount,
            "gst_amount": gst_amount.quantize(Decimal("0.01")),
            "total_amount": total_amount,
        }

    @staticmethod
    def validate_gst_precision(
        calculated_gst: Decimal,
        expected_gst: Decimal,
        tolerance: Decimal = Decimal("0.01")
    ) -> bool:
        """
        Validate GST calculation matches expected within tolerance.
        
        IRAS allows 1 cent rounding difference.
        
        Args:
            calculated_gst: Our calculated GST
            expected_gst: Expected GST amount
            tolerance: Allowed difference (default: 0.01)
            
        Returns:
            True if within tolerance
        """
        diff = abs(calculated_gst - expected_gst)
        return diff <= tolerance

    @staticmethod
    def get_f5_box_amounts(
        org_id: UUID,
        period_start: str,
        period_end: str
    ) -> dict[str, Any]:
        """
        Calculate F5 form box amounts for a period.

        Aggregates posted documents against the tax codes' IRAS F5 box
        mapping columns (f5_supply_box / f5_purchase_box / f5_tax_box),
        honouring is_claimable for input tax and is_reverse_charge for Box 14.

        Box convention (matches gst.return columns, the DB CHECK constraints
        and IRAS):
            Box 1 = standard-rated supplies      Box 6 = output tax due
            Box 2 = zero-rated supplies          Box 7 = input tax claimed
            Box 3 = exempt supplies              Box 8 = Box 6 - Box 7
            Box 4 = Box 1 + Box 2 + Box 3       Box 13 = total revenue
            Box 5 = total taxable purchases      Box 14 = reverse charge

        Args:
            org_id: Organisation ID
            period_start: Period start date (YYYY-MM-DD)
            period_end: Period end date (YYYY-MM-DD)

        Returns:
            F5 box amounts dictionary
        """
        from django.db import connection

        # One query over document lines joined to their documents and tax
        # codes. Sales documents feed the supply/output side; purchase
        # documents feed the purchase/input side. VOID and DRAFT documents
        # are excluded; BCRS deposit lines are out of scope for GST.
        #
        # P11/H-3: only POSTING document types count — quotes and purchase
        # orders never post GL entries, so they must not feed statutory
        # boxes (a converted quote reaches APPROVED with the same lines as
        # its converted invoice — without this filter, F5 double-counts).
        # Credit notes net their boxes (IRAS: the return reports supplies
        # NET of credit notes issued in the period) — computed below via
        # the sign column.
        POSTING_TYPES = (
            "SALES_INVOICE", "SALES_CREDIT_NOTE", "SALES_DEBIT_NOTE",
            "PURCHASE_INVOICE", "PURCHASE_CREDIT_NOTE", "PURCHASE_DEBIT_NOTE",
        )
        placeholders = ", ".join(["%s"] * len(POSTING_TYPES))
        query = f"""
            SELECT
                tc.f5_supply_box,
                tc.f5_purchase_box,
                tc.f5_tax_box,
                tc.is_claimable,
                tc.is_reverse_charge,
                CASE WHEN d.document_type::text LIKE 'PURCHASE%%' THEN 'PURCHASE' ELSE 'SALES' END AS side,
                CASE WHEN d.document_type::text LIKE '%%CREDIT_NOTE' THEN -1 ELSE 1 END AS sign,
                SUM(dl.line_amount) AS total_amount,
                SUM(dl.gst_amount) AS total_gst
            FROM invoicing.document_line dl
            JOIN invoicing.document d ON d.id = dl.document_id
            JOIN gst.tax_code tc ON tc.id = dl.tax_code_id
            WHERE d.org_id = %s
                AND d.document_date BETWEEN %s AND %s
                AND d.status IN ('APPROVED', 'SENT', 'PARTIALLY_PAID', 'PAID', 'OVERDUE')
                AND d.document_type IN ({placeholders})
                AND COALESCE(dl.is_bcrs_deposit, FALSE) = FALSE
            GROUP BY 1, 2, 3, 4, 5, 6, 7
        """

        with connection.cursor() as cursor:
            cursor.execute(
                query, [str(org_id), period_start, period_end, *POSTING_TYPES]
            )
            rows = cursor.fetchall()

        boxes = {
            "box1": Decimal("0.00"),
            "box2": Decimal("0.00"),
            "box3": Decimal("0.00"),
            "box4": Decimal("0.00"),
            "box5": Decimal("0.00"),
            "box6": Decimal("0.00"),
            "box7": Decimal("0.00"),
            "box8": Decimal("0.00"),
            "box13": Decimal("0.00"),
            "box14": Decimal("0.00"),
        }

        for (
            supply_box,
            purchase_box,
            tax_box,
            is_claimable,
            is_reverse_charge,
            side,
            sign,
            amount,
            gst_amount,
        ) in rows:
            amount = Decimal(str(amount or 0)) * sign
            gst_amount = Decimal(str(gst_amount or 0)) * sign

            if side == "SALES":
                # Supplies feed Boxes 1/2/3 (net amounts, excluding GST)
                if supply_box in (1, 2, 3):
                    boxes[f"box{supply_box}"] += amount
                    boxes["box13"] += amount
                # Output tax feeds Box 6 via the tax-box mapping
                if tax_box == 6:
                    boxes["box6"] += gst_amount
            else:
                # Purchases feed Box 5 (total taxable purchases)
                if purchase_box == 5:
                    boxes["box5"] += amount
                # Input tax feeds Box 7 only when claimable (IRAS: blocked
                # and denied input tax — is_claimable = FALSE — never enters
                # Box 7 even though the purchase itself counts in Box 5)
                if tax_box == 7 and is_claimable:
                    boxes["box7"] += gst_amount
                # Reverse charge supplies (Box 14)
                if is_reverse_charge:
                    boxes["box14"] += amount

        # Derived boxes — the DB CHECKs (chk_box4_total, chk_box8_net)
        # enforce these identities for anything above DRAFT status.
        boxes["box4"] = boxes["box1"] + boxes["box2"] + boxes["box3"]
        boxes["box8"] = boxes["box6"] - boxes["box7"]

        return {
            box: str(value.quantize(Decimal("0.01")))
            for box, value in boxes.items()
        }


def calculate_gst_summary(
    net_amount: Decimal,
    gst_rate: Decimal = GSTCalculationService.DEFAULT_GST_RATE,
    is_bcrs_deposit: bool = False
) -> tuple[Decimal, Decimal, Decimal]:
    """
    Convenience function for GST calculation.
    
    Args:
        net_amount: Amount before GST
        gst_rate: GST rate (default 9%)
        is_bcrs_deposit: Whether BCRS exempt
        
    Returns:
        Tuple of (net_amount, gst_amount, total_amount)
    """
    result = GSTCalculationService.calculate_line_gst(
        amount=net_amount,
        rate=gst_rate,
        is_bcrs_deposit=is_bcrs_deposit
    )

    return (
        result["net_amount"],
        result["gst_amount"],
        result["total_amount"]
    )
