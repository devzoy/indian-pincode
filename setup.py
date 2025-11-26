from setuptools import setup, find_packages

setup(
    name="indian-pincode",
    version="1.0.0",
    description="High-performance Indian Pincode library",
    author="DevZoy",
    packages=["indian_pincode"],
    package_dir={"": "src/python"},
    include_package_data=True,
    package_data={
        "indian_pincode": ["data/*.json", "data/*.sqlite"],
    },
    install_requires=[],
    python_requires=">=3.6",
)
