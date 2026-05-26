from setuptools import setup, find_packages

with open("requirements.txt") as f:
    reqs = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="classification_cma_es",
    version="0.1.0",
    description="Порівняння класифікаторів з використанням розширеного CMA-ES",
    author="Bohdan",
    packages=find_packages(exclude=["tests", "tests.*", "notebooks"]),
    install_requires=reqs,
    python_requires=">=3.10",
)
