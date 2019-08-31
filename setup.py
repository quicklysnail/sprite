from setuptools import setup, find_packages

setup(
    name="sprite",
    version="0.1.0",
    author="liyong",
    description="Python 3.6+ web scraping micro-framework based on asyncio coroutine pool.",
    long_description_content_type="text/markdown",
    author_email="819078740@qq.com",
    python_requires=">=3.6",
    install_requires=["httptools", "bitarray", "w3lib", "typing"],
    packages=find_packages(),
    license="MIT",
    classifiers=[
        "Framework :: AsyncIO",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX :: BSD",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3.6",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
