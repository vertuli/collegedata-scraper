import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="collegedatascraper",
    version="0.1.0",
    author="Michael Francis Vertuli",
    author_email="michael@vertuli.com",
    description="Scrape CollegeData.com",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/vertuli/collegedatascraper",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)