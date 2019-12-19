from setuptools import find_packages, setup


setup(
    name="contrail-vcenter-fabric-manager",
    version="0.1dev",
    packages=find_packages(),
    package_data={"": ["*.html", "*.css", "*.xml", "*.yml"]},
    zip_safe=False,
    long_description="Contrail vCenter Fabric Manager",
    install_requires=["six", "future"],
    test_suite="tests",
    entry_points={
        "console_scripts": [
            "contrail-vcenter-fabric-manager = cvfm.__main__:server_main"
        ]
    },
)
