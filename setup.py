"""
Setup script para COE IA Training
Permite instalar el paquete en modo editable: pip install -e .
"""

from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = [
        line.strip()
        for line in f
        if line.strip() and not line.startswith("#")
    ]

setup(
    name="coe-ia-training",
    version="1.0.0",
    description="Capacitación en Agentes de IA para COE TI AFP Integra",
    author="LILAB",
    python_requires=">=3.11",
    packages=find_packages(),
    install_requires=requirements,
    extras_require={
        "dev": [
            "ipython>=8.12.0",
            "ipdb>=0.13.13",
        ]
    },
    entry_points={
        "console_scripts": [
            "coe-api=src.api.main:main",
        ],
    },
)
