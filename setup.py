from setuptools import find_packages, setup


setup(
    name="contrail-vcenter-fabric-manager",
    version="0.1dev",
    packages=find_packages(),
    package_data={"": ["*.html", "*.css", "*.xml", "*.yml"]},
    zip_safe=False,
    long_description="Contrail vCenter Fabric Manager",
    install_requires=["six", "future"],
    entry_points={
        "console_scripts": [
            "contrail-vcenter-fabric-manager = cvfm:server_main"
        ]
    },
)
