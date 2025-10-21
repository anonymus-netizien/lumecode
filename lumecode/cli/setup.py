#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(
    name="lumecode-cli",
    version="0.1.0",
    description="Lumecode CLI - Command-line interface for the Lumecode platform",
    author="Lumecode Team",
    author_email="info@lumecode.ai",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "click>=8.0.0",
        "colorama>=0.4.4",
        "requests>=2.25.0",
        "pyyaml>=6.0",
        "rich>=10.0.0",
    ],
    entry_points={
        "console_scripts": [
            "lumecode=cli.main:main",
        ],
    },
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
