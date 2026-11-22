"""Serializers for the Peppol/InvoiceNow module."""

from rest_framework import serializers


class PeppolSettingsSerializer(serializers.Serializer):
    """Typed payload for the Peppol settings PATCH (P7/F-10 — the pre-P7
    raw setattr crashed on a non-numeric retry_attempts)."""

    enabled = serializers.BooleanField(required=False)
    participant_id = serializers.CharField(max_length=64, required=False, allow_blank=True)
    auto_transmit = serializers.BooleanField(required=False)
    access_point_provider = serializers.CharField(max_length=50, required=False, allow_blank=True)
    retry_attempts = serializers.IntegerField(min_value=0, max_value=10, required=False)
