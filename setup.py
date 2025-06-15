from setuptools import setup, find_packages

setup(
    name="isa_mcp",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "langchain>=0.1.0",
        "langchain-core>=0.1.0",
        "langgraph>=0.0.10",
        "pydantic>=2.0.0",
        "fastapi>=0.100.0",
        "uvicorn>=0.22.0",
        "python-dotenv>=1.0.0",
        "neo4j>=5.0.0",
    ],
    author="Your Name",
    author_email="your.email@example.com",
    description="ISA MCP Framework - A Model-Controller-Presenter framework for AI agents",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/isa_mcp",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.8",
)
