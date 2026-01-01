"""
Score Configuration Loader

Loads security control scores and category weights from an Excel configuration file.
This allows admins to modify scores without changing code.
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime
import os


class ScoreConfigLoader:
    """
    Loads and caches security scoring configuration from Excel.

    Usage:
        loader = ScoreConfigLoader()
        max_points = loader.get_control_max_points('mfa_enforcement')
        weight = loader.get_category_weight('Security')
    """

    _instance = None
    _config_loaded = False
    _controls: Dict[str, Dict] = {}
    _weights: Dict[str, int] = {}
    _last_load_time: datetime = None
    _cache_duration_seconds: int = 300  # Reload config every 5 minutes

    # Default Excel file path
    DEFAULT_CONFIG_PATH = Path(__file__).parent / "data" / "security_control_scores.xlsx"

    def __new__(cls):
        """Singleton pattern - only one instance"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the loader.

        Args:
            config_path: Optional path to Excel config file.
                        Uses default path if not specified.
        """
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self._ensure_config_loaded()

    def _ensure_config_loaded(self, force_reload: bool = False) -> bool:
        """
        Ensure configuration is loaded, reload if needed.

        Args:
            force_reload: Force reload even if cache is valid

        Returns:
            True if config was loaded/reloaded
        """
        # Check if we need to reload
        if self._config_loaded and not force_reload:
            if self._last_load_time:
                elapsed = (datetime.now() - self._last_load_time).total_seconds()
                if elapsed < self._cache_duration_seconds:
                    return False  # Cache is still valid

        return self._load_config()

    def _load_config(self) -> bool:
        """
        Load configuration from Excel file.

        Returns:
            True if loaded successfully
        """
        try:
            if not self.config_path.exists():
                print(f"Warning: Config file not found at {self.config_path}")
                print("Using hardcoded defaults. Run create_score_config.py to create the file.")
                self._load_defaults()
                return False

            # Load Controls sheet
            controls_df = pd.read_excel(self.config_path, sheet_name='Controls')

            # Build controls dictionary keyed by ControlKey
            self._controls = {}
            for _, row in controls_df.iterrows():
                control_key = row['ControlKey']
                self._controls[control_key] = {
                    'category': row['Category'],
                    'sub_category': row['SubCategory'],
                    'control_name': row['Control'],
                    'max_points': int(row['MaxPoints']),
                    'description': row['Description'],
                    'thresholds': row['Thresholds']
                }

            # Load CategoryWeights sheet
            weights_df = pd.read_excel(self.config_path, sheet_name='CategoryWeights')

            self._weights = {}
            for _, row in weights_df.iterrows():
                category = row['Category']
                # Map category names to internal keys
                category_key = category.lower().replace(' ', '_').replace('&', '')
                if category_key == 'collaboration__productivity':
                    category_key = 'collaboration'
                elif category_key == 'operations__governance':
                    category_key = 'operations'

                self._weights[category_key] = int(row['WeightPercentage'])

            self._config_loaded = True
            self._last_load_time = datetime.now()

            print(f"Loaded scoring config: {len(self._controls)} controls, {len(self._weights)} categories")
            return True

        except Exception as e:
            print(f"Error loading scoring config: {e}")
            self._load_defaults()
            return False

    def _load_defaults(self):
        """Load hardcoded default values as fallback"""
        self._controls = {
            'mfa_enforcement': {'max_points': 20, 'control_name': 'MFA Enforcement'},
            'admin_mfa_enforcement': {'max_points': 15, 'control_name': 'Admin MFA Enforcement'},
            'password_age_policy': {'max_points': 10, 'control_name': 'Password Age Policy'},
            'inactive_account_mgmt': {'max_points': 10, 'control_name': 'Inactive Account Management'},
            'emergency_access': {'max_points': 10, 'control_name': 'Emergency Access Accounts'},
            'pim': {'max_points': 20, 'control_name': 'Privileged Identity Management'},
            'defender_o365': {'max_points': 25, 'control_name': 'Defender for Office 365'},
            'anti_phishing': {'max_points': 20, 'control_name': 'Anti-phishing Policies'},
            'safe_links': {'max_points': 15, 'control_name': 'Safe Links'},
            'safe_attachments': {'max_points': 15, 'control_name': 'Safe Attachments'},
            'anti_malware': {'max_points': 15, 'control_name': 'Anti-malware Policies'},
            'zap': {'max_points': 10, 'control_name': 'Zero-hour Auto Purge'},
            'sensitivity_labels': {'max_points': 25, 'control_name': 'Sensitivity Labels'},
            'dlp_policies': {'max_points': 25, 'control_name': 'DLP Policies'},
            'encryption_policies': {'max_points': 20, 'control_name': 'Encryption Policies'},
            'aip': {'max_points': 15, 'control_name': 'Azure Information Protection'},
            'auto_labeling': {'max_points': 15, 'control_name': 'Auto-labeling Rules'},
            'unified_audit_log': {'max_points': 40, 'control_name': 'Unified Audit Log'},
            'alert_policies': {'max_points': 30, 'control_name': 'Alert Policies'},
            'signin_risk': {'max_points': 30, 'control_name': 'Sign-in Risk Policies'},
            'retention_policies': {'max_points': 30, 'control_name': 'Retention Policies'},
            'records_mgmt': {'max_points': 25, 'control_name': 'Records Management'},
            'info_barriers': {'max_points': 20, 'control_name': 'Information Barriers'},
            'comm_compliance': {'max_points': 25, 'control_name': 'Communication Compliance'},
            'compliance_mgr_score': {'max_points': 40, 'control_name': 'Compliance Manager Score'},
            'compliance_templates': {'max_points': 30, 'control_name': 'Compliance Templates'},
            'compliance_assessments': {'max_points': 30, 'control_name': 'Compliance Assessments'},
            'ediscovery': {'max_points': 50, 'control_name': 'eDiscovery Cases'},
            'legal_hold': {'max_points': 50, 'control_name': 'Legal Hold Policies'},
            'guest_access': {'max_points': 20, 'control_name': 'Guest Access Governance'},
            'sspr': {'max_points': 20, 'control_name': 'Self-Service Password Reset'},
            'block_legacy_auth': {'max_points': 20, 'control_name': 'Block Legacy Authentication'},
            'ca_admin_mfa': {'max_points': 20, 'control_name': 'Require MFA for Admins'},
            'compliant_devices': {'max_points': 15, 'control_name': 'Require Compliant Devices'},
            'geo_restrictions': {'max_points': 10, 'control_name': 'Geographic Restrictions'},
            'session_controls': {'max_points': 15, 'control_name': 'Session Controls'},
            'teams_external': {'max_points': 20, 'control_name': 'Teams External Access'},
            'sp_sharing': {'max_points': 20, 'control_name': 'SharePoint Sharing Settings'},
            'teams_retention': {'max_points': 10, 'control_name': 'Teams Data Retention'},
            'mailbox_quota': {'max_points': 25, 'control_name': 'Mailbox Quota Management'},
            'shared_mailbox_license': {'max_points': 25, 'control_name': 'Shared Mailbox License Optimization'},
            'dkim': {'max_points': 20, 'control_name': 'DKIM Email Signing'},
            'dmarc': {'max_points': 20, 'control_name': 'DMARC Policy'},
            'spf': {'max_points': 15, 'control_name': 'SPF Records'},
            'license_utilization': {'max_points': 30, 'control_name': 'License Utilization'},
            'inactive_users': {'max_points': 20, 'control_name': 'Inactive User Management'},
            'service_health': {'max_points': 20, 'control_name': 'Service Health Monitoring'},
            'usage_analytics': {'max_points': 15, 'control_name': 'Usage Analytics'},
            'security_score_tracking': {'max_points': 15, 'control_name': 'Security Score Tracking'},
        }

        self._weights = {
            'security': 35,
            'compliance': 25,
            'identity_management': 15,
            'collaboration': 15,
            'operations': 10
        }

        self._config_loaded = True

    def get_control_max_points(self, control_key: str) -> int:
        """
        Get maximum points for a control.

        Args:
            control_key: The control key (e.g., 'mfa_enforcement')

        Returns:
            Maximum points for the control, or 0 if not found
        """
        self._ensure_config_loaded()
        control = self._controls.get(control_key, {})
        return control.get('max_points', 0)

    def get_control_info(self, control_key: str) -> Optional[Dict]:
        """
        Get full control information.

        Args:
            control_key: The control key

        Returns:
            Control info dict or None if not found
        """
        self._ensure_config_loaded()
        return self._controls.get(control_key)

    def get_category_weight(self, category: str) -> int:
        """
        Get category weight percentage.

        Args:
            category: Category name (e.g., 'security', 'compliance')

        Returns:
            Weight percentage (0-100)
        """
        self._ensure_config_loaded()
        # Normalize category name
        category_key = category.lower().replace(' ', '_').replace('&', '')
        return self._weights.get(category_key, 0)

    def get_all_weights(self) -> Dict[str, int]:
        """Get all category weights"""
        self._ensure_config_loaded()
        return self._weights.copy()

    def get_controls_by_category(self, category: str) -> Dict[str, Dict]:
        """
        Get all controls for a category.

        Args:
            category: Category name

        Returns:
            Dict of control_key -> control_info
        """
        self._ensure_config_loaded()
        result = {}
        for key, control in self._controls.items():
            if control.get('category', '').lower() == category.lower():
                result[key] = control
        return result

    def reload_config(self) -> bool:
        """Force reload configuration from Excel file"""
        return self._ensure_config_loaded(force_reload=True)

    def get_config_path(self) -> Path:
        """Get the path to the config file"""
        return self.config_path

    def is_config_loaded(self) -> bool:
        """Check if config is loaded"""
        return self._config_loaded


# Global singleton instance
score_config = ScoreConfigLoader()


def get_max_points(control_key: str) -> int:
    """Convenience function to get max points for a control"""
    return score_config.get_control_max_points(control_key)


def get_weight(category: str) -> int:
    """Convenience function to get category weight"""
    return score_config.get_category_weight(category)
