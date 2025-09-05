#!/usr/bin/env python
"""
Setup script for CCXT Multi-Exchange Copy Trading System
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

# Read requirements
def read_requirements(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="ccxt-multi-exchange-copy-trader",
    version="1.0.0",
    author="yigoza",
    author_email="yigit.ozaksut@example.com",
    description="Multi-exchange copy trading system using CCXT library",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yigoza/ccxt-multi-exchange-copy-trader",
    packages=find_packages(exclude=["tests", "docs", "examples"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Office/Business :: Financial :: Investment",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="cryptocurrency trading copy-trading ccxt binance bybit exchange api",
    python_requires=">=3.8",
    install_requires=read_requirements("requirements.txt"),
    extras_require={
        "dev": read_requirements("requirements-dev.txt"),
        "test": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
        ],
        "docs": [
            "sphinx>=5.0.0",
            "sphinx-rtd-theme>=1.2.0",
            "myst-parser>=0.18.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "ccxt-copy-trader=exchange.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.json", "*.yaml", "*.yml"],
        "exchange": ["config/*.json", "config/*.yaml"],
    },
    project_urls={
        "Bug Reports": "https://github.com/yigoza/ccxt-multi-exchange-copy-trader/issues",
        "Source": "https://github.com/yigoza/ccxt-multi-exchange-copy-trader",
        "Documentation": "https://ccxt-multi-exchange-copy-trader.readthedocs.io/",
    },
)
