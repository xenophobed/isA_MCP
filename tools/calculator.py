"""
Simple calculator tools for testing auto-discovery and registration.
"""

async def add(a: float, b: float) -> float:
    """
    Add two numbers together.
    
    Args:
        a: First number
        b: Second number
        
    Returns:
        The sum of a and b
    """
    return a + b

async def subtract(a: float, b: float) -> float:
    """
    Subtract second number from first.
    
    Args:
        a: First number
        b: Second number
        
    Returns:
        The difference (a - b)
    """
    return a - b

async def multiply(a: float, b: float) -> float:
    """
    Multiply two numbers.
    
    Args:
        a: First number
        b: Second number
        
    Returns:
        The product of a and b
    """
    return a * b

# This function should not be registered as a tool
def _internal_helper() -> None:
    """This is an internal function and should not be registered."""
    pass 