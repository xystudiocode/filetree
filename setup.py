from setuptools import setup, find_packages

setup(
    name = "fileTreeCommand",
    version = "0.1.0",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires = [],
    python_requires = ">=3",
    author = "xystudio",
    author_email = "173288240@qq.com",
    description = "",
    long_description = open("README.md",encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    license = "MIT",
    url = "https://github.com/xystudio889/",
    entry_points = {
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    keywords = "",
)
