#!/usr/bin/env python3
"""
Dependency Verification Script for MEDIPREDICT
Checks Python package dependencies, versions, and conflicts.
"""

import os
import sys
import re
import json
import pkg_resources
import subprocess
import platform
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/requirements_check.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DependencyStatus(Enum):
    """Enum for dependency status."""
    OK = "✓"
    OUTDATED = "🔄"
    MISSING = "✗"
    INCOMPATIBLE = "⚠"
    CONFLICT = "⚡"

@dataclass
class Dependency:
    """Class representing a package dependency."""
    name: str
    required_version: str
    installed_version: Optional[str] = None
    latest_version: Optional[str] = None
    status: DependencyStatus = DependencyStatus.MISSING
    conflicts: List[str] = None
    
    def __post_init__(self):
        if self.conflicts is None:
            self.conflicts = []

class RequirementsChecker:
    """Main class for dependency verification."""
    
    def __init__(self, requirements_files=None):
        self.project_root = Path(__file__).parent.parent
        
        if requirements_files is None:
            requirements_files = [
                'requirements.txt',
                'requirements-dev.txt'
            ]
        
        self.requirements_files = [self.project_root / f for f in requirements_files]
        self.dependencies: Dict[str, Dependency] = {}
        self.python_version = platform.python_version()
        self.system_info = self.get_system_info()
        
    def get_system_info(self) -> Dict:
        """Get system information."""
        return {
            'platform': platform.platform(),
            'python_version': self.python_version,
            'python_implementation': platform.python_implementation(),
            'machine': platform.machine(),
            'processor': platform.processor()
        }
    
    def parse_requirements_file(self, file_path: Path) -> List[Tuple[str, str]]:
        """Parse requirements file and extract dependencies."""
        dependencies = []
        
        if not file_path.exists():
            logger.warning(f"Requirements file not found: {file_path}")
            return dependencies
        
        with open(file_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                
                # Handle -r for recursive includes
                if line.startswith('-r '):
                    include_file = line[3:].strip()
                    include_path = file_path.parent / include_file
                    if include_path.exists():
                        dependencies.extend(self.parse_requirements_file(include_path))
                    else:
                        logger.warning(f"Included file not found: {include_path}")
                    continue
                
                # Parse package specification
                try:
                    # Handle various requirement formats
                    if line.startswith('git+'):
                        # Git repository
                        match = re.search(r'#egg=([\w\-]+)', line)
                        if match:
                            package_name = match.group(1)
                            dependencies.append((package_name, 'git'))
                        else:
                            logger.warning(f"Could not parse git requirement: {line}")
                    
                    elif '@' in line:
                        # Direct URL
                        package_name = line.split('@')[0].strip()
                        dependencies.append((package_name, 'url'))
                    
                    else:
                        # Standard package specification
                        # Remove environment markers
                        if ';' in line:
                            line = line.split(';')[0].strip()
                        
                        # Parse package and version
                        if '>=' in line:
                            parts = line.split('>=')
                            package_name = parts[0].strip()
                            version = f">={parts[1].strip()}"
                        elif '<=' in line:
                            parts = line.split('<=')
                            package_name = parts[0].strip()
                            version = f"<={parts[1].strip()}"
                        elif '>' in line:
                            parts = line.split('>')
                            package_name = parts[0].strip()
                            version = f">{parts[1].strip()}"
                        elif '<' in line:
                            parts = line.split('<')
                            package_name = parts[0].strip()
                            version = f"<{parts[1].strip()}"
                        elif '==' in line:
                            parts = line.split('==')
                            package_name = parts[0].strip()
                            version = f"=={parts[1].strip()}"
                        elif '~=' in line:
                            parts = line.split('~=')
                            package_name = parts[0].strip()
                            version = f"~={parts[1].strip()}"
                        elif '!=' in line:
                            parts = line.split('!=')
                            package_name = parts[0].strip()
                            version = f"!={parts[1].strip()}"
                        else:
                            package_name = line.strip()
                            version = 'any'
                        
                        dependencies.append((package_name, version))
                
                except Exception as e:
                    logger.error(f"Error parsing line {line_num} in {file_path}: {e}")
                    logger.error(f"Line content: {line}")
        
        return dependencies
    
    def get_installed_version(self, package_name: str) -> Optional[str]:
        """Get installed version of a package."""
        try:
            # Try standard import
            dist = pkg_resources.get_distribution(package_name)
            return dist.version
        except pkg_resources.DistributionNotFound:
            # Try alternative package names
            alternatives = {
                'scikit-learn': 'sklearn',
                'psycopg2-binary': 'psycopg2',
                'Pillow': 'PIL',
                'django-crispy-forms': 'crispy_forms',
                'djangorestframework': 'rest_framework'
            }
            
            alt_name = alternatives.get(package_name)
            if alt_name:
                try:
                    dist = pkg_resources.get_distribution(alt_name)
                    return dist.version
                except pkg_resources.DistributionNotFound:
                    pass
            
            return None
    
    def get_latest_version(self, package_name: str) -> Optional[str]:
        """Get latest version available on PyPI."""
        try:
            import requests
            
            # Use PyPI JSON API
            url = f"https://pypi.org/pypi/{package_name}/json"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                return data['info']['version']
            else:
                return None
                
        except Exception as e:
            logger.debug(f"Could not fetch latest version for {package_name}: {e}")
            return None
    
    def check_version_compatibility(self, required: str, installed: str) -> bool:
        """Check if installed version satisfies requirement."""
        if required == 'any' or required == 'git' or required == 'url':
            return True
        
        try:
            # Parse version specifier
            if required.startswith('=='):
                required_version = required[2:]
                return installed == required_version
            
            elif required.startswith('>='):
                required_version = required[2:]
                return self.compare_versions(installed, required_version) >= 0
            
            elif required.startswith('<='):
                required_version = required[2:]
                return self.compare_versions(installed, required_version) <= 0
            
            elif required.startswith('>'):
                required_version = required[1:]
                return self.compare_versions(installed, required_version) > 0
            
            elif required.startswith('<'):
                required_version = required[1:]
                return self.compare_versions(installed, required_version) < 0
            
            elif required.startswith('~='):
                # Compatible release
                required_version = required[2:]
                return self.is_compatible_release(installed, required_version)
            
            elif required.startswith('!='):
                required_version = required[2:]
                return installed != required_version
            
            else:
                logger.warning(f"Unknown version specifier: {required}")
                return True
                
        except Exception as e:
            logger.error(f"Error checking version compatibility: {e}")
            return False
    
    def compare_versions(self, v1: str, v2: str) -> int:
        """Compare two version strings."""
        try:
            from pkg_resources import parse_version
            v1_parsed = parse_version(v1)
            v2_parsed = parse_version(v2)
            
            if v1_parsed < v2_parsed:
                return -1
            elif v1_parsed > v2_parsed:
                return 1
            else:
                return 0
        except Exception:
            # Fallback simple comparison
            return (v1 > v2) - (v1 < v2)
    
    def is_compatible_release(self, installed: str, required: str) -> bool:
        """Check compatible release (~= operator)."""
        # For ~= X.Y, requires >= X.Y, == X.*
        # For ~= X.Y.Z, requires >= X.Y.Z, == X.Y.*
        
        installed_parts = installed.split('.')
        required_parts = required.split('.')
        
        # Ensure same length
        min_len = min(len(installed_parts), len(required_parts))
        installed_parts = installed_parts[:min_len]
        required_parts = required_parts[:min_len]
        
        # Check major and minor versions match
        for i in range(min_len - 1):
            if installed_parts[i] != required_parts[i]:
                return False
        
        # Check installed >= required for last part
        if int(installed_parts[-1]) < int(required_parts[-1]):
            return False
        
        return True
    
    def detect_conflicts(self) -> Dict[str, List[str]]:
        """Detect package conflicts."""
        conflicts = {}
        
        # Check for common conflicts
        conflict_patterns = [
            (['tensorflow', 'tensorflow-gpu'], 'Both tensorflow and tensorflow-gpu installed'),
            (['mysqlclient', 'mysql-connector-python'], 'Multiple MySQL connectors'),
            (['django', 'djangorestframework'], 'Version compatibility check needed'),
        ]
        
        for packages, reason in conflict_patterns:
            installed = [p for p in packages if p in self.dependencies 
                        and self.dependencies[p].status != DependencyStatus.MISSING]
            if len(installed) > 1:
                for pkg in installed:
                    if pkg not in conflicts:
                        conflicts[pkg] = []
                    conflicts[pkg].append(reason)
        
        # Check for version conflicts in dependency tree
        try:
            import pipdeptree
            
            tree = pipdeptree.get_installed_distributions()
            for dist in tree:
                for req in dist.requires():
                    req_name = req.project_name
                    if req_name in self.dependencies:
                        # Check if required version conflicts with installed
                        if req.specifier:
                            installed_version = self.dependencies[dist.project_name].installed_version
                            if installed_version:
                                # This is a simplified check
                                pass
        
        except ImportError:
            logger.warning("pipdeptree not installed, skipping advanced conflict detection")
        
        return conflicts
    
    def check_dependencies(self) -> Dict[str, Dependency]:
        """Check all dependencies."""
        logger.info("Checking dependencies...")
        
        # Parse all requirements files
        all_deps = []
        for req_file in self.requirements_files:
            if req_file.exists():
                file_deps = self.parse_requirements_file(req_file)
                all_deps.extend(file_deps)
        
        # Remove duplicates, keeping the strictest requirement
        deps_dict = {}
        for package_name, version in all_deps:
            if package_name in deps_dict:
                # Keep the stricter requirement
                old_version = deps_dict[package_name]
                if version != 'any' and old_version == 'any':
                    deps_dict[package_name] = version
                elif version.startswith('==') and not old_version.startswith('=='):
                    deps_dict[package_name] = version
                elif '>=' in version and '>' in old_version:
                    # >= is stricter than >
                    deps_dict[package_name] = version
            else:
                deps_dict[package_name] = version
        
        # Check each dependency
        for package_name, required_version in deps_dict.items():
            dep = Dependency(name=package_name, required_version=required_version)
            
            # Get installed version
            installed_version = self.get_installed_version(package_name)
            
            if installed_version:
                dep.installed_version = installed_version
                
                # Check version compatibility
                if self.check_version_compatibility(required_version, installed_version):
                    dep.status = DependencyStatus.OK
                    
                    # Check if outdated
                    latest_version = self.get_latest_version(package_name)
                    if latest_version and latest_version != installed_version:
                        dep.latest_version = latest_version
                        
                        # Only mark as outdated if not pinned to specific version
                        if not required_version.startswith('=='):
                            dep.status = DependencyStatus.OUTDATED
                else:
                    dep.status = DependencyStatus.INCOMPATIBLE
            else:
                dep.status = DependencyStatus.MISSING
            
            self.dependencies[package_name] = dep
        
        # Detect conflicts
        conflicts = self.detect_conflicts()
        for package_name, conflict_reasons in conflicts.items():
            if package_name in self.dependencies:
                self.dependencies[package_name].status = DependencyStatus.CONFLICT
                self.dependencies[package_name].conflicts = conflict_reasons
        
        return self.dependencies
    
    def generate_report(self) -> Dict:
        """Generate comprehensive dependency report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'system_info': self.system_info,
            'requirements_files': [str(f) for f in self.requirements_files],
            'summary': {
                'total': 0,
                'ok': 0,
                'outdated': 0,
                'missing': 0,
                'incompatible': 0,
                'conflicts': 0
            },
            'dependencies': {},
            'recommendations': []
        }
        
        for dep in self.dependencies.values():
            report['summary']['total'] += 1
            
            if dep.status == DependencyStatus.OK:
                report['summary']['ok'] += 1
            elif dep.status == DependencyStatus.OUTDATED:
                report['summary']['outdated'] += 1
            elif dep.status == DependencyStatus.MISSING:
                report['summary']['missing'] += 1
            elif dep.status == DependencyStatus.INCOMPATIBLE:
                report['summary']['incompatible'] += 1
            elif dep.status == DependencyStatus.CONFLICT:
                report['summary']['conflicts'] += 1
            
            # Add dependency details
            report['dependencies'][dep.name] = {
                'required': dep.required_version,
                'installed': dep.installed_version,
                'latest': dep.latest_version,
                'status': dep.status.value,
                'conflicts': dep.conflicts
            }
        
        # Generate recommendations
        if report['summary']['missing'] > 0:
            missing_pkgs = [d.name for d in self.dependencies.values() 
                          if d.status == DependencyStatus.MISSING]
            report['recommendations'].append({
                'action': 'install',
                'packages': missing_pkgs,
                'command': f"pip install {' '.join(missing_pkgs)}"
            })
        
        if report['summary']['outdated'] > 0:
            outdated_pkgs = [d.name for d in self.dependencies.values() 
                           if d.status == DependencyStatus.OUTDATED]
            report['recommendations'].append({
                'action': 'upgrade',
                'packages': outdated_pkgs,
                'command': f"pip install --upgrade {' '.join(outdated_pkgs)}"
            })
        
        if report['summary']['conflicts'] > 0:
            report['recommendations'].append({
                'action': 'resolve_conflicts',
                'message': 'Review and resolve package conflicts',
                'conflicting_packages': [
                    d.name for d in self.dependencies.values() 
                    if d.status == DependencyStatus.CONFLICT
                ]
            })
        
        # Save report
        report_dir = self.project_root / 'dependency_reports'
        report_dir.mkdir(exist_ok=True)
        
        report_file = report_dir / f'dependency_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Dependency report saved to: {report_file}")
        
        return report
    
    def print_summary(self, report: Dict):
        """Print dependency check summary."""
        print("\n" + "="*60)
        print("DEPENDENCY CHECK SUMMARY")
        print("="*60)
        
        print(f"\nSystem Information:")
        print(f"  Platform: {self.system_info['platform']}")
        print(f"  Python: {self.system_info['python_version']}")
        
        print(f"\nRequirements Files:")
        for file in report['requirements_files']:
            print(f"  {file}")
        
        print(f"\nDependency Status:")
        summary = report['summary']
        print(f"  Total: {summary['total']}")
        print(f"  ✓ OK: {summary['ok']}")
        print(f"  🔄 Outdated: {summary['outdated']}")
        print(f"  ✗ Missing: {summary['missing']}")
        print(f"  ⚠ Incompatible: {summary['incompatible']}")
        print(f"  ⚡ Conflicts: {summary['conflicts']}")
        
        # Print detailed status
        if any(v > 0 for k, v in summary.items() if k != 'total' and k != 'ok'):
            print(f"\nDetailed Status:")
            print("-" * 40)
            
            for dep_name, dep_info in report['dependencies'].items():
                if dep_info['status'] != '✓':
                    status_icon = dep_info['status']
                    print(f"{status_icon} {dep_name}:")
                    print(f"    Required: {dep_info['required']}")
                    print(f"    Installed: {dep_info.get('installed', 'Not installed')}")
                    if dep_info.get('latest'):
                        print(f"    Latest: {dep_info['latest']}")
                    if dep_info.get('conflicts'):
                        print(f"    Conflicts: {', '.join(dep_info['conflicts'])}")
        
        # Print recommendations
        if report['recommendations']:
            print(f"\nRecommendations:")
            print("-" * 40)
            
            for rec in report['recommendations']:
                if rec['action'] == 'install':
                    print(f"\nMissing packages detected:")
                    print(f"  Command: {rec['command']}")
                
                elif rec['action'] == 'upgrade':
                    print(f"\nOutdated packages detected:")
                    print(f"  Command: {rec['command']}")
                
                elif rec['action'] == 'resolve_conflicts':
                    print(f"\nPackage conflicts detected:")
                    print(f"  Conflicting packages: {', '.join(rec['conflicting_packages'])}")
                    print(f"  Action: {rec['message']}")
        
        print("\n" + "="*60)
        
        # Overall status
        if summary['missing'] > 0 or summary['incompatible'] > 0 or summary['conflicts'] > 0:
            print("\n\033[91m✗ Dependency check FAILED\033[0m")
            return False
        elif summary['outdated'] > 0:
            print("\n\033[93m⚠ Dependency check PASSED with warnings\033[0m")
            return True
        else:
            print("\n\033[92m✓ Dependency check PASSED\033[0m")
            return True
    
    def fix_dependencies(self, auto_fix: bool = False) -> bool:
        """Attempt to fix dependency issues."""
        logger.info("Attempting to fix dependencies...")
        
        issues_fixed = 0
        issues_total = 0
        
        for dep in self.dependencies.values():
            if dep.status == DependencyStatus.MISSING:
                issues_total += 1
                if auto_fix:
                    try:
                        logger.info(f"Installing {dep.name}...")
                        subprocess.run(
                            [sys.executable, '-m', 'pip', 'install', dep.name],
                            check=True,
                            capture_output=True
                        )
                        issues_fixed += 1
                        logger.info(f"Installed {dep.name}")
                    except subprocess.CalledProcessError as e:
                        logger.error(f"Failed to install {dep.name}: {e}")
            
            elif dep.status == DependencyStatus.OUTDATED:
                issues_total += 1
                if auto_fix:
                    try:
                        logger.info(f"Upgrading {dep.name}...")
                        subprocess.run(
                            [sys.executable, '-m', 'pip', 'install', '--upgrade', dep.name],
                            check=True,
                            capture_output=True
                        )
                        issues_fixed += 1
                        logger.info(f"Upgraded {dep.name}")
                    except subprocess.CalledProcessError as e:
                        logger.error(f"Failed to upgrade {dep.name}: {e}")
        
        logger.info(f"Fixed {issues_fixed}/{issues_total} issues")
        
        if issues_fixed > 0:
            # Re-check dependencies
            self.check_dependencies()
        
        return issues_fixed == issues_total

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='MEDIPREDICT Dependency Checker')
    parser.add_argument('--fix', action='store_true',
                       help='Automatically fix missing and outdated packages')
    parser.add_argument('--report-only', action='store_true',
                       help='Generate report only, no console output')
    parser.add_argument('--requirements', nargs='+',
                       help='Custom requirements files to check')
    parser.add_argument('--output', type=str,
                       help='Output report file path')
    
    args = parser.parse_args()
    
    checker = RequirementsChecker(
        requirements_files=args.requirements if args.requirements else None
    )
    
    # Check dependencies
    dependencies = checker.check_dependencies()
    
    # Generate report
    report = checker.generate_report()
    
    # Print summary unless report-only mode
    if not args.report_only:
        success = checker.print_summary(report)
    
    # Auto-fix if requested
    if args.fix:
        checker.fix_dependencies(auto_fix=True)
    
    # Save report to custom location if specified
    if args.output:
        output_path = Path(args.output)
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info(f"Report saved to: {output_path}")
    
    # Exit with appropriate code
    if not args.report_only:
        sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()