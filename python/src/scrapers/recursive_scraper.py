"""
Recursive Scraper - Ownership Chain Traversal

This scraper traces ownership chains through parent companies
to identify ultimate beneficial owners (UBO) and indirect beneficial owners (IBO).
"""

from typing import Optional, Dict, Any, List, Set
from dataclasses import dataclass, field
from collections import deque, defaultdict

from src.scrapers.rpvs_slovak import RpvsSlovakScraper
from src.scrapers.esm_czech import EsmCzechScraper
from src.scrapers.ares_czech import ARESCzechScraper
from src.scrapers.rpo_slovak import RpoSlovakScraper
from src.utils.logger import get_logger
from src.utils.field_mapper import get_retrieved_at
from src.utils.output_normalizer import (
    UnifiedOutput, Entity, Holder, Metadata,
    detect_holder_type, parse_address, normalize_country_code,
    get_register_name
)


@dataclass
class OwnershipNode:
    """Represents a node in the ownership tree."""
    ico: str
    name: str
    country: str
    ownership_percentage: float = 0.0
    is_individual: bool = False
    children: List['OwnershipNode'] = field(default_factory=list)
    source: str = ""
    depth: int = 0
    parent: Optional['OwnershipNode'] = None
    # For tracking the path from root
    path_from_root: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary."""
        return {
            "ico": self.ico,
            "name": self.name,
            "country": self.country,
            "ownership_percentage": self.ownership_percentage,
            "is_individual": self.is_individual,
            "children": [c.to_dict() for c in self.children],
            "source": self.source,
            "depth": self.depth,
            "path_from_root": self.path_from_root
        }

    def get_path_to_root(self) -> List[str]:
        """Get the ownership chain from root to this node."""
        if not self.parent:
            return [self.name]
        path = self.parent.get_path_to_root()
        path.append(self.name)
        return path


class RecursiveScraper:
    """Scraper for traversing ownership chains recursively.

    Traces parent company ownership to identify ultimate beneficial owners.

    Example:
        scraper = RecursiveScraper(max_depth=5)
        tree = scraper.build_ownership_tree("06649114")

        # Print tree structure
        scraper.print_tree(tree)

        # Get ultimate beneficial owners
        ubos = scraper.extract_ultimate_owners(tree)
    """

    # Ownership threshold for following chains
    OWNERSHIP_THRESHOLD = 25.0

    def __init__(
        self,
        max_depth: int = 5,
        follow_cross_border: bool = True,
        enable_snapshots: bool = False
    ):
        """Initialize recursive scraper.

        Args:
            max_depth: Maximum recursion depth
            follow_cross_border: Whether to follow cross-border ownership
            enable_snapshots: Enable snapshot saving
        """
        self.max_depth = max_depth
        self.follow_cross_border = follow_cross_border
        self.enable_snapshots = enable_snapshots

        self.logger = get_logger(self.__class__.__name__)

        # Initialize scrapers
        self.rpvs_scraper = RpvsSlovakScraper(enable_snapshots=enable_snapshots)
        self.esm_scraper = EsmCzechScraper(enable_snapshots=enable_snapshots)
        self.ares_scraper = ARESCzechScraper(enable_snapshots=enable_snapshots)
        self.rpo_scraper = RpoSlovakScraper(enable_snapshots=enable_snapshots)

        # Track visited ICOs to prevent infinite loops
        self._visited = set()

    def build_ownership_tree(self, ico: str, country: str = "auto") -> Optional[OwnershipNode]:
        """Build complete ownership tree for a company.

        Args:
            ico: Company identification number
            country: Country code (CZ, SK) or "auto" for detection

        Returns:
            Root node of ownership tree
        """
        self._visited = set()
        root = self._build_tree_recursive(ico, country, 0, 100.0)
        if root:
            root.path_from_root = [root.name]
            self._update_paths(root)
        return root

    def _build_tree_recursive(
        self,
        ico: str,
        country: str,
        depth: int,
        accumulated_ownership: float,
        parent: Optional[OwnershipNode] = None
    ) -> Optional[OwnershipNode]:
        """Recursively build ownership tree.

        Args:
            ico: Company identification number
            country: Country code
            depth: Current recursion depth
            accumulated_ownership: Ownership percentage from parent
            parent: Parent node for tracking path

        Returns:
            Ownership node or None
        """
        # Prevent infinite loops (cycle detection)
        if ico in self._visited:
            self.logger.debug(f"Cycle detected: already visited {ico}, skipping")
            return None

        # Check depth limit
        if depth > self.max_depth:
            self.logger.debug(f"Max depth ({self.max_depth}) reached for {ico}")
            return None

        self._visited.add(ico)

        # Auto-detect country
        if country == "auto":
            country = self._detect_country(ico)

        # Get UBO data based on country
        ubo_data = self._get_ubo_data(ico, country)

        if not ubo_data:
            # Create basic node if no UBO data
            company_data = self._get_company_data(ico, country)
            if company_data:
                node = OwnershipNode(
                    ico=ico,
                    name=company_data.get("entity", {}).get("company_name_registry") or company_data.get("name", "Unknown"),
                    country=country,
                    ownership_percentage=accumulated_ownership,
                    is_individual=False,
                    source=company_data.get("metadata", {}).get("source", "UNKNOWN"),
                    depth=depth,
                    parent=parent
                )
                if parent:
                    node.path_from_root = parent.path_from_root + [node.name]
                return node
            return None

        # Create root node
        entity = ubo_data.get("entity", {})
        root = OwnershipNode(
            ico=ico,
            name=entity.get("company_name_registry") or ubo_data.get("company_name", "Unknown"),
            country=country,
            ownership_percentage=accumulated_ownership,
            is_individual=False,
            source=ubo_data.get("metadata", {}).get("source", "UNKNOWN"),
            depth=depth,
            parent=parent
        )

        if parent:
            root.path_from_root = parent.path_from_root + [root.name]
        else:
            root.path_from_root = [root.name]

        # Process beneficial owners
        holders = ubo_data.get("holders", [])
        ubos = [h for h in holders if h.get("role") in ["beneficial_owner", "ultimate_beneficial_owner", "ubo"]]

        if not ubos:
            # Try legacy format
            ubos = ubo_data.get("ubos") or ubo_data.get("beneficial_owners") or []

        for ubo in ubos:
            owner_ico = ubo.get("ico")
            owner_name = ubo.get("name", "Unknown")
            ownership_pct = ubo.get("ownership_pct_direct") or ubo.get("ownership_percentage", 0.0)

            # Check if individual or corporate
            is_individual = self._is_individual_owner(ubo)

            if is_individual:
                # Individual owner - add as leaf node
                citizenship = ubo.get("citizenship")
                child = OwnershipNode(
                    ico=owner_ico or "",
                    name=owner_name,
                    country=citizenship or "Unknown",
                    ownership_percentage=ownership_pct * accumulated_ownership / 100,
                    is_individual=True,
                    source=ubo_data.get("metadata", {}).get("source", "UNKNOWN"),
                    depth=depth + 1,
                    parent=root
                )
                child.path_from_root = root.path_from_root + [child.name]
                root.children.append(child)

            elif owner_ico and ownership_pct >= self.OWNERSHIP_THRESHOLD:
                # Corporate owner - recurse
                owner_country = self._detect_country(owner_ico)

                # Check cross-border setting
                if not self.follow_cross_border and owner_country != country:
                    self.logger.debug(f"Skipping cross-border {owner_ico} ({owner_country} from {country})")
                    continue

                child = self._build_tree_recursive(
                    owner_ico,
                    owner_country,
                    depth + 1,
                    ownership_pct * accumulated_ownership / 100,
                    parent=root
                )

                if child:
                    root.children.append(child)

        return root

    def _update_paths(self, node: OwnershipNode) -> None:
        """Update paths for all nodes in tree."""
        for child in node.children:
            child.path_from_root = node.path_from_root + [child.name]
            self._update_paths(child)

    def _detect_country(self, ico: str) -> str:
        """Detect country from ICO format.

        Args:
            ico: Company identification number

        Returns:
            Country code (CZ or SK)
        """
        if not ico:
            return "CZ"

        # Czech ICOs are typically 8 digits
        # Slovak ICOs are also 8 digits but may start differently
        ico_clean = ico.replace(" ", "").strip()

        if len(ico_clean) == 8:
            # Both countries use 8-digit format
            # Try to determine from leading digits
            if ico_clean.startswith("0"):
                return "CZ"
            return "SK"

        return "CZ"

    def _get_ubo_data(self, ico: str, country: str) -> Optional[Dict[str, Any]]:
        """Get UBO data for a company.

        Args:
            ico: Company identification number
            country: Country code

        Returns:
            UBO data dictionary or None
        """
        try:
            if country == "CZ":
                return self.esm_scraper.search_by_id(ico)
            else:
                return self.rpvs_scraper.search_by_id(ico)
        except Exception as e:
            self.logger.debug(f"Error getting UBO data for {ico}: {e}")
            return None

    def _get_company_data(self, ico: str, country: str) -> Optional[Dict[str, Any]]:
        """Get basic company data.

        Args:
            ico: Company identification number
            country: Country code

        Returns:
            Company data dictionary or None
        """
        try:
            if country == "CZ":
                return self.ares_scraper.search_by_id(ico)
            else:
                return self.rpo_scraper.search_by_id(ico)
        except Exception as e:
            self.logger.debug(f"Error getting company data for {ico}: {e}")
            return None

    def _is_individual_owner(self, ubo: Dict[str, Any]) -> bool:
        """Check if an owner is an individual.

        Args:
            ubo: Owner data

        Returns:
            True if individual, False if corporate
        """
        # Check for birth date (individual indicator)
        if ubo.get("birth_date") or ubo.get("identification", {}).get("birth_date"):
            return True

        # Check role
        role = ubo.get("role", "").lower()
        if "individual" in role or "fyzick" in role or "natural" in role:
            return True

        # Check for corporate indicators
        if ubo.get("ico") and len(ubo.get("ico", "")) == 8:
            # Has ICO - likely corporate
            return False

        return True  # Default to individual

    def extract_ultimate_owners(self, root: OwnershipNode) -> List[Dict[str, Any]]:
        """Extract all ultimate beneficial owners from tree.

        Args:
            root: Root of ownership tree

        Returns:
            List of ultimate owner dictionaries
        """
        ubos = []

        def traverse(node: OwnershipNode, parent_ownership: float):
            if node.is_individual:
                ubos.append({
                    "name": node.name,
                    "ico": node.ico,
                    "country": node.country,
                    "ownership_percentage": node.ownership_percentage,
                    "total_ownership": parent_ownership * node.ownership_percentage / 100,
                    "source": node.source
                })
            else:
                for child in node.children:
                    traverse(child, parent_ownership)

        if root:
            traverse(root, 100.0)

        return ubos

    def print_tree(self, root: OwnershipNode, indent: int = 0) -> None:
        """Print ownership tree to console.

        Args:
            root: Root of ownership tree
            indent: Current indentation level
        """
        if not root:
            print("Empty tree")
            return

        prefix = "  " * indent
        tree_char = "└── " if indent > 0 else ""

        owner_type = "[Individual]" if root.is_individual else "[Company]"
        print(f"{prefix}{tree_char}{root.name} ({root.country}) - {root.ownership_percentage:.1f}% {owner_type}")

        for child in root.children:
            self.print_tree(child, indent + 1)

    def get_ownership_summary(self, root: OwnershipNode) -> Dict[str, Any]:
        """Get summary statistics for ownership tree.

        Args:
            root: Root of ownership tree

        Returns:
            Summary dictionary
        """
        ubos = self.extract_ultimate_owners(root)

        total_ownership = sum(u["total_ownership"] for u in ubos)

        return {
            "root_ico": root.ico if root else None,
            "root_name": root.name if root else None,
            "total_ultimate_owners": len(ubos),
            "total_ownership_traced": total_ownership,
            "untraced_ownership": 100.0 - total_ownership,
            "individual_owners": len([u for u in ubos if u["ico"] == "" or u["ico"] is None]),
            "corporate_owners": len([u for u in ubos if u["ico"]]),
            "retrieved_at": get_retrieved_at()
        }

    # ========== NEW: Unified Output Methods ==========

    def to_unified_output(self, root: OwnershipNode, original_ico: str, original_country: str) -> Optional[Dict[str, Any]]:
        """Convert ownership tree to unified output format.

        Args:
            root: Root of ownership tree
            original_ico: Original company ICO
            original_country: Original company country

        Returns:
            Unified output dictionary with recursive ownership info
        """
        if not root:
            return None

        # Get basic company data for the entity
        company_data = self._get_company_data(original_ico, original_country)
        if not company_data:
            return None

        entity = company_data.get("entity", {})

        # Convert tree to holders with chain info
        holders = self._convert_tree_to_holders(root)

        # Calculate UBOs and IBOs
        ubos = self._extract_ultimate_owners_detailed(root)
        ibos = self.calculate_indirect_owners(root)

        # Build extended metadata
        metadata = Metadata(
            source="RECURSIVE",
            register_name="Recursive Ownership Search",
            retrieved_at=get_retrieved_at(),
            is_mock=company_data.get("metadata", {}).get("is_mock", False),
            ownership_depth=self.max_depth
        )

        # Add recursive ownership info
        metadata_dict = metadata.to_dict()
        metadata_dict["ultimate_beneficial_owners"] = ubos
        metadata_dict["indirect_beneficial_owners"] = ibos
        metadata_dict["ownership_tree"] = self._tree_to_dict(root)

        # Build unified output dictionary directly
        return {
            "entity": {
                "ico_registry": entity.get("ico_registry", original_ico),
                "company_name_registry": entity.get("company_name_registry", root.name),
                "legal_form": entity.get("legal_form"),
                "status": entity.get("status"),
            },
            "holders": [h.to_dict() for h in holders],
            "tax_info": company_data.get("tax_info"),
            "metadata": metadata_dict
        }

    def _convert_tree_to_holders(self, root: OwnershipNode) -> List[Holder]:
        """Convert ownership tree to list of holders with chain info.

        Args:
            root: Root of ownership tree

        Returns:
            List of Holder objects with chain tracking
        """
        holders = []

        def traverse(node: OwnershipNode, is_indirect: bool = False):
            if node.is_individual or not node.children:
                # This is a leaf (either individual or corporate with no owners)
                holder = Holder(
                    holder_type="individual" if node.is_individual else "entity",
                    role="beneficial_owner",
                    name=node.name,
                    ico=node.ico if node.ico else None,
                    jurisdiction=node.country if not node.is_individual else None,
                    citizenship=node.country if node.is_individual else None,
                    ownership_pct_direct=node.ownership_percentage,
                    chain_depth=node.depth,
                    is_ultimate=len(node.children) == 0,
                    ownership_path=node.path_from_root
                )
                holders.append(holder)
            else:
                # This is a corporate node with children - it's an intermediate
                for child in node.children:
                    traverse(child, is_indirect=True)

        if root:
            for child in root.children:
                traverse(child)

        return holders

    def _extract_ultimate_owners_detailed(self, root: OwnershipNode) -> List[Dict[str, Any]]:
        """Extract detailed ultimate beneficial owner information.

        Args:
            root: Root of ownership tree

        Returns:
            List of detailed UBO dictionaries
        """
        ubos = []
        seen_owners: Set[str] = set()

        def traverse(node: OwnershipNode, accumulated_pct: float):
            if node.is_individual or not node.children:
                # This is a leaf node - could be UBO
                owner_key = f"{node.name}_{node.country}"
                if owner_key not in seen_owners:
                    ubos.append({
                        "name": node.name,
                        "ico": node.ico if node.ico else None,
                        "country": node.country,
                        "ownership_percentage": round(node.ownership_percentage, 2),
                        "is_individual": node.is_individual,
                        "path": " -> ".join(node.path_from_root),
                        "source": node.source
                    })
                    seen_owners.add(owner_key)
            else:
                for child in node.children:
                    traverse(child, accumulated_pct)

        if root:
            traverse(root, 100.0)

        # Sort by ownership percentage descending
        ubos.sort(key=lambda x: x["ownership_percentage"], reverse=True)
        return ubos

    def _tree_to_dict(self, root: OwnershipNode) -> Dict[str, Any]:
        """Convert ownership tree to dictionary format.

        Args:
            root: Root of ownership tree

        Returns:
            Dictionary representation of tree
        """
        if not root:
            return {}

        def node_to_dict(node: OwnershipNode) -> Dict[str, Any]:
            return {
                "ico": node.ico,
                "name": node.name,
                "country": node.country,
                "ownership_percentage": round(node.ownership_percentage, 2),
                "is_individual": node.is_individual,
                "depth": node.depth,
                "children": [node_to_dict(child) for child in node.children]
            }

        return node_to_dict(root)

    # ========== NEW: IBO Calculation ==========

    def calculate_indirect_owners(self, root: OwnershipNode) -> List[Dict[str, Any]]:
        """Calculate indirect beneficial owners.

        IBO = Individual who owns indirectly through corporate chains.
        Ownership is calculated by multiplying percentages along the chain.

        Example:
            Company A owns 50% of Company B
            Person X owns 100% of Company A
            Person X's indirect ownership of Company B = 50% * 100% = 50%

        Args:
            root: Root of ownership tree

        Returns:
            List of indirect beneficial owner dictionaries
        """
        indirect_owners = []
        seen_owners: Set[str] = set()

        def traverse(node: OwnershipNode, accumulated_pct: float, has_corporate_ancestor: bool):
            if node.is_individual and has_corporate_ancestor:
                # This is an individual with corporate ancestors - IBO candidate
                owner_key = f"{node.name}_{node.country}"
                if owner_key not in seen_owners:
                    indirect_owners.append({
                        "name": node.name,
                        "ico": node.ico if node.ico else None,
                        "country": node.country,
                        "indirect_ownership_pct": round(accumulated_pct, 2),
                        "path": " -> ".join(node.path_from_root),
                        "depth": node.depth,
                        "source": node.source
                    })
                    seen_owners.add(owner_key)
            else:
                # Continue traversal
                for child in node.children:
                    child_pct = accumulated_pct * child.ownership_percentage / 100
                    child_has_corp = has_corporate_ancestor or (not node.is_individual and node.depth > 0)
                    traverse(child, child_pct, child_has_corp)

        if root:
            for child in root.children:
                child_pct = child.ownership_percentage
                has_corp = not child.is_individual
                traverse(child, child_pct, has_corp)

        # Sort by indirect ownership percentage descending
        indirect_owners.sort(key=lambda x: x["indirect_ownership_pct"], reverse=True)
        return indirect_owners

    # ========== NEW: Helper Methods ==========

    def get_ownership_path(self, root: OwnershipNode, target_ico: str) -> List[str]:
        """Get the ownership chain from root to a target ICO.

        Args:
            root: Root of ownership tree
            target_ico: Target ICO to find path for

        Returns:
            List of names in the ownership chain, or empty list if not found
        """
        def find_path(node: OwnershipNode, target: str, current_path: List[str]) -> Optional[List[str]]:
            if node.ico == target:
                return current_path + [node.name]
            for child in node.children:
                result = find_path(child, target, current_path + [node.name])
                if result:
                    return result
            return None

        if root:
            return find_path(root, target_ico, []) or []
        return []

    def find_concentration_risk(self, root: OwnershipNode) -> Dict[str, Any]:
        """Check if there's concentration risk (>50% controlled by single entity).

        Args:
            root: Root of ownership tree

        Returns:
            Dictionary with concentration risk analysis
        """
        ubos = self.extract_ultimate_owners(root)

        # Find single owner with >50% control
        dominant_owner = None
        for ubo in ubos:
            if ubo["total_ownership"] > 50:
                dominant_owner = ubo
                break

        # Calculate total traced ownership
        total_traced = sum(u["total_ownership"] for u in ubos)

        return {
            "has_concentration_risk": dominant_owner is not None,
            "dominant_owner": dominant_owner["name"] if dominant_owner else None,
            "dominant_ownership_pct": round(dominant_owner["total_ownership"], 2) if dominant_owner else 0,
            "total_traced_ownership": round(total_traced, 2),
            "untraced_ownership": round(100 - total_traced, 2),
            "num_ultimate_owners": len(ubos)
        }

    def get_cross_border_exposure(self, root: OwnershipNode) -> List[Dict[str, Any]]:
        """Identify all cross-border ownership links.

        Args:
            root: Root of ownership tree

        Returns:
            List of cross-border ownership links
        """
        cross_border_links = []
        root_country = root.country if root else "Unknown"

        def traverse(node: OwnershipNode):
            if node.depth > 0 and node.country != root_country:
                # This is a cross-border link
                cross_border_links.append({
                    "from_country": root_country,
                    "to_country": node.country,
                    "entity_name": node.name,
                    "ico": node.ico,
                    "ownership_percentage": round(node.ownership_percentage, 2),
                    "depth": node.depth
                })
            for child in node.children:
                traverse(child)

        if root:
            traverse(root)

        return cross_border_links

    def get_ownership_depth_reached(self, root: OwnershipNode) -> int:
        """Get the maximum depth reached in the ownership tree.

        Args:
            root: Root of ownership tree

        Returns:
            Maximum depth level
        """
        if not root:
            return 0

        def max_depth(node: OwnershipNode) -> int:
            if not node.children:
                return node.depth
            return max(max_depth(child) for child in node.children)

        return max_depth(root)

    def get_entity_count(self, root: OwnershipNode) -> Dict[str, int]:
        """Get count of entities and individuals in the tree.

        Args:
            root: Root of ownership tree

        Returns:
            Dictionary with entity and individual counts
        """
        entities = 0
        individuals = 0

        def traverse(node: OwnershipNode):
            nonlocal entities, individuals
            if node.is_individual:
                individuals += 1
            else:
                entities += 1
            for child in node.children:
                traverse(child)

        if root:
            traverse(root)

        return {
            "total_entities": entities,
            "total_individuals": individuals,
            "total_nodes": entities + individuals
        }
