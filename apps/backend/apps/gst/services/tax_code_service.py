"""
Tax Code service for LedgerSG GST module.

Manages GST tax codes including:
- Listing tax codes (seeded + custom)
- Creating custom tax codes
- Validating tax codes for invoices
- Getting current GST rate
"""

from typing import Optional, List, Dict, Any
from decimal import Decimal
from uuid import UUID
from datetime import date

from apps.core.models import TaxCode
from common.exceptions import ValidationError, DuplicateResource, ResourceNotFound


# IRAS-defined tax codes (seeded)
IRAS_TAX_CODES = {
    "SR": {
        "name": "Standard-Rated Supply",
        "rate": Decimal("0.0900"),
        "is_gst_charged": True,
        "is_input": False,
        "is_output": True,
        "description": "Standard-rated supplies (9% GST)",
        "f5_supply_box": 1,
        "f5_tax_box": 6,
    },
    "ZR": {
        "name": "Zero-Rated Supply",
        "rate": Decimal("0.0000"),
        "is_gst_charged": True,
        "is_input": False,
        "is_output": True,
        "description": "Zero-rated supplies (exports, international services)",
        "f5_supply_box": 2,
    },
    "ES": {
        "name": "Exempt Supply",
        "rate": Decimal("0.0000"),
        "is_gst_charged": False,
        "is_input": False,
        "is_output": True,
        "description": "Exempt supplies (financial services, residential rent)",
        "f5_supply_box": 3,
    },
    "OS": {
        "name": "Out-of-Scope Supply",
        "rate": Decimal("0.0000"),
        "is_gst_charged": False,
        "is_input": False,
        "is_output": True,
        "description": "Out-of-scope supplies (asset sales, private transactions)",
    },
    "TX": {
        "name": "Taxable Purchase",
        "rate": Decimal("0.0900"),
        "is_gst_charged": True,
        "is_input": True,
        "is_output": False,
        "description": "Taxable purchases with GST incurred",
        "f5_purchase_box": 5,
        "f5_tax_box": 7,
    },
    "IM": {
        "name": "Import Supply",
        "rate": Decimal("0.0900"),
        "is_gst_charged": True,
        "is_input": True,
        "is_output": False,
        "description": "Imported goods (GST paid at customs)",
        "f5_purchase_box": 5,
        "f5_tax_box": 7,
    },
    "BL": {
        "name": "Blocked Input Tax",
        "rate": Decimal("0.0900"),
        "is_gst_charged": True,
        "is_input": True,
        "is_output": False,
        "is_claimable": False,
        "description": "GST incurred but blocked from claiming (e.g. motor vehicles)",
        "f5_purchase_box": 5,
    },
    "NA": {
        "name": "Not Applicable",
        "rate": Decimal("0.0000"),
        "is_gst_charged": False,
        "is_input": True,
        "is_output": True,
        "description": "Transactions where GST is not applicable",
    },
}


