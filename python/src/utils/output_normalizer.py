"""Unified output format normalizer for all scrapers.

This module provides standardized dataclasses and normalization functions
to ensure consistent output format across all scrapers (ARES, ORSR, RPO, RPVS,
Justice.cz, ESM, Finančná správa).

The unified format follows the specification:
- entity: Core company information
- holders: List of all holder types (shareholders, UBOs, statutory body, etc.)
- tax_info: Tax-related information
- metadata: Source and retrieval information
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Dict, Any, List
import json


# Country code mappings to ISO 3166-1 alpha-2
COUNTRY_CODE_MAPPINGS = {
    "slovensko": "SK",
    "slovakia": "SK",
    "slovak": "SK",
    "sk": "SK",
    "česká republika": "CZ",
    "ceska republika": "CZ",
    "czech republic": "CZ",
    "czechia": "CZ",
    "česko": "CZ",
    "cesko": "CZ",
    "cz": "CZ",
    "austria": "AT",
    "rakúsko": "AT",
    "rakousko": "AT",
    "at": "AT",
    "germany": "DE",
    "nemecko": "DE",
    "de": "DE",
    "italy": "IT",
    "taliansko": "IT",
    "it": "IT",
    "hungary": "HU",
    "maďarsko": "HU",
    "madarsko": "HU",
    "hu": "HU",
    "poland": "PL",
    "poľsko": "PL",
    "polsko": "PL",
    "pl": "PL",
    "united kingdom": "GB",
    "velká británia": "GB",
    "velka britanie": "GB",
    "gb": "GB",
    "uk": "GB",
    "usa": "US",
    "united states": "US",
    "spojené štáty": "US",
    "spojene staty": "US",
    "us": "US",
}

# Status value mappings to normalized values
STATUS_NORMALIZATIONS = {
    # Active variants
    "aktivní": "active",
    "aktivni": "active",
    "active": "active",
    "aktívny": "active",
    "aktívne": "active",
    "činný": "active",
    "cinný": "active",
    "cenny": "active",
    "zapsaný": "active",
    "zapsany": "active",
    # Cancelled variants
    "zrušený": "cancelled",
    "zruseny": "cancelled",
    "cancelled": "cancelled",
    "zrušena": "cancelled",
    "zrusena": "cancelled",
    "zrušená": "cancelled",
    "zrusena": "cancelled",
    "vymazaný": "cancelled",
    "vymazany": "cancelled",
    # Liquidation variants
    "likvidace": "in_liquidation",
    "liquidation": "in_liquidation",
    "v likvidaci": "in_liquidation",
    "v likvidácii": "in_liquidation",
    "in liquidation": "in_liquidation",
    # Bankruptcy variants
    "konkurz": "bankruptcy",
    "bankruptcy": "bankruptcy",
    "v konkurze": "bankruptcy",
    # Dissolved variants
    "zaniklý": "dissolved",
    "zanikly": "dissolved",
    "dissolved": "dissolved",
    "zaniknutý": "dissolved",
    "zaniknuty": "dissolved",
    # Suspended variants
    "pozastavený": "suspended",
    "pozastaveny": "suspended",
    "suspended": "suspended",
    # Inactive variants
    "neaktivní": "inactive",
    "neaktivni": "inactive",
    "inactive": "inactive",
}

# Register names for each source
REGISTER_NAMES = {
    "ARES_CZ": "Register of Economic Subjects (ARES)",
    "JUSTICE_CZ": "Commercial Register (Obchodní rejstřík)",
    "ESM_CZ": "Register of Beneficial Owners (Evidence skutečných majitelů)",
    "ORSR_SK": "Business Register (Obchodný register SR)",
    "RPO_SK": "Register of Legal Entities (Register právnických osôb)",
    "RPVS_SK": "Register of Public Sector Partners",
    "FINANCNA_SK": "Financial Administration (Finančná správa)",
    "STATS_SK": "Statistical Office of the Slovak Republic",
    "RUZ_SK": "Register of Financial Statements (Register účtovných závierok)",
    "NBS_SK": "National Bank of Slovakia - Financial Entities Register",
    "SMLOUVY_CZ": "Register of Public Contracts (Smlouvy.gov.cz)",
    "CNB_CZ": "Czech National Bank - Financial Supervision Registers",
    "IVES_SK": "Register of Non-Governmental Organizations (IVES)",
    "DPH_CZ": "VAT Register (Registr plátců DPH)",
    "VR_CZ": "Vermont Register (Register oddělovaných nemovitostí)",
    "RES_CZ": "Resident Income Tax Register (Rezidentní poplatek daně z příjmů)",
}

# Role value mappings
ROLE_MAPPINGS = {
    "ultimate_beneficial_owner": "beneficial_owner",
    "ubo": "beneficial_owner",
    "skutočný majiteľ": "beneficial_owner",
    "skutocny majitel": "beneficial_owner",
    "beneficial_owner": "beneficial_owner",
    "shareholder": "shareholder",
    "akcionár": "shareholder",
    "akcionar": "shareholder",
    "spoločník": "shareholder",
    "spolocnik": "shareholder",
    "statutory_body": "statutory_body",
    "štatutárny orgán": "statutory_body",
    "statutarny organ": "statutory_body",
    "jednatel": "statutory_body",
    "jednateľ": "statutory_body",
    "konateľ": "statutory_body",
    "konatel": "statutory_body",
    "predstavenstvo": "statutory_body",
    "dozorná rada": "statutory_body",
    "dozorna rada": "statutory_body",
    "prokurista": "procurist",
    "prokurist": "procurist",
    "liquidator": "liquidator",
    "likvidátor": "liquidator",
    "likvidator": "liquidator",
}


@dataclass
class Address:
    """Standardized address structure."""
    street: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    full_address: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class Entity:
    """Unified entity/company information."""
    ico_registry: str = ""
    company_name_registry: str = ""
    legal_form: Optional[str] = None
    legal_form_code: Optional[str] = None
    status: Optional[str] = None
    status_effective_date: Optional[str] = None
    incorporation_date: Optional[str] = None
    registered_address: Optional[Address] = None
    nace_codes: Optional[List[str]] = None
    vat_id: Optional[str] = None
    tax_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "ico_registry": self.ico_registry,
            "company_name_registry": self.company_name_registry,
        }
        if self.legal_form is not None:
            result["legal_form"] = self.legal_form
        if self.legal_form_code is not None:
            result["legal_form_code"] = self.legal_form_code
        if self.status is not None:
            result["status"] = self.status
        if self.status_effective_date is not None:
            result["status_effective_date"] = self.status_effective_date
        if self.incorporation_date is not None:
            result["incorporation_date"] = self.incorporation_date
        if self.registered_address is not None:
            result["registered_address"] = self.registered_address.to_dict()
        if self.nace_codes is not None:
            result["nace_codes"] = self.nace_codes
        if self.vat_id is not None:
            result["vat_id"] = self.vat_id
        if self.tax_id is not None:
            result["tax_id"] = self.tax_id
        return result


@dataclass
class Holder:
    """Unified holder/owner structure."""
    holder_type: str = "unknown"  # individual, entity, trust_fund
    role: str = "unknown"  # shareholder, beneficial_owner, statutory_body, procurist, liquidator
    name: str = ""
    ico: Optional[str] = None
    jurisdiction: Optional[str] = None  # ISO country code for entity holders
    citizenship: Optional[str] = None  # ISO country code for individuals
    date_of_birth: Optional[str] = None
    residency: Optional[str] = None  # ISO country code
    address: Optional[Address] = None
    ownership_pct_direct: float = 0.0
    voting_rights_pct: Optional[float] = None
    record_effective_from: Optional[str] = None
    record_effective_to: Optional[str] = None

    # Recursive ownership chain tracking
    chain_depth: int = 0
    is_ultimate: bool = False
    direct_ownership_pct: float = 0.0
    indirect_ownership_pct: float = 0.0
    ownership_path: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "holder_type": self.holder_type,
            "role": self.role,
            "name": self.name,
        }
        if self.ico is not None:
            result["ico"] = self.ico
        if self.jurisdiction is not None:
            result["jurisdiction"] = self.jurisdiction
        if self.citizenship is not None:
            result["citizenship"] = self.citizenship
        if self.date_of_birth is not None:
            result["date_of_birth"] = self.date_of_birth
        if self.residency is not None:
            result["residency"] = self.residency
        if self.address is not None:
            result["address"] = self.address.to_dict()
        result["ownership_pct_direct"] = self.ownership_pct_direct
        if self.voting_rights_pct is not None:
            result["voting_rights_pct"] = self.voting_rights_pct
        if self.record_effective_from is not None:
            result["record_effective_from"] = self.record_effective_from
        if self.record_effective_to is not None:
            result["record_effective_to"] = self.record_effective_to

        # Add chain tracking fields if present
        if self.chain_depth > 0:
            result["chain_depth"] = self.chain_depth
        if self.is_ultimate:
            result["is_ultimate"] = self.is_ultimate
        if self.direct_ownership_pct > 0:
            result["direct_ownership_pct"] = self.direct_ownership_pct
        if self.indirect_ownership_pct > 0:
            result["indirect_ownership_pct"] = self.indirect_ownership_pct
        if self.ownership_path:
            result["ownership_path"] = self.ownership_path

        return result


@dataclass
class TaxDebts:
    """Tax debt information."""
    has_debts: bool = False
    amount_eur: float = 0.0
    details: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {"has_debts": self.has_debts, "amount_eur": self.amount_eur}
        if self.details is not None:
            result["details"] = self.details
        return result


@dataclass
class TaxInfo:
    """Unified tax information structure."""
    vat_id: Optional[str] = None
    vat_status: Optional[str] = None  # active, inactive
    tax_id: Optional[str] = None
    tax_debts: Optional[TaxDebts] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {}
        if self.vat_id is not None:
            result["vat_id"] = self.vat_id
        if self.vat_status is not None:
            result["vat_status"] = self.vat_status
        if self.tax_id is not None:
            result["tax_id"] = self.tax_id
        if self.tax_debts is not None:
            result["tax_debts"] = self.tax_debts.to_dict()
        return result


@dataclass
class Metadata:
    """Unified metadata structure."""
    source: str
    register_name: str
    register_url: Optional[str] = None
    retrieved_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    snapshot_reference: Optional[str] = None
    parent_entity_ico: Optional[str] = None
    level: int = 0
    is_mock: bool = False

    # Recursive ownership fields
    ownership_depth: int = 0
    ultimate_beneficial_owners: List[Dict[str, Any]] = field(default_factory=list)
    indirect_beneficial_owners: List[Dict[str, Any]] = field(default_factory=list)
    ownership_tree: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "source": self.source,
            "register_name": self.register_name,
            "retrieved_at": self.retrieved_at,
            "level": self.level,
            "is_mock": self.is_mock,
        }
        if self.register_url is not None:
            result["register_url"] = self.register_url
        if self.snapshot_reference is not None:
            result["snapshot_reference"] = self.snapshot_reference
        if self.parent_entity_ico is not None:
            result["parent_entity_ico"] = self.parent_entity_ico
        if self.ownership_depth > 0:
            result["ownership_depth"] = self.ownership_depth
        if self.ultimate_beneficial_owners:
            result["ultimate_beneficial_owners"] = self.ultimate_beneficial_owners
        if self.indirect_beneficial_owners:
            result["indirect_beneficial_owners"] = self.indirect_beneficial_owners
        if self.ownership_tree is not None:
            result["ownership_tree"] = self.ownership_tree
        return result


@dataclass
class UnifiedOutput:
    """Complete unified output structure."""
    entity: Entity = field(default_factory=lambda: Entity(ico_registry="", company_name_registry=""))
    holders: List[Holder] = field(default_factory=list)
    tax_info: Optional[TaxInfo] = None
    metadata: Metadata = field(default_factory=Metadata)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "entity": self.entity.to_dict(),
            "holders": [h.to_dict() for h in self.holders],
        }
        if self.tax_info is not None:
            result["tax_info"] = self.tax_info.to_dict()
        result["metadata"] = self.metadata.to_dict()
        return result

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


# Helper functions

def normalize_country_code(country: Optional[str]) -> Optional[str]:
    """Normalize country name/code to ISO 3166-1 alpha-2 format.

    Args:
        country: Country name or code

    Returns:
        ISO 3166-1 alpha-2 country code or None
    """
    if not country:
        return None

    country_lower = country.lower().strip()

    # Already a valid 2-letter code
    if len(country_lower) == 2 and country_lower.isalpha():
        return country_lower.upper()

    return COUNTRY_CODE_MAPPINGS.get(country_lower)


def normalize_status(status: Optional[str]) -> Optional[str]:
    """Normalize status value to standard format.

    Args:
        status: Status value from source

    Returns:
        Normalized status value or None
    """
    if not status:
        return None

    status_lower = status.lower().strip()
    return STATUS_NORMALIZATIONS.get(status_lower, status_lower)


def normalize_role(role: Optional[str]) -> str:
    """Normalize role value to standard format.

    Args:
        role: Role value from source

    Returns:
        Normalized role value
    """
    if not role:
        return "unknown"

    role_lower = role.lower().strip()
    return ROLE_MAPPINGS.get(role_lower, role_lower)


def detect_holder_type(holder_data: Dict[str, Any]) -> str:
    """Detect holder type from holder data.

    Args:
        holder_data: Raw holder data

    Returns:
        Holder type: individual, entity, or trust_fund
    """
    # Check explicit type field
    holder_type = holder_data.get("type") or holder_data.get("holder_type")
    if holder_type:
        holder_type_lower = holder_type.lower()
        if "fyzic" in holder_type_lower or "individual" in holder_type_lower or "natural" in holder_type_lower:
            return "individual"
        if "pravnic" in holder_type_lower or "entity" in holder_type_lower or "corporate" in holder_type_lower:
            return "entity"
        if "trust" in holder_type_lower or "fund" in holder_type_lower:
            return "trust_fund"

    # Check for birth date (indicates individual)
    if holder_data.get("birth_date") or holder_data.get("date_of_birth"):
        return "individual"

    # Check identification object
    identification = holder_data.get("identification", {})
    if identification.get("birth_date") or identification.get("date_of_birth"):
        return "individual"

    # Check citizenship (usually indicates individual)
    if identification.get("citizenship") and not holder_data.get("ico"):
        # But if there's an IČO and no birth date, it's likely an entity
        pass

    # Check for company indicators in name
    name = holder_data.get("name", "")
    company_indicators = ["a.s.", "s.r.o.", "ag", "gmbh", "inc.", "corp.", "ltd.", "spol.", "akciová", "spoločnosť"]
    if any(indicator in name.lower() for indicator in company_indicators):
        return "entity"

    # Check if there's an IČO for the holder (indicates entity)
    if holder_data.get("ico") or holder_data.get("ico_registry"):
        return "entity"

    # Default to individual if birth date present, entity otherwise
    if holder_data.get("birth_date") or identification.get("birth_date"):
        return "individual"

    # If there's ownership percentage but no strong indicators, default to entity for company names
    if len(name.split()) > 2 and not any(c.isdigit() for c in name):
        return "entity"

    return "individual"


def parse_address(address_data: Optional[Dict[str, Any]]) -> Optional[Address]:
    """Parse address data into standardized Address object.

    Args:
        address_data: Raw address data

    Returns:
        Address object or None
    """
    if not address_data:
        return None

    # Handle string address
    if isinstance(address_data, str):
        return Address(full_address=address_data)

    # Extract country code
    country = address_data.get("country")
    country_code = address_data.get("country_code") or normalize_country_code(country)

    return Address(
        street=address_data.get("street") or address_data.get("nazevUlice"),
        city=address_data.get("city") or address_data.get("nazevObce"),
        postal_code=address_data.get("postal_code") or address_data.get("psc"),
        country=country,
        country_code=country_code,
        full_address=address_data.get("full_address"),
    )


def get_register_name(source: str) -> str:
    """Get human-readable register name for source.

    Args:
        source: Source identifier

    Returns:
        Register name
    """
    return REGISTER_NAMES.get(source, source)


def get_retrieved_at() -> str:
    """Get current timestamp in ISO format.

    Returns:
        ISO formatted timestamp string
    """
    return datetime.utcnow().isoformat() + "Z"
