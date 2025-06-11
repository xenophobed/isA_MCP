import os 
os.environ["ENV"] = "local"

from app.services.ai.tools.tools_manager import tools_manager
from app.services.ai.tools.math.python_repl_tools import execute_python_code
from langchain_core.messages import AIMessage
from app.services.ai.llm.llm_factory import LLMFactory
from app.config.config_manager import config_manager
import logging
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

async def setup_tools_manager():
    """Initialize tools manager with graph support"""
    try:
        await tools_manager.initialize(test_mode=True)
        logger.info("Tools manager initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize tools manager: {str(e)}")
        raise

async def test_direct_code_execution():
    """Test direct code execution"""
    print("\n=== Testing Direct Code Execution ===")
    
    # Test simple calculation
    print("\nTesting simple calculation:")
    calc_code = """
x = 10
y = 20
result = x + y
print(f'Sum: {result}')
"""
    tool = tools_manager.get_tool("execute_python_code")
    result = tool.invoke(calc_code)
    print(f"Simple calculation result: {result}")
    
    # Test list comprehension
    print("\nTesting list comprehension:")
    list_code = """
numbers = [1, 2, 3, 4, 5]
squares = [x**2 for x in numbers]
print(f'Squares: {squares}')
"""
    result = tool.invoke(list_code)
    print(f"List comprehension result: {result}")

async def test_tool_node():
    """Test tool through ToolNode"""
    print("\n=== Testing Tool Node ===")
    
    # Create message with tool call
    message_with_tool_call = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "execute_python_code",
                "args": {"code_description": "print('Hello from tool node!')"},
                "id": "tool_call_id",
                "type": "tool_call",
            }
        ],
    )
    
    # Create tool node
    tool_node = tools_manager.create_tool_node()
    
    # Invoke tool
    print("\nTesting tool node with code execution:")
    result = tool_node.invoke({"messages": [message_with_tool_call]})
    print(f"Tool node result: {result}")

async def test_error_handling():
    """Test error handling"""
    print("\n=== Testing Error Handling ===")
    
    # Test syntax error
    print("\nTesting syntax error:")
    invalid_code = """
x = 10
if x > 5
    print('Invalid syntax')
"""
    tool = tools_manager.get_tool("execute_python_code")
    result = tool.invoke(invalid_code)
    print(f"Syntax error result: {result}")
    
    # Test runtime error
    print("\nTesting runtime error:")
    runtime_error_code = """
x = 10 / 0  # Division by zero
"""
    result = tool.invoke(runtime_error_code)
    print(f"Runtime error result: {result}")

async def test_tool_node_with_model():
    """Test tool node with model"""
    print("\n=== Testing Tool Node with Model ===")
    
    # Create agent with tool
    from app.services.ai.agent.agent_builder import AgentBuilder
    
    builder = AgentBuilder()
    await builder.initialize()
    app, state = await builder.create_base_agent(tools=["execute_python_code"])
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def run_model_test(messages):
        state["messages"] = messages
        return app.invoke(state)
    
    # Test with IMO-style number theory problem
    print("\nTesting IMO-style number theory problem:")
    messages = [{
        "role": "user",
        "content": """Write a Python code that solves this IMO-style problem:
        Find all positive integers n such that n^2 + 2n + 2 is prime.
        
        Steps:
        1. Define a function to check if a number is prime
        2. Implement a function to test the expression n^2 + 2n + 2
        3. Search for solutions up to n=100
        4. Print all found solutions and explain why these are all possible solutions
        
        Note: Use efficient primality testing and explain the mathematical reasoning."""
    }]
    try:
        result = await run_model_test(messages)
        print(f"Number theory problem result: {result}")
    except Exception as e:
        print(f"Number theory problem failed: {str(e)}")
    
    # Test with combinatorics problem
    print("\nTesting combinatorics problem:")
    messages = [{
        "role": "user",
        "content": """Write a Python code that solves this combinatorics problem:
        In how many ways can you place 8 rooks on a 8×8 chessboard so that no two rooks attack each other?
        
        Steps:
        1. Implement a function to generate permutations
        2. Calculate the total number of valid rook placements
        3. Print the result and verify it equals 40320 (8!)
        4. Optionally, visualize one valid solution
        
        Note: Use Python's itertools for efficiency and explain the mathematical principle."""
    }]
    try:
        result = await run_model_test(messages)
        print(f"Combinatorics problem result: {result}")
    except Exception as e:
        print(f"Combinatorics problem failed: {str(e)}")
    
    # Test with geometry problem
    print("\nTesting geometry problem:")
    messages = [{
        "role": "user",
        "content": """Write a Python code that solves this geometry problem:
        Given a triangle with sides a=3, b=4, c=5, calculate:
        1. The area using Heron's formula
        2. The radius of the inscribed circle
        3. The radius of the circumscribed circle
        4. The angles in degrees
        5. The coordinates of the orthocenter
        
        Steps:
        1. Implement Heron's formula
        2. Calculate all the required measurements
        3. Use math.acos() for angle calculations
        4. Print results with proper formatting
        
        Note: Use math module and round results to 4 decimal places."""
    }]
    try:
        result = await run_model_test(messages)
        print(f"Geometry problem result: {result}")
    except Exception as e:
        print(f"Geometry problem failed: {str(e)}")
    
    # Test with calculus problem
    print("\nTesting calculus problem:")
    messages = [{
        "role": "user",
        "content": """Write a Python code that implements numerical methods to:
        1. Find all real roots of the equation: x^3 - 6x^2 + 11x - 6 = 0
        2. Calculate the area under the curve y = sin(x) from 0 to π using:
           a) Rectangle method
           b) Trapezoidal method
           c) Simpson's rule
        3. Compare the results with the actual value (2)
        
        Steps:
        1. Implement Newton's method for root finding
        2. Implement all three numerical integration methods
        3. Calculate and compare errors
        4. Plot the function and highlight the roots
        
        Note: Use numpy for calculations and matplotlib for visualization."""
    }]
    try:
        result = await run_model_test(messages)
        print(f"Calculus problem result: {result}")
    except Exception as e:
        print(f"Calculus problem failed: {str(e)}")

async def test_tool_registry_health():
    """Test tool registry health checks"""
    status = await tools_manager.get_registry_status()
    assert status["health_status"] == "healthy"
    assert "execute_python_code" in status["registered_tools"]
    
    # Verify tool integrity
    issues = await tools_manager.verify_tools_integrity()
    assert len(issues) == 0
    
    # Test tool existence
    code_tool = tools_manager.get_tool("execute_python_code")
    assert code_tool is not None, "Python REPL tool not found"
    assert code_tool.name in status["registered_tools"]

async def run_tests():
    """Run all tests"""
    try:
        await setup_tools_manager()
        
        # Run tests
        await test_direct_code_execution()
        await test_tool_node()
        await test_error_handling()
        await test_tool_node_with_model()
        await test_tool_registry_health()
        
    except Exception as e:
        logger.error(f"Test suite failed: {str(e)}")
        raise
    finally:
        await tools_manager.cleanup()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_tests())
