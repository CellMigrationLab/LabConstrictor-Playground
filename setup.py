from setuptools import setup, find_packages

setup(
    name="labconstrictor_playground",
    version="0.1.0",
    description="LabConstrictor Playground: check an installation (machine, worker, GPU) and try every feature of the tools bridge",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.12",
    install_requires=[
        "numpy",
        "pandas",
        "scipy",
        "matplotlib",
        "tifffile",
    ],
)
