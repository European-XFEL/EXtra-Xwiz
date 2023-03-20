#!/usr/bin/env python
import os.path as osp
import re
from setuptools import setup, find_packages
import sys


def get_script_path():
    return osp.dirname(osp.realpath(sys.argv[0]))


def read(*parts):
    return open(osp.join(get_script_path(), *parts)).read()


def find_version(*parts):
    vers_file = read(*parts)
    match = re.search(r'^__version__ = "(\d+\.\d+\.\d+)"', vers_file, re.M)
    if match is not None:
        return match.group(1)
    raise RuntimeError("Unable to find version string.")


setup(
    name="EXtra-xwiz",
    version=find_version("extra_xwiz", "__init__.py"),
    author="European XFEL GmbH",
    author_email="da-support@xfel.eu",
    maintainer="Fabio Dall'Antonia",
    url="",
    description="Tool to automate SFX workflows",
    long_description=read("README.md"),
    long_description_content_type='text/markdown',
    license="BSD-3-Clause",
    packages=find_packages(),
    package_data={
        "": ["resources/*.geom"]
    },
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "xwiz-cell-checker = extra_xwiz.cell_check:main",
            "xwiz-collector = extra_xwiz.collector:main",
            "xwiz-powder = extra_xwiz.powder:main",
            "xwiz-workflow = extra_xwiz.workflow:main",
            "xwiz-mask-hd52geom = extra_xwiz.mask_converter.mask_hd52geom:main",
            "xwiz-mask-geom2hd5 = extra_xwiz.mask_converter.mask_geom2hd5:main",
            "xwiz-scan-parameters = extra_xwiz.param_scan.scan_parameters:main",
            "xwiz-import-project = extra_xwiz.import_cryst_project:main",
        ],
    },
    install_requires=[
        'h5py',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'toml',
        'xarray',
        'findxfel>=0.1.1',
        'extra_data>=1.4',
        'psutil',
    ],
    extras_require={
        'docs': [],
        'test': []
    },
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: Scientific/Engineering :: Physics',
    ]
)

