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
    BR-CO-10..17 arithmetic rules (sum of line net amounts, payable =
    tax-inclusive - prepaid). XPath 1.0 sum() computes in IEEE doubles
    while the mapper emits NUMERIC(19,4) decimal strings; a naive
    equality compare is rounding-hazard flaky. The ISO-4217 VOCABULARY
    check stays at the input surfaces (P34/M1, common/currency.py) -
    a regex code list here would duplicate the allowlist in an
    untestable artefact; this layer checks the SHAPE.
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
</schema>
