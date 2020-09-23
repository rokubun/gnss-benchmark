from setuptools import find_packages, setup


# read the contents of your README file
from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


setup(
    name='gnss-benchmark',
    version_cc='{version}',
    author='Rokubun',
    author_email='info@rokubun.cat',
    description='GNSS benchmarking tool',
    long_description=long_description,
    long_description_content_type='text/markdown',
    license='http://opensource.org/licenses/MIT',
    url="https://github.com/rokubun/gnss-benchmark",
    setup_requires=['setuptools-git-version-cc'],
    packages=["gnss_benchmark"],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        "docopt",
        "jason_gnss",
        "jinja2",
        "matplotlib",
        "numpy",
        "pandoc",
        "pyproj",
        "requests",
        "roktools"
    ],
    entry_points={
        'console_scripts': [
            'gnss_benchmark = gnss_benchmark.main:main'
        ]
    }
)
