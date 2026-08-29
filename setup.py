"""Packaging for WiFi-Evil-Twin."""

from setuptools import setup, find_packages
from wifi_evil_twin import __version__

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="wifi-evil-twin",
    version=__version__,
    description="Authorized Evil Twin / rogue-AP WiFi testing framework.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/sachintha82288-cpu/WiFi-Evil-Twin",
    packages=find_packages(exclude=("tests", "tests.*")),
    include_package_data=True,
    python_requires=">=3.8",
    install_requires=[
        "Flask>=2.3,<4.0",
        "Jinja2>=3.0",
        "Werkzeug>=2.3",
        "colorama>=0.4",
    ],
    entry_points={
        "console_scripts": [
            "wifi-evil-twin=wifi_evil_twin.cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Topic :: Security",
        "Environment :: Console",
    ],
)
