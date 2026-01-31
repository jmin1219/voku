"""Variable Registry - tracks known variable names and aliases.

Responsibilities:
  - Store canonical variable names
  - Map aliases to canonical names
  - Track observation counts

NOT responsible for (see Trainer agent, v0.2):
  - Deciding which variables matter
  - Comparing against training plans
  - Prioritizing variables
"""
import json
from pathlib import Path


class VariableRegistry:
    """
    Tracks known fitness variables and maps aliases to canonical names.
    
    Example:
        registry = VariableRegistry(path="data/registry/variables.json")
        canonical = registry.get_canonical("Avg HR")  # Returns "avg_heart_rate"
    """

    def __init__(self, path: str | Path):
        """
        Initialize registry, loading from disk if exists.
        
        Args:
            path: Path to registry JSON file
        """
        self.path = Path(path)
        self.variables: dict = {}
        self._load()

    def _load(self) -> None:
        """Load registry from disk if exists."""
        if self.path.exists():
            with open(self.path) as f:
                self.variables = json.load(f)

    def save(self) -> None:
        """Persist registry to disk."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(self.variables, f, indent=2)

    def _normalize(self, name: str) -> str:
        """Normalize name for comparison: lowercase, underscores for spaces."""
        return name.lower().replace(" ", "_")

    def get_canonical(self, name: str) -> str | None:
        """
        Find canonical name for a variable.
        
        Args:
            name: Variable name (may be alias or canonical)
            
        Returns:
            Canonical name if found, None if unknown
        """
        normalized = self._normalize(name)
        
        # Check direct match on canonical keys
        if normalized in self.variables:
            return normalized
        
        # Check aliases
        for canonical, data in self.variables.items():
            # Check canonical with normalization
            if self._normalize(canonical) == normalized:
                return canonical
            # Check each alias
            for alias in data.get("aliases", []):
                if self._normalize(alias) == normalized:
                    return canonical
        
        return None

    def add_variable(
        self,
        canonical: str,
        display: str,
        unit: str,
        aliases: list[str] = None,
        # Future params - accepted but not used yet (v0.2 trainer integration)
        source: str = "observed",
        priority: int = None,
    ) -> None:
        """
        Add a new variable to the registry.
        
        Args:
            canonical: Lowercase underscore key (e.g., "avg_heart_rate")
            display: Human-readable name (e.g., "Avg Heart Rate")
            unit: Default unit (e.g., "bpm")
            aliases: Alternative names that map to this variable
            source: Who added this ("observed" or "expected") - reserved for v0.2
            priority: Importance level - reserved for v0.2
        """
        self.variables[canonical] = {
            "display": display,
            "aliases": aliases or [],
            "unit": unit,
            "count": 1,
        }

    def add_alias(self, canonical: str, alias: str) -> None:
        """
        Add an alias to an existing variable.
        
        Args:
            canonical: Existing variable's canonical name
            alias: New alias to add
        """
        if canonical in self.variables:
            if alias not in self.variables[canonical]["aliases"]:
                self.variables[canonical]["aliases"].append(alias)

    def increment_count(self, canonical: str) -> None:
        """Increment observation count for a variable."""
        if canonical in self.variables:
            self.variables[canonical]["count"] += 1
