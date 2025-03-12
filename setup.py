from setuptools import setup, find_packages

setup(
    name="montreal_parking_finder",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "pandas>=1.3.0",
        "numpy>=1.20.0",
        "requests>=2.25.1",
        "shapely>=1.7.1",
        "geopandas>=0.9.0",
        "matplotlib>=3.4.0",
        "folium>=0.12.1",
        "Flask>=2.0.0",
        "SQLAlchemy>=1.4.0",
        "geopy>=2.2.0",
        "multiprocessing>=0.70.12",
    ],
    entry_points={
        "console_scripts": [
            "montreal-parking-finder=montreal_parking_finder.cli:main",
        ],
    },
)
