<?xml version="1.0" encoding="UTF-8"?>
<schema xmlns="http://purl.oclc.org/dml/schematron"
        queryBinding="xslt2">
  <title>PINT-SG Validation Rules - Minimal version for LedgerSG</title>
  <ns prefix="ubl" uri="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"/>
  <ns prefix="cbc" uri="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"/>
  <ns prefix="cac" uri="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"/>
  
  <pattern id="PINT-SG-BASIC">
    <rule context="/">
      <assert test="ubl:Invoice or ubl:CreditNote">
        Document must be either Invoice or CreditNote
      </assert>
    </rule>
    
    <rule context="ubl:Invoice">
      <assert test="cbc:ID">
        Invoice must have an ID
      </assert>
      <assert test="cbc:IssueDate">
        Invoice must have an IssueDate
      </assert>
    </rule>
  </pattern>
</schema>