class TaxCodeService:
    """Service class for tax code operations."""
    
    @staticmethod
    def list_tax_codes(
        org_id: UUID,
        is_active: Optional[bool] = None,
        is_gst_charged: Optional[bool] = None,
        include_system: bool = True,
        code: Optional[str] = None
    ) -> List[TaxCode]:
        """
        List tax codes for an organisation.
        """
        from django.db.models import Q
        queryset = TaxCode.objects.filter(Q(org_id=org_id) | Q(org_id__isnull=True))
        
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        
        if is_gst_charged is not None:
            queryset = queryset.filter(is_gst_charged=is_gst_charged)
        
        if code:
            queryset = queryset.filter(code=code.upper())
        
        if not include_system:
            queryset = queryset.filter(org_id__isnull=False)
        
        return list(queryset.order_by("code"))
    
    @staticmethod
    def get_tax_code(org_id: UUID, tax_code_id: UUID) -> TaxCode:
        """
        Get tax code by ID.
        """
        from django.db.models import Q
        try:
            return TaxCode.objects.get(Q(id=tax_code_id) & (Q(org_id=org_id) | Q(org_id__isnull=True)))
        except TaxCode.DoesNotExist:
            raise ResourceNotFound(f"Tax code {tax_code_id} not found")
    
    @staticmethod
    def get_tax_code_by_code(org_id: UUID, code: str) -> Optional[TaxCode]:
        """
        Get tax code by code.
        """
        from django.db.models import Q
        try:
            return TaxCode.objects.filter(
                Q(code=code.upper()) & (Q(org_id=org_id) | Q(org_id__isnull=True))
            ).first()
        except TaxCode.DoesNotExist:
            return None
    
    @staticmethod
    def create_tax_code(
        org_id: UUID,
        code: str,
        name: str,
        rate: Optional[Decimal],
        is_gst_charged: bool,
        description: str = "",
        f5_supply_box: Optional[int] = None,
        f5_purchase_box: Optional[int] = None,
        f5_tax_box: Optional[int] = None,
        **kwargs
    ) -> TaxCode:
        """
        Create a custom tax code.
        """
        code = code.upper().strip()
        
        if not code:
            raise ValidationError("Tax code is required.")
        
        if code in IRAS_TAX_CODES:
            raise ValidationError(f"Tax code '{code}' is reserved.")
        
        if TaxCode.objects.filter(org_id=org_id, code=code).exists():
            raise DuplicateResource(f"Tax code '{code}' already exists.")
        
        tax_code = TaxCode.objects.create(
            org_id=org_id,
            code=code,
            name=name.strip(),
            rate=rate or Decimal("0.0000"),
            is_gst_charged=is_gst_charged,
            description=description.strip(),
            f5_supply_box=f5_supply_box,
            f5_purchase_box=f5_purchase_box,
            f5_tax_box=f5_tax_box,
            is_active=True,
            effective_from=date.today(),
            **kwargs
        )
        
        return tax_code
    
    @staticmethod
    def update_tax_code(org_id: UUID, tax_code_id: UUID, **updates) -> TaxCode:
        """
        Update tax code.
        """
        tax_code = TaxCodeService.get_tax_code(org_id, tax_code_id)
        
        # System codes (global) have limited update capability
        if tax_code.org_id is None:
            allowed_fields = {"description", "is_active"}
            for key in updates:
                if key not in allowed_fields:
                    raise ValidationError(f"Cannot modify '{key}' on system tax codes.")
        
        for key, value in updates.items():
            if hasattr(tax_code, key):
                setattr(tax_code, key, value)
        
        tax_code.save()
        return tax_code
    
    @staticmethod
    def deactivate_tax_code(org_id: UUID, tax_code_id: UUID) -> TaxCode:
        """
        Deactivate a custom tax code.
        """
        tax_code = TaxCodeService.get_tax_code(org_id, tax_code_id)
        if tax_code.org_id is None:
            raise ValidationError("System tax codes cannot be deactivated.")
        
        tax_code.is_active = False
        tax_code.save()
        return tax_code
    
    @staticmethod
    def validate_tax_code_for_invoice(
        org_id: UUID,
        tax_code_id: UUID,
        amount: Decimal,
        is_bcrs_deposit: bool = False
    ) -> Dict[str, Any]:
        """
        Validate tax code for an invoice line.
        """
        tax_code = TaxCodeService.get_tax_code(org_id, tax_code_id)
        
        if not tax_code.is_active:
            raise ValidationError(f"Tax code '{tax_code.code}' is not active.")
        
        if is_bcrs_deposit:
            return {
                "valid": True,
                "tax_code": tax_code.code,
                "rate": Decimal("0.0000"),
                "gst_amount": Decimal("0.0000"),
                "total_amount": amount,
            }
        
        if tax_code.rate is not None and tax_code.is_gst_charged:
            gst_amount = (amount * tax_code.rate).quantize(Decimal("0.0001"))
            total_amount = amount + gst_amount
        else:
            gst_amount = Decimal("0.0000")
            total_amount = amount
        
        return {
            "valid": True,
            "tax_code": tax_code.code,
            "rate": tax_code.rate,
            "gst_amount": gst_amount,
            "total_amount": total_amount,
            "f5_supply_box": tax_code.f5_supply_box,
            "f5_purchase_box": tax_code.f5_purchase_box,
            "f5_tax_box": tax_code.f5_tax_box,
        }
    
    @staticmethod
    def get_current_gst_rate(org_id: UUID, as_of_date: Optional[date] = None) -> Decimal:
        """
        Get current GST rate (SR code).
        """
        sr_code = TaxCodeService.get_tax_code_by_code(org_id, "SR")
        if sr_code and sr_code.rate is not None:
            return sr_code.rate
        return Decimal("0.0900")
    
    @staticmethod
    def seed_default_tax_codes(org_id: UUID) -> List[TaxCode]:
        """
        Seed default IRAS tax codes for a new organisation.
        """
        created = []
        for code, config in IRAS_TAX_CODES.items():
            if TaxCode.objects.filter(org_id=org_id, code=code).exists():
                continue
            
            tax_code = TaxCode.objects.create(
                org_id=org_id,
                code=code,
                name=config["name"],
                rate=config["rate"],
                is_gst_charged=config["is_gst_charged"],
                is_input=config.get("is_input", False),
                is_output=config.get("is_output", False),
                is_claimable=config.get("is_claimable", True),
                description=config["description"],
                f5_supply_box=config.get("f5_supply_box"),
                f5_purchase_box=config.get("f5_purchase_box"),
                f5_tax_box=config.get("f5_tax_box"),
                is_active=True,
                effective_from=date(2024, 1, 1),
            )
            created.append(tax_code)
        return created
    
    @staticmethod
    def get_iras_tax_codes_info() -> Dict[str, Any]:
        """
        Get information about IRAS-defined tax codes.
        """
        return {
            code: {
                "name": config["name"],
                "rate": str(config["rate"]),
                "is_gst_charged": config["is_gst_charged"],
                "description": config["description"],
            }
            for code, config in IRAS_TAX_CODES.items()
        }
