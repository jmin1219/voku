"""Registry router - manage variable registry for name normalization."""
from pathlib import Path

from app.services.registry import VariableRegistry
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

router = APIRouter()

# Registry path (same as used in main.py)
REGISTRY_PATH = Path(__file__).parent.parent.parent / "data" / "registry" / "variables.json"


def get_registry() -> VariableRegistry:
    """Get registry instance."""
    return VariableRegistry(path=REGISTRY_PATH)


# Request/Response Models
class VariableCreate(BaseModel):
    """Request model for creating a new variable."""
    canonical: str = Field(..., min_length=1, max_length=100)
    display: str = Field(..., min_length=1, max_length=200)
    unit: str = Field(..., min_length=1, max_length=50)
    aliases: list[str] = Field(default_factory=list)
    
    @field_validator('canonical')
    @classmethod
    def canonical_must_be_lowercase_underscore(cls, v):
        """Validate canonical name format."""
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('canonical must contain only lowercase letters, numbers, underscores, and hyphens')
        if v != v.lower():
            raise ValueError('canonical must be lowercase')
        return v
    
    @field_validator('aliases')
    @classmethod
    def aliases_must_be_unique(cls, v):
        """Validate aliases are unique."""
        if len(v) != len(set(v)):
            raise ValueError('aliases must be unique')
        return v


class AliasCreate(BaseModel):
    """Request model for adding an alias."""
    alias: str = Field(..., min_length=1, max_length=200)


class VariableResponse(BaseModel):
    """Response model for a variable."""
    canonical: str
    display: str
    unit: str
    aliases: list[str]
    count: int


class RegistryResponse(BaseModel):
    """Response model for full registry."""
    variables: dict[str, dict]
    count: int


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str
    canonical: str | None = None


# Endpoints
@router.get("/variables", response_model=RegistryResponse)
def list_variables():
    """
    List all known variables in the registry.
    
    Returns:
        Dictionary of all variables with their metadata
    """
    registry = get_registry()
    return {
        "variables": registry.variables,
        "count": len(registry.variables)
    }


@router.get("/variables/{canonical}", response_model=VariableResponse)
def get_variable(canonical: str):
    """
    Get a specific variable by canonical name.
    
    Args:
        canonical: Canonical name of the variable
        
    Returns:
        Variable metadata
        
    Raises:
        404: Variable not found
    """
    registry = get_registry()
    
    if canonical not in registry.variables:
        raise HTTPException(status_code=404, detail=f"Variable '{canonical}' not found")
    
    var_data = registry.variables[canonical]
    return VariableResponse(
        canonical=canonical,
        display=var_data["display"],
        unit=var_data["unit"],
        aliases=var_data.get("aliases", []),
        count=var_data.get("count", 0)
    )


@router.post("/variables", response_model=MessageResponse, status_code=201)
def create_variable(variable: VariableCreate):
    """
    Add a new canonical variable to the registry.
    
    Args:
        variable: Variable data (canonical, display, unit, aliases)
        
    Returns:
        Success message
        
    Raises:
        400: Variable already exists or invalid data
    """
    registry = get_registry()
    
    # Check if canonical name already exists
    if variable.canonical in registry.variables:
        raise HTTPException(
            status_code=400, 
            detail=f"Variable '{variable.canonical}' already exists"
        )
    
    # Check if any alias conflicts with existing canonical names or aliases
    for alias in variable.aliases:
        existing_canonical = registry.get_canonical(alias)
        if existing_canonical:
            raise HTTPException(
                status_code=400,
                detail=f"Alias '{alias}' conflicts with existing variable '{existing_canonical}'"
            )
    
    # Add variable
    registry.add_variable(
        canonical=variable.canonical,
        display=variable.display,
        unit=variable.unit,
        aliases=variable.aliases
    )
    registry.save()
    
    return MessageResponse(
        message=f"Variable '{variable.canonical}' created successfully",
        canonical=variable.canonical
    )


@router.post("/variables/{canonical}/aliases", response_model=MessageResponse)
def add_alias(canonical: str, alias_data: AliasCreate):
    """
    Add an alias to an existing variable.
    
    Args:
        canonical: Canonical name of the variable
        alias_data: Alias to add
        
    Returns:
        Success message
        
    Raises:
        404: Variable not found
        400: Alias already exists
    """
    registry = get_registry()
    
    # Check if canonical exists
    if canonical not in registry.variables:
        raise HTTPException(
            status_code=404,
            detail=f"Variable '{canonical}' not found"
        )
    
    # Check if alias already exists
    existing_canonical = registry.get_canonical(alias_data.alias)
    if existing_canonical:
        if existing_canonical == canonical:
            raise HTTPException(
                status_code=400,
                detail=f"Alias '{alias_data.alias}' already mapped to '{canonical}'"
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Alias '{alias_data.alias}' already mapped to '{existing_canonical}'"
            )
    
    # Add alias
    registry.add_alias(canonical, alias_data.alias)
    registry.save()
    
    return MessageResponse(
        message=f"Alias '{alias_data.alias}' added to '{canonical}'",
        canonical=canonical
    )


@router.delete("/variables/{canonical}", response_model=MessageResponse)
def delete_variable(canonical: str):
    """
    Delete a variable from the registry.
    
    Args:
        canonical: Canonical name of the variable to delete
        
    Returns:
        Success message
        
    Raises:
        404: Variable not found
    """
    registry = get_registry()
    
    if canonical not in registry.variables:
        raise HTTPException(
            status_code=404,
            detail=f"Variable '{canonical}' not found"
        )
    
    del registry.variables[canonical]
    registry.save()
    
    return MessageResponse(
        message=f"Variable '{canonical}' deleted successfully",
        canonical=canonical
    )
