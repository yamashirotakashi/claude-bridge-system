"""
Claude Bridge System Setup
"""

from setuptools import setup, find_packages
from pathlib import Path

# README読み込み
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

# 要件読み込み
requirements_path = Path(__file__).parent / "requirements.txt"
if requirements_path.exists():
    with open(requirements_path, 'r', encoding='utf-8') as f:
        requirements = [
            line.strip() for line in f 
            if line.strip() and not line.startswith('#')
        ]
else:
    requirements = []

setup(
    name="claude-bridge-system",
    version="1.0.0",
    author="Claude Bridge Development Team",
    author_email="contact@claude-bridge.dev",
    description="Claude Code CLI と Claude Desktop の統合連携システム",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yamashirotakashi/claude-bridge-system",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: System Administration",
        "Topic :: Utilities",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0", 
            "black>=23.0.0",
            "mypy>=1.0.0",
            "flake8>=6.0.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "claude-bridge=claude_bridge.cli.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "claude_bridge": [
            "config/*.json",
            "templates/*.md",
        ],
    },
    zip_safe=False,
)