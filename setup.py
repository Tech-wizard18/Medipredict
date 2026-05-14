#!/usr/bin/env python
"""
Setup script for MEDIPREDICT Disease Prediction System.
"""

from setuptools import setup, find_packages
import os
import re

# Read version from __init__.py
with open(os.path.join('disease_app', '__init__.py'), 'r') as f:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]', f.read(), re.MULTILINE).group(1)

# Read requirements
with open('requirements.txt', 'r') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

# Read development requirements
with open('requirements-dev.txt', 'r') as f:
    dev_requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

# Read long description from README
with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='medipredict',
    version=version,
    description='A comprehensive disease prediction system using machine learning',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='MEDIPREDICT Team',
    author_email='contact@medipredict.com',
    url='https://github.com/yourusername/medipredict',
    license='MIT',
    
    # Package discovery
    packages=find_packages(exclude=['tests', 'tests.*']),
    include_package_data=True,
    
    # Dependencies
    install_requires=requirements,
    extras_require={
        'dev': dev_requirements,
        'ml': [
            'scikit-learn>=1.3.0',
            'pandas>=2.0.0',
            'numpy>=1.24.0',
            'xgboost>=2.0.0',
            'lightgbm>=4.0.0',
        ],
        'api': [
            'djangorestframework>=3.14.0',
            'django-cors-headers>=4.0.0',
            'drf-yasg>=1.21.0',
        ],
        'celery': [
            'celery>=5.3.0',
            'redis>=5.0.0',
            'django-celery-beat>=2.5.0',
        ],
    },
    
    # Entry points
    entry_points={
        'console_scripts': [
            'medipredict = manage:main',
            'medipredict-train = train_real_models:main',
            'medipredict-celery = celery_app:app.start',
        ],
    },
    
    # Classifiers
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 4.2',
        'Intended Audience :: Healthcare Industry',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
        'Topic :: Scientific/Engineering :: Medical Science Apps.',
    ],
    
    # Keywords
    keywords='disease prediction machine learning healthcare django',
    
    # Project URLs
    project_urls={
        'Documentation': 'https://medipredict.readthedocs.io/',
        'Source': 'https://github.com/yourusername/medipredict',
        'Tracker': 'https://github.com/yourusername/medipredict/issues',
    },
    
    # Python version requirement
    python_requires='>=3.11',
    
    # Data files
    data_files=[
        ('config', ['.env.example']),
        ('docs', ['README.md', 'CHANGELOG.md', 'CONTRIBUTING.md']),
        ('scripts', ['scripts/setup_database.py', 'scripts/backup_database.py']),
    ],
    
    # Zip safe
    zip_safe=False,
    
    # Additional metadata
    platforms='any',
    test_suite='tests',
    
    # Package data
    package_data={
        'medipredict': [
            'templates/**/*.html',
            'static/**/*',
            'ml_models/*.pkl',
            'ml_models/scalers/*.pkl',
        ],
    },
    
    # Provides
    provides=['medipredict'],
    
    # Obsoletes
    obsoletes=['old-medipredict'],
    
    # Download URL
    download_url=f'https://github.com/yourusername/medipredict/archive/v{version}.tar.gz',
)

if __name__ == '__main__':
    print(f"MEDIPREDICT v{version}")
    print("Setup complete.")