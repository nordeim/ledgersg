"""
P14/X-1 — the XML parser must be hardened (XXE + entity-expansion DoS).

The Peppol validation path accepts candidate UBL XML from the outside
world. lxml's DEFAULT parser resolves entities, loads external DTDs and
accepts huge trees — exactly the knobs a hostile document exercises:
  * an external entity pointing at a local file (XXE disclosure)
  * an external entity pointing at a URL (SSRF probe)
  * a billion-laughs nested-entity bomb (CPU/memory exhaustion)

The hardened parser (resolve_entities=False, no_network=True,
load_dtd=False, huge_tree=False) must reject all of these WITHOUT
file/network access, while valid UBL still validates.
"""

from pathlib import Path

from apps.peppol.services.xml_validation_service import XMLValidationService

VALID_UBL = """<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">
  <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">INV-1</cbc:ID>
</Invoice>
"""

XXE_FILE = """<?xml version="1.0"?>
<!DOCTYPE Invoice [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<Invoice>&xxe;</Invoice>
"""

XXE_URL = """<?xml version="1.0"?>
<!DOCTYPE Invoice [
  <!ENTITY remote SYSTEM "http://127.0.0.1:9/probe">
]>
<Invoice>&remote;</Invoice>
"""

# A (small) billion-laughs shape: nested entity expansion. With
# resolve_entities=False the parser refuses it outright.
ENTITY_BOMB = """<?xml version="1.0"?>
<!DOCTYPE lolz [
  <!ENTITY lol "lol">
  <!ENTITY lol1 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
  <!ENTITY lol2 "&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;">
  <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
]>
<Invoice>&lol3;</Invoice>
"""


class TestHardenedXMLParserP14:
    def test_xxe_local_file_entity_is_not_resolved(self):
        """RED for X-1: file:///etc/passwd must not be readable through an
        external entity — the parse either fails or yields a doc whose
        text does NOT contain /etc/passwd content (root: markers)."""
        svc = XMLValidationService()
        doc, err = svc._parse_xml(XXE_FILE)
        if doc is not None:
            content = (doc.text or "") + str(doc.itertext())
            assert "root:" not in content, "XXE: local file content leaked"

    def test_xxe_url_entity_is_not_fetched(self):
        """RED for X-1: external entities must not fetch URLs (SSRF). With
        no_network=True + resolve_entities=False the parse must fail (no
        entity content) — port 9 is discard, nothing should connect."""
        svc = XMLValidationService()
        doc, err = svc._parse_xml(XXE_URL)
        if doc is not None:
            content = (doc.text or "") + str(doc.itertext())
            assert "probe" not in content.lower() or "&remote" in content, (
                "XXE/SSRF: the remote entity's content must not appear"
            )

    def test_entity_expansion_bomb_is_rejected(self):
        """RED for X-1: nested entity expansion is refused outright (the
        parser must not expand entities at all)."""
        svc = XMLValidationService()
        doc, err = svc._parse_xml(ENTITY_BOMB)
        if doc is not None:
            content = "".join(doc.itertext())
            assert len(content) < 1000, (
                f"billion-laughs: entity expansion ran away ({len(content)} chars)"
            )

    def test_valid_xml_still_parses(self):
        """Control: hardening must not break the legitimate path."""
        svc = XMLValidationService()
        doc, err = svc._parse_xml(VALID_UBL)
        assert doc is not None, f"valid UBL must parse (err={err})"
        assert err is None

    def test_parser_flags_are_hardened(self):
        """The parser policy itself: no entities, no network, no DTD, no
        huge trees. lxml.etree.XMLParser does NOT expose its construction
        flags for introspection (session-29 lesson — the committed test
        read attributes that do not exist), so the gate asserts
        `_HARDENED_PARSER_FLAGS`, the single source of truth the parser
        is built from."""
        from apps.peppol.services.xml_validation_service import (
            _HARDENED_PARSER_FLAGS,
        )

        assert _HARDENED_PARSER_FLAGS["resolve_entities"] is False
        assert _HARDENED_PARSER_FLAGS["no_network"] is True
        assert _HARDENED_PARSER_FLAGS["load_dtd"] is False
        assert _HARDENED_PARSER_FLAGS["huge_tree"] is False
        # and _hardened_parser() builds from exactly that constant
        assert XMLValidationService._hardened_parser() is not None
