<?xml version="1.0" encoding="UTF-8"?>
<schema xmlns="http://purl.oclc.org/dsdl/schematron"
        queryBinding="xslt">
  <title>PINT-SG Validation Rules - LedgerSG business-rule layer (P35)</title>

  <!--
    The business-rule layer ABOVE the XSD layer (P34 made the XSD real;
    P35 wires this layer). The XSD enforces STRUCTURE; these rules carry
    the cross-element truths an XSD cannot express.

    P35/BE-P35-H1(a): this artefact was previously UNPARSEABLE by any
    ISO-Schematron implementation - it declared the WRONG namespace
    (http://purl.oclc.org/dml/schematron - a typo of dsdl) and an
    unsupported queryBinding="xslt2" (an XSLT 2.0 binding needs Saxon;
    lxml ships only the XSLT 1.0 skeleton). queryBinding="xslt" is the
    binding the shipped skeleton supports: every rule below is
    deterministic under XPath 1.0.

    Deliberately OUT of this rule set (registered, not faked): the
    ISO-4217 VOCABULARY check stays at the input surfaces (P34/M1,
    common/currency.py) - a regex code list here would duplicate the
    allowlist in an untestable artefact; this layer checks the SHAPE.

    P36 adds the ARITHMETIC pattern below (the BR-CO calculation rules -
    the registered P35-deferred axis). The XPath 1.0 precision resolution:
    every construction-exact rule compares with the half-unit of the last
    decimal place (0.00005 - absorbs the IEEE-double representation error
    of sum(), fails on any real disagreement at the DB's 0.0001 scale);
    absent elements are read via sum() (an empty node-set sums to 0 - a
    missing element inside an arithmetic expression is NaN and silently
    fails every comparison); BR-CO-17 carries the per-line rounding bound
    (the DB rounds GST per line to 2dp - IRAS cent-level - so the category
    tax is a sum of per-line roundings and |tax - taxable*rate/100| is
    bounded by 0.005 x line count: sound, never false-rejecting). The
    line count is the TOTAL line count (lines carry no tax category in
    this XML shape, so the per-category count is unavailable; the total
    is the conservative multiplier).

    Deliberately OUT (registered): BR-CO-11/12 (document-level
    allowance/charge arithmetic - the generator emits neither element,
    N/A until the mapper grows them); BR-CO-18 (at least one VAT
    breakdown - a deposit-only document legitimately carries zero
    subtotals); BR-CO-16's rounding-amount term (PayableRoundingAmount
    is never emitted).
  -->

  <ns prefix="ubl" uri="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"/>
  <ns prefix="ublcn" uri="urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2"/>
  <ns prefix="cbc" uri="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"/>
  <ns prefix="cac" uri="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"/>

  <pattern id="PINT-SG-BASIC">

    <rule context="/">
      <assert test="ubl:Invoice or ublcn:CreditNote" role="PINT-SG-BR-SG-01">
        BR-SG-01: Document root must be an Invoice or a CreditNote
      </assert>
    </rule>

    <rule context="ubl:Invoice | ublcn:CreditNote">
      <assert test="cbc:ID" role="PINT-SG-BR-SG-02">
        BR-SG-02: Document must carry a cbc:ID
      </assert>
      <assert test="cbc:IssueDate" role="PINT-SG-BR-SG-03">
        BR-SG-03: Document must carry a cbc:IssueDate
      </assert>
      <!-- XPath 1.0 has no matches(): the translate idiom checks the shape
           (3 chars, all uppercase A-Z; non-ASCII letters fail translate's
           explicit alphabet, deliberately). -->
      <assert test="string-length(cbc:DocumentCurrencyCode) = 3 and translate(cbc:DocumentCurrencyCode, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', '') = ''" role="PINT-SG-BR-SG-04">
        BR-SG-04: DocumentCurrencyCode must be an uppercase 3-letter ISO-4217-shaped code
      </assert>
      <!-- The BR-08 analog; the XSD enforces it too (minOccurs=1) - the
           business floor is deliberate redundancy. -->
      <assert test="count(cac:InvoiceLine | cac:CreditNoteLine) &gt;= 1" role="PINT-SG-BR-SG-05">
        BR-SG-05: Document must carry at least one line
      </assert>
    </rule>

    <!-- The flagship cross-element rule - the P33 currency-truth pin.
         Every amount element the generator emits, on both document paths:
         a document whose amounts disagree with its own currency header is
         internally inconsistent UBL and must not be transmitted. -->
    <rule context="cbc:LineExtensionAmount | cbc:TaxAmount | cbc:TaxableAmount | cbc:TaxExclusiveAmount | cbc:TaxInclusiveAmount | cbc:PayableAmount | cbc:PrepaidAmount | cbc:PriceAmount">
      <assert test="@currencyID = (ancestor::ubl:Invoice | ancestor::ublcn:CreditNote)/cbc:DocumentCurrencyCode" role="PINT-SG-BR-SG-06">
        BR-SG-06: Every amount's currencyID must equal the document's DocumentCurrencyCode
      </assert>
    </rule>

  </pattern>

  <!-- P36: the BR-CO calculation rules - the arithmetic truth above the
       currency truth. The generator computes every total from the DB's
       NUMERIC(19,4) Decimals (total_excl = sum of line amounts, gst_total
       = sum of line GST with deposits exempt, total_incl = total_excl +
       gst_total, payable = total_incl - amount_paid), so these invariants
       hold by construction in emitted XML; this pattern converts
       construction-truth into checked-truth - a tampered or corrupted
       document no longer validates clean. Relative paths from
       LegalMonetaryTotal use ../ (the parent IS the document root). -->
  <pattern id="PINT-SG-ARITHMETIC">

    <rule context="cac:LegalMonetaryTotal">
      <!-- BR-CO-10: sum of line net amounts == LineExtensionAmount
           (sum() over an empty node-set is 0 - the absent-element NaN
           trap avoided). -->
      <assert test="(sum(../cac:InvoiceLine/cbc:LineExtensionAmount |
                         ../cac:CreditNoteLine/cbc:LineExtensionAmount)
                    - cbc:LineExtensionAmount) &lt; 0.00005 and
                    (cbc:LineExtensionAmount
                    - sum(../cac:InvoiceLine/cbc:LineExtensionAmount |
                          ../cac:CreditNoteLine/cbc:LineExtensionAmount))
                    &lt; 0.00005"
              role="PINT-SG-BR-CO-10">
        BR-CO-10: Sum of line net amounts must equal the document LineExtensionAmount
      </assert>
      <!-- BR-CO-13 in the repo's no-allowance/charge form: the generator
           emits no document-level allowances or charges, so the general
           rule reduces to TaxExclusive == LineExtension. -->
      <assert test="(cbc:TaxExclusiveAmount - cbc:LineExtensionAmount) &lt; 0.00005 and
                    (cbc:LineExtensionAmount - cbc:TaxExclusiveAmount) &lt; 0.00005"
              role="PINT-SG-BR-CO-13">
        BR-CO-13: TaxExclusiveAmount must equal LineExtensionAmount (no document-level allowances or charges)
      </assert>
      <!-- BR-CO-15: TaxInclusive == TaxExclusive + the total tax amount
           (0 when the element is absent - sum() over an empty node-set). -->
      <assert test="(cbc:TaxInclusiveAmount
                    - cbc:TaxExclusiveAmount
                    - sum(../cac:TaxTotal/cbc:TaxAmount)) &lt; 0.00005 and
                    (cbc:TaxExclusiveAmount
                    + sum(../cac:TaxTotal/cbc:TaxAmount)
                    - cbc:TaxInclusiveAmount) &lt; 0.00005"
              role="PINT-SG-BR-CO-15">
        BR-CO-15: TaxInclusiveAmount must equal TaxExclusiveAmount plus the total tax amount
      </assert>
      <!-- BR-CO-16: Payable == TaxInclusive - Prepaid (0 when absent;
       the PayableRoundingAmount term is never emitted by the generator). -->
      <assert test="(cbc:PayableAmount - cbc:TaxInclusiveAmount
                    + sum(cbc:PrepaidAmount)) &lt; 0.00005 and
                    (cbc:TaxInclusiveAmount
                    - sum(cbc:PrepaidAmount)
                    - cbc:PayableAmount) &lt; 0.00005"
              role="PINT-SG-BR-CO-16">
        BR-CO-16: PayableAmount must equal TaxInclusiveAmount minus PrepaidAmount
      </assert>
    </rule>

    <rule context="cac:TaxTotal[cbc:TaxAmount]">
      <!-- BR-CO-14: the total tax == the sum of the subtotal taxes (exact
           by construction: deposit lines are GST-exempt, so the non-deposit
           subtotal sums equal the document total; no subtotals sums to 0). -->
      <assert test="(cbc:TaxAmount - sum(cac:TaxSubtotal/cbc:TaxAmount)) &lt; 0.00005 and
                    (sum(cac:TaxSubtotal/cbc:TaxAmount) - cbc:TaxAmount) &lt; 0.00005"
              role="PINT-SG-BR-CO-14">
        BR-CO-14: The total tax amount must equal the sum of the tax-subtotal tax amounts
      </assert>
    </rule>

    <rule context="cac:TaxSubtotal[cbc:TaxAmount][cbc:TaxableAmount][cac:TaxCategory/cbc:Percent]">
      <!-- BR-CO-17 with the per-line rounding bound: the DB rounds GST per
           line to 2dp (IRAS cent-level), so the category tax is a sum of
           per-line roundings, NOT a rounding of the category sum - a naive
           equality would false-reject legitimate documents (3 x 5.55 at
           9%: 1.50 vs 1.4985). The bound: |tax - taxable*rate/100| <=
           0.005 x (total line count) - sound (each line's rounding
           contributes at most half a cent) and tight enough to catch
           gross tampering. -->
      <assert test="(cbc:TaxAmount
                     - cbc:TaxableAmount * cac:TaxCategory/cbc:Percent div 100
                     - 0.005 * count(../..//cac:InvoiceLine |
                                     ../..//cac:CreditNoteLine)
                     - 0.00005) &lt; 0 and
                    (cbc:TaxableAmount * cac:TaxCategory/cbc:Percent div 100
                     - cbc:TaxAmount
                     - 0.005 * count(../..//cac:InvoiceLine |
                                     ../..//cac:CreditNoteLine)
                     - 0.00005) &lt; 0"
              role="PINT-SG-BR-CO-17">
        BR-CO-17: The tax-subtotal tax amount must equal the taxable amount times the rate, within the per-line rounding allowance
      </assert>
    </rule>

  </pattern>
</schema>

