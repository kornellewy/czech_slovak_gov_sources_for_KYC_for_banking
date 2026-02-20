"""Field mapping utilities for normalizing data from different sources."""

from datetime import datetime
from typing import Dict, Any, Optional, List

from config.constants import (
    ARES_ENTITY_URL_TEMPLATE, ORSR_SEARCH_URL_TEMPLATE,
    RPO_ENTITY_URL_TEMPLATE, RPVS_ENTITY_URL_TEMPLATE,
    FINANCNA_ENTITY_URL_TEMPLATE, ESM_ENTITY_URL_TEMPLATE,
    JUSTICE_ENTITY_URL_TEMPLATE
)


# Field name mappings from source-specific to standardized names
FIELD_MAPPINGS = {
    "obchodniJmeno": "name",
    "obchodne_meno": "name",
    "company_name": "name",
    "nazev": "name",
    "ico": "ico",
    "ico_number": "ico",
    "dic": "dic",
    "tax_id": "dic",
    "pravniForma": "legal_form",
    "legal_form_code": "legal_form",
    "statutarniOrgan": "statutory_body",
    "sidlo": "address",
    "adresa": "address",
}

# Status value mappings to normalized values
STATUS_MAPPINGS = {
    "aktivní": "active",
    "aktivni": "active",
    "active": "active",
    "aktívne": "active",
    "činný": "active",
    "cinný": "active",
    "cenny": "active",
    "zrušený": "cancelled",
    "zruseny": "cancelled",
    "cancelled": "cancelled",
    "zrušena": "cancelled",
    "zrusena": "cancelled",
    "likvidace": "liquidation",
    "liquidation": "liquidation",
    "v likvidaci": "liquidation",
    "konkurz": "bankruptcy",
    "bankruptcy": "bankruptcy",
    "neaktivní": "inactive",
    "neaktivni": "inactive",
    "inactive": "inactive",
}

# Holder type mappings
HOLDER_TYPE_MAPPINGS = {
    "natural_person": "individual",
    "fyzicka_osoba": "individual",
    "individual": "individual",
    "legal_entity": "entity",
    "pravnicka_osoba": "entity",
    "entity": "entity",
    "corporate": "entity",
}


def get_retrieved_at() -> str:
    """Get current timestamp in ISO format.

    Returns:
        ISO formatted timestamp string
    """
    return datetime.utcnow().isoformat() + "Z"


def normalize_status(status: Optional[str]) -> str:
    """Normalize status value to standard format.

    Args:
        status: Status value from source

    Returns:
        Normalized status value
    """
    if not status:
        return "unknown"

    return STATUS_MAPPINGS.get(status.lower().strip(), status.lower())


def map_holder_type(holder_type: Optional[str]) -> str:
    """Map holder type to standard format.

    Args:
        holder_type: Holder type from source

    Returns:
        Standardized holder type
    """
    if not holder_type:
        return "unknown"

    return HOLDER_TYPE_MAPPINGS.get(holder_type.lower().strip(), holder_type.lower())


def normalize_source(source: str) -> str:
    """Normalize source name by removing country suffix.

    Args:
        source: Source name (e.g., "ARES_CZ")

    Returns:
        Normalized source name (e.g., "ARES")
    """
    if "_" in source:
        return source.split("_")[0]
    return source


def build_entity_url(source: str, ico: str, **kwargs) -> Optional[str]:
    """Build direct URL to entity in source register.

    Args:
        source: Source name
        ico: Company identification number
        **kwargs: Additional URL parameters

    Returns:
        Direct URL to entity or None if source not supported
    """
    source_upper = source.upper()

    if "ARES" in source_upper:
        return ARES_ENTITY_URL_TEMPLATE.format(ico=ico)
    elif "ORSR" in source_upper:
        return ORSR_SEARCH_URL_TEMPLATE.format(ico=ico)
    elif "RPO" in source_upper:
        return RPO_ENTITY_URL_TEMPLATE.format(ico=ico)
    elif "RPVS" in source_upper:
        return RPVS_ENTITY_URL_TEMPLATE.format(ico=ico)
    elif "FINANCNA" in source_upper:
        return FINANCNA_ENTITY_URL_TEMPLATE.format(ico=ico)
    elif "ESM" in source_upper:
        return ESM_ENTITY_URL_TEMPLATE.format(ico=ico)
    elif "JUSTICE" in source_upper:
        return JUSTICE_ENTITY_URL_TEMPLATE.format(ico=ico)

    return None


def normalize_field_name(field_name: str) -> str:
    """Normalize field name to standard format.

    Args:
        field_name: Original field name

    Returns:
        Normalized field name
    """
    return FIELD_MAPPINGS.get(field_name, field_name)


def apply_field_mappings(data: Dict[str, Any], mappings: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Apply field mappings to data dictionary.

    Args:
        data: Original data dictionary
        mappings: Custom field mappings (optional)

    Returns:
        Data with normalized field names
    """
    if mappings is None:
        mappings = FIELD_MAPPINGS

    result = {}
    for key, value in data.items():
        new_key = mappings.get(key, key)
        result[new_key] = value

    return result


def add_retrieved_at(data: Dict[str, Any]) -> Dict[str, Any]:
    """Add retrieval timestamp to data.

    Args:
        data: Data dictionary

    Returns:
        Data with retrieved_at timestamp
    """
    if "retrieved_at" not in data:
        data["retrieved_at"] = get_retrieved_at()
    return data


def map_ownership_fields(ubo_data: Dict[str, Any]) -> Dict[str, Any]:
    """Map UBO ownership fields to standard format.

    Args:
        ubo_data: UBO data dictionary

    Returns:
        Data with standardized ownership fields
    """
    # Map ownership percentage field
    if "ownership_percentage" in ubo_data:
        ubo_data["ownership_pct_direct"] = ubo_data["ownership_percentage"]

    if "voting_rights_percentage" in ubo_data:
        ubo_data["voting_rights_pct"] = ubo_data["voting_rights_percentage"]

    return ubo_data
