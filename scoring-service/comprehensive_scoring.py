"""
Comprehensive Microsoft 365 Tenant Security & Compliance Scoring Framework

Implements weighted scoring across 5 major categories:
- Security (35%)
- Compliance (25%)
- Identity Management (15%)
- Collaboration & Productivity (15%)
- Operations & Governance (10%)

Total Score: 0-100 with maturity levels
"""

from config import SQL_SERVER, SQL_DATABASE, SQL_USERNAME, SQL_PASSWORD
import pyodbc
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json
from score_config_loader import score_config


class ComprehensiveTenantScoring:
    """
    Comprehensive tenant scoring system with weighted categories.
    Scores are loaded from Excel configuration file (data/security_control_scores.xlsx).
    To modify scores, edit the Excel file - no code changes needed.

    IMPORTANT: Always pass tenant_code to ensure proper data isolation.
    """

    def __init__(self, tenant_code: str = None):
        """
        Initialize scoring with tenant filtering.

        Args:
            tenant_code: The tenant code to filter all queries by.
                        REQUIRED for accurate per-tenant scoring.
        """
        self.tenant_code = tenant_code
        self.connection_string = (
            f'DRIVER={{ODBC Driver 17 for SQL Server}};'
            f'SERVER={SQL_SERVER};'
            f'DATABASE={SQL_DATABASE};'
            f'UID={SQL_USERNAME};'
            f'PWD={SQL_PASSWORD}'
        )
        # Load weights from Excel config
        self._load_weights()

        if not tenant_code:
            print("WARNING: No tenant_code provided - scoring will include ALL tenants!")

    def _load_weights(self):
        """Load category weights from Excel configuration"""
        self.WEIGHTS = score_config.get_all_weights()
        if not self.WEIGHTS:
            # Fallback to defaults if config fails
            self.WEIGHTS = {
                'security': 35,
                'compliance': 25,
                'identity_management': 15,
                'collaboration': 15,
                'operations': 10
            }

    def _get_max_points(self, control_key: str) -> int:
        """Get max points for a control from Excel config"""
        return score_config.get_control_max_points(control_key)

    def _get_tenant_filter(self, table_alias: str = None) -> str:
        """
        Get tenant filter clause for SQL queries.

        Args:
            table_alias: Optional table alias (e.g., 'ur' for UserRecords)

        Returns:
            SQL WHERE clause fragment like "TenantCode = 'xxx'" or empty string
        """
        if not self.tenant_code:
            return ""

        prefix = f"{table_alias}." if table_alias else ""
        return f"{prefix}TenantCode = '{self.tenant_code}'"

    def _add_tenant_filter(self, where_clause: str, table_alias: str = None) -> str:
        """
        Add tenant filter to existing WHERE clause.

        Args:
            where_clause: Existing WHERE conditions (without 'WHERE' keyword)
            table_alias: Optional table alias

        Returns:
            Combined WHERE clause with tenant filter
        """
        tenant_filter = self._get_tenant_filter(table_alias)
        if not tenant_filter:
            return where_clause

        if where_clause:
            return f"{tenant_filter} AND {where_clause}"
        return tenant_filter

    # Maturity levels
    MATURITY_LEVELS = {
        (0, 40): {'level': 1, 'name': 'Initial', 'description': 'Ad-hoc configuration', 'color': 'red'},
        (41, 60): {'level': 2, 'name': 'Managed', 'description': 'Basic security implemented', 'color': 'orange'},
        (61, 75): {'level': 3, 'name': 'Defined', 'description': 'Standard practices followed', 'color': 'yellow'},
        (76, 90): {'level': 4, 'name': 'Optimized', 'description': 'Best practices implemented', 'color': 'blue'},
        (91, 100): {'level': 5, 'name': 'Leading', 'description': 'Advanced security posture', 'color': 'green'}
    }

    def get_maturity_level(self, score: float) -> Dict:
        """Determine maturity level from score"""
        for (min_score, max_score), details in self.MATURITY_LEVELS.items():
            if min_score <= score <= max_score:
                return details
        return self.MATURITY_LEVELS[(0, 40)]

    # ==================== SECURITY SCORING (35%) ====================

    def score_security(self) -> Dict:
        """
        Security Category (35%)
        ├── Identity & Access (10%)
        ├── Threat Protection (10%)
        ├── Information Protection (10%)
        └── Security Monitoring (5%)
        """
        try:
            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()

            controls = []
            total_points = 0
            earned_points = 0

            # --- Identity & Access (10%) ---
            # MFA enabled for all users - CRITICAL SECURITY CONTROL
            mfa_max_points = self._get_max_points('mfa_enforcement')
            tenant_filter = self._add_tenant_filter("AccountEnabled = 1")
            cursor.execute(f"""
                SELECT
                    COUNT(*) as Total,
                    SUM(CASE WHEN IsMFADisabled = 0 THEN 1 ELSE 0 END) as MFAEnabled
                FROM UserRecords
                WHERE {tenant_filter}
            """)
            row = cursor.fetchone()
            total_users = row.Total if row.Total else 0
            mfa_enabled = row.MFAEnabled if row.MFAEnabled else 0
            mfa_coverage = (mfa_enabled / total_users * 100) if total_users > 0 else 0

            # Graduated scoring for MFA - scales based on max points from config
            if mfa_coverage >= 98:
                mfa_score = mfa_max_points
            elif mfa_coverage >= 90:
                mfa_score = int(mfa_max_points * 0.85)
            elif mfa_coverage >= 80:
                mfa_score = int(mfa_max_points * 0.70)
            elif mfa_coverage >= 70:
                mfa_score = int(mfa_max_points * 0.50)
            elif mfa_coverage >= 50:
                mfa_score = int(mfa_max_points * 0.30)
            elif mfa_coverage >= 25:
                mfa_score = int(mfa_max_points * 0.15)
            else:
                mfa_score = 0

            # Determine status with more nuanced criteria
            if mfa_score < mfa_max_points * 0.50:
                mfa_status = 'CRITICAL'
                mfa_recommendation = f'URGENT: Enable MFA for all {total_users - mfa_enabled} remaining users immediately. Current {mfa_coverage:.1f}% coverage is below minimum security standards.'
            elif mfa_score < mfa_max_points * 0.85:
                mfa_status = 'WARNING'
                mfa_recommendation = f'Enable MFA for remaining {total_users - mfa_enabled} users to reach 98%+ coverage (industry best practice).'
            else:
                mfa_status = 'PASS'
                mfa_recommendation = None

            controls.append({
                'category': 'Identity & Access',
                'control': 'MFA Enforcement',
                'points_possible': mfa_max_points,
                'points_earned': mfa_score,
                'status': mfa_status,
                'details': f'{mfa_coverage:.1f}% coverage ({mfa_enabled}/{total_users} users)',
                'data_source': 'database',
                'recommendation': mfa_recommendation
            })
            total_points += mfa_max_points
            earned_points += mfa_score

            # MFA enabled for all admin accounts
            admin_mfa_max = self._get_max_points('admin_mfa_enforcement')
            admin_filter = self._add_tenant_filter("IsAdmin = 1 AND AccountEnabled = 1")
            cursor.execute(f"""
                SELECT
                    COUNT(*) as TotalAdmins,
                    SUM(CASE WHEN IsMFADisabled = 0 THEN 1 ELSE 0 END) as AdminsMFAEnabled
                FROM UserRecords
                WHERE {admin_filter}
            """)
            row = cursor.fetchone()
            total_admins = row.TotalAdmins if row.TotalAdmins else 0
            admins_mfa = row.AdminsMFAEnabled if row.AdminsMFAEnabled else 0
            admin_mfa_coverage = (admins_mfa / total_admins * 100) if total_admins > 0 else 0

            admin_mfa_score = admin_mfa_max if admin_mfa_coverage == 100 else (
                int(admin_mfa_max * 0.67) if admin_mfa_coverage >= 80 else (
                    int(admin_mfa_max * 0.33) if admin_mfa_coverage >= 50 else 0
                )
            )

            controls.append({
                'category': 'Identity & Access',
                'control': 'Admin MFA Enforcement',
                'points_possible': admin_mfa_max,
                'points_earned': admin_mfa_score,
                'status': 'CRITICAL' if admin_mfa_score < admin_mfa_max else 'PASS',
                'details': f'{admin_mfa_coverage:.1f}% coverage ({admins_mfa}/{total_admins} admins)',
                'data_source': 'database',
                'recommendation': 'Enforce MFA for ALL admin accounts immediately' if admin_mfa_score < admin_mfa_max else None
            })
            total_points += admin_mfa_max
            earned_points += admin_mfa_score

            # Password age compliance
            pwd_max = self._get_max_points('password_age_policy')
            pwd_filter = self._add_tenant_filter("AccountEnabled = 1 AND LastPasswordChangeDateTime IS NOT NULL")
            cursor.execute(f"""
                SELECT
                    COUNT(*) as Total,
                    SUM(CASE WHEN DATEDIFF(day, LastPasswordChangeDateTime, GETDATE()) <= 90 THEN 1 ELSE 0 END) as RecentPassword
                FROM UserRecords
                WHERE {pwd_filter}
            """)
            row = cursor.fetchone()
            total_pwd = row.Total if row.Total else 0
            recent_pwd = row.RecentPassword if row.RecentPassword else 0
            pwd_compliance = (recent_pwd / total_pwd * 100) if total_pwd > 0 else 0

            pwd_score = pwd_max if pwd_compliance >= 90 else (
                int(pwd_max * 0.70) if pwd_compliance >= 70 else (
                    int(pwd_max * 0.40) if pwd_compliance >= 50 else 0
                )
            )

            controls.append({
                'category': 'Identity & Access',
                'control': 'Password Age Policy',
                'points_possible': pwd_max,
                'points_earned': pwd_score,
                'status': 'PASS' if pwd_score >= int(pwd_max * 0.70) else 'WARNING',
                'details': f'{pwd_compliance:.1f}% passwords changed in last 90 days',
                'data_source': 'database',
                'recommendation': 'Implement password expiration policy' if pwd_score < int(pwd_max * 0.70) else None
            })
            total_points += pwd_max
            earned_points += pwd_score

            # Inactive account management
            inactive_max = self._get_max_points('inactive_account_mgmt')
            inactive_filter = self._add_tenant_filter("AccountStatus != 'Active' AND IsLicensed = 1")
            cursor.execute(f"""
                SELECT
                    COUNT(*) as InactiveWithLicenses
                FROM UserRecords
                WHERE {inactive_filter}
            """)
            row = cursor.fetchone()
            inactive_licensed = row.InactiveWithLicenses if row.InactiveWithLicenses else 0

            # Score based on how few inactive accounts have licenses
            inactive_score = inactive_max if inactive_licensed == 0 else (
                int(inactive_max * 0.70) if inactive_licensed <= 5 else (
                    int(inactive_max * 0.40) if inactive_licensed <= 20 else 0
                )
            )

            controls.append({
                'category': 'Identity & Access',
                'control': 'Inactive Account Management',
                'points_possible': inactive_max,
                'points_earned': inactive_score,
                'status': 'PASS' if inactive_score >= int(inactive_max * 0.70) else 'WARNING',
                'details': f'{inactive_licensed} inactive accounts still have licenses',
                'data_source': 'database',
                'recommendation': 'Remove licenses from inactive accounts' if inactive_score < inactive_max else None
            })
            total_points += inactive_max
            earned_points += inactive_score

            # Emergency access accounts configured
            emergency_max = self._get_max_points('emergency_access')
            controls.append({
                'category': 'Identity & Access',
                'control': 'Emergency Access Accounts',
                'points_possible': emergency_max,
                'points_earned': 0,
                'status': 'REQUIRES_CONFIG',
                'details': 'Requires M365 API integration',
                'data_source': 'requires_api',
                'recommendation': 'Configure break-glass admin accounts with documented procedures'
            })
            total_points += emergency_max

            # Privileged Identity Management
            pim_max = self._get_max_points('pim')
            controls.append({
                'category': 'Identity & Access',
                'control': 'Privileged Identity Management (PIM)',
                'points_possible': pim_max,
                'points_earned': 0,
                'status': 'REQUIRES_CONFIG',
                'details': 'Requires M365 API integration',
                'data_source': 'requires_api',
                'recommendation': 'Enable Azure AD PIM for just-in-time admin access'
            })
            total_points += pim_max

            # --- Threat Protection (10%) ---
            defender_max = self._get_max_points('defender_o365')
            controls.append({
                'category': 'Threat Protection',
                'control': 'Microsoft Defender for Office 365',
                'points_possible': defender_max,
                'points_earned': 0,
                'status': 'REQUIRES_CONFIG',
                'details': 'Requires M365 API integration',
                'data_source': 'requires_api',
                'recommendation': 'Enable Defender for Office 365 P1 or P2'
            })
            total_points += defender_max

            anti_phishing_max = self._get_max_points('anti_phishing')
            controls.append({
                'category': 'Threat Protection',
                'control': 'Anti-phishing Policies',
                'points_possible': anti_phishing_max,
                'points_earned': 0,
                'status': 'REQUIRES_CONFIG',
                'details': 'Requires Security & Compliance Center API',
                'data_source': 'requires_api',
                'recommendation': 'Configure anti-phishing policies for all domains'
            })
            total_points += anti_phishing_max

            safe_links_max = self._get_max_points('safe_links')
            controls.append({
                'category': 'Threat Protection',
                'control': 'Safe Links Enabled',
                'points_possible': safe_links_max,
                'points_earned': 0,
                'status': 'REQUIRES_CONFIG',
                'details': 'Requires M365 API integration',
                'data_source': 'requires_api',
                'recommendation': 'Enable Safe Links for email and Office apps'
            })
            total_points += safe_links_max

            safe_attach_max = self._get_max_points('safe_attachments')
            controls.append({
                'category': 'Threat Protection',
                'control': 'Safe Attachments Enabled',
                'points_possible': safe_attach_max,
                'points_earned': 0,
                'status': 'REQUIRES_CONFIG',
                'details': 'Requires M365 API integration',
                'data_source': 'requires_api',
                'recommendation': 'Enable Safe Attachments with dynamic delivery'
            })
            total_points += safe_attach_max

            anti_malware_max = self._get_max_points('anti_malware')
            controls.append({
                'category': 'Threat Protection',
                'control': 'Anti-malware Policies',
                'points_possible': anti_malware_max,
                'points_earned': 0,
                'status': 'REQUIRES_CONFIG',
                'details': 'Requires Security & Compliance Center API',
                'data_source': 'requires_api',
                'recommendation': 'Configure anti-malware policies'
            })
            total_points += anti_malware_max

            zap_max = self._get_max_points('zap')
            controls.append({
                'category': 'Threat Protection',
                'control': 'Zero-hour Auto Purge (ZAP)',
                'points_possible': zap_max,
                'points_earned': 0,
                'status': 'REQUIRES_CONFIG',
                'details': 'Requires Exchange Online PowerShell',
                'data_source': 'requires_api',
                'recommendation': 'Enable ZAP for phishing and malware'
            })
            total_points += zap_max

            # --- Information Protection (10%) ---
            sens_labels_max = self._get_max_points('sensitivity_labels')
            controls.append({
                'category': 'Information Protection',
                'control': 'Sensitivity Labels',
                'points_possible': sens_labels_max,
                'points_earned': 0,
                'status': 'REQUIRES_CONFIG',
                'details': 'Requires M365 Compliance API',
                'data_source': 'requires_api',
                'recommendation': 'Create and publish sensitivity labels'
            })
            total_points += sens_labels_max

            dlp_max = self._get_max_points('dlp_policies')
            controls.append({
                'category': 'Information Protection',
                'control': 'DLP Policies for Sensitive Data',
                'points_possible': dlp_max,
                'points_earned': 0,
                'status': 'REQUIRES_CONFIG',
                'details': 'Requires M365 Compliance API',
                'data_source': 'requires_api',
                'recommendation': 'Implement DLP policies for PII, credit cards, etc.'
            })
            total_points += dlp_max

            encrypt_max = self._get_max_points('encryption_policies')
            controls.append({
                'category': 'Information Protection',
                'control': 'Encryption Policies',
                'points_possible': encrypt_max,
                'points_earned': 0,
                'status': 'REQUIRES_CONFIG',
                'details': 'Requires M365 Compliance API',
                'data_source': 'requires_api',
                'recommendation': 'Enable email encryption and OME'
            })
            total_points += encrypt_max

            aip_max = self._get_max_points('aip')
            controls.append({
                'category': 'Information Protection',
                'control': 'Azure Information Protection',
                'points_possible': aip_max,
                'points_earned': 0,
                'status': 'REQUIRES_CONFIG',
                'details': 'Requires Azure API',
                'data_source': 'requires_api',
                'recommendation': 'Integrate Azure Information Protection'
            })
            total_points += aip_max

            auto_label_max = self._get_max_points('auto_labeling')
            controls.append({
                'category': 'Information Protection',
                'control': 'Auto-labeling Rules',
                'points_possible': auto_label_max,
                'points_earned': 0,
                'status': 'REQUIRES_CONFIG',
                'details': 'Requires M365 Compliance API',
                'data_source': 'requires_api',
                'recommendation': 'Configure auto-labeling based on sensitive content'
            })
            total_points += auto_label_max

            # --- Security Monitoring (5%) ---
            audit_log_max = self._get_max_points('unified_audit_log')
            controls.append({
                'category': 'Security Monitoring',
                'control': 'Unified Audit Log Enabled',
                'points_possible': audit_log_max,
                'points_earned': 0,
                'status': 'REQUIRES_CONFIG',
                'details': 'Requires Exchange Online PowerShell',
                'data_source': 'requires_api',
                'recommendation': 'Enable unified audit logging'
            })
            total_points += audit_log_max

            alert_max = self._get_max_points('alert_policies')
            controls.append({
                'category': 'Security Monitoring',
                'control': 'Alert Policies Configured',
                'points_possible': alert_max,
                'points_earned': 0,
                'status': 'REQUIRES_CONFIG',
                'details': 'Requires M365 Compliance API',
                'data_source': 'requires_api',
                'recommendation': 'Create alert policies for security events'
            })
            total_points += alert_max

            signin_risk_max = self._get_max_points('signin_risk')
            controls.append({
                'category': 'Security Monitoring',
                'control': 'Sign-in Risk Policies',
                'points_possible': signin_risk_max,
                'points_earned': 0,
                'status': 'REQUIRES_CONFIG',
                'details': 'Requires Azure AD Identity Protection',
                'data_source': 'requires_api',
                'recommendation': 'Configure sign-in risk policies'
            })
            total_points += signin_risk_max

            conn.close()

            category_score = (earned_points / total_points * 100) if total_points > 0 else 0

            return {
                'category_name': 'Security',
                'weight_percentage': self.WEIGHTS['security'],
                'category_score': round(category_score, 2),
                'weighted_score': round(category_score * self.WEIGHTS['security'] / 100, 2),
                'total_points_possible': total_points,
                'total_points_earned': earned_points,
                'controls': controls,
                'critical_gaps': [c for c in controls if c['status'] == 'CRITICAL'],
                'requires_api_count': len([c for c in controls if c['data_source'] == 'requires_api'])
            }

        except Exception as e:
            print(f"Error in security scoring: {e}")
            return {
                'category_name': 'Security',
                'error': str(e),
                'category_score': 0,
                'weighted_score': 0
            }

    # ==================== COMPLIANCE SCORING (25%) ====================

    def score_compliance(self) -> Dict:
        """
        Compliance Category (25%)
        ├── Data Governance (10%)
        ├── Regulatory Compliance (10%)
        └── eDiscovery & Legal Hold (5%)
        """
        controls = []
        total_points = 0
        earned_points = 0

        # Most compliance controls require M365 Compliance Center API
        retention_max = self._get_max_points('retention_policies')
        controls.append({
            'category': 'Data Governance',
            'control': 'Retention Policies Configured',
            'points_possible': retention_max,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires M365 Compliance API',
            'data_source': 'requires_api',
            'recommendation': 'Configure retention policies for all workloads'
        })
        total_points += retention_max

        records_max = self._get_max_points('records_mgmt')
        controls.append({
            'category': 'Data Governance',
            'control': 'Records Management',
            'points_possible': records_max,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires M365 Compliance API',
            'data_source': 'requires_api',
            'recommendation': 'Enable records management for important content'
        })
        total_points += records_max

        info_barriers_max = self._get_max_points('info_barriers')
        controls.append({
            'category': 'Data Governance',
            'control': 'Information Barriers',
            'points_possible': info_barriers_max,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires M365 Compliance API',
            'data_source': 'requires_api',
            'recommendation': 'Configure information barriers if needed'
        })
        total_points += info_barriers_max

        comm_compliance_max = self._get_max_points('comm_compliance')
        controls.append({
            'category': 'Data Governance',
            'control': 'Communication Compliance',
            'points_possible': comm_compliance_max,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires M365 Compliance API',
            'data_source': 'requires_api',
            'recommendation': 'Enable communication compliance policies'
        })
        total_points += comm_compliance_max

        compliance_mgr_max = self._get_max_points('compliance_mgr_score')
        controls.append({
            'category': 'Regulatory Compliance',
            'control': 'Compliance Manager Score',
            'points_possible': compliance_mgr_max,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires M365 Compliance API',
            'data_source': 'requires_api',
            'recommendation': 'Achieve >70% Compliance Manager score'
        })
        total_points += compliance_mgr_max

        templates_max = self._get_max_points('compliance_templates')
        controls.append({
            'category': 'Regulatory Compliance',
            'control': 'Compliance Templates',
            'points_possible': templates_max,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires M365 Compliance API',
            'data_source': 'requires_api',
            'recommendation': 'Apply relevant compliance templates (GDPR, HIPAA, etc.)'
        })
        total_points += templates_max

        assessments_max = self._get_max_points('compliance_assessments')
        controls.append({
            'category': 'Regulatory Compliance',
            'control': 'Compliance Assessments',
            'points_possible': assessments_max,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires documentation review',
            'data_source': 'requires_api',
            'recommendation': 'Document and track compliance assessments'
        })
        total_points += assessments_max

        ediscovery_max = self._get_max_points('ediscovery')
        controls.append({
            'category': 'eDiscovery & Legal Hold',
            'control': 'eDiscovery Cases',
            'points_possible': ediscovery_max,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires M365 Compliance API',
            'data_source': 'requires_api',
            'recommendation': 'Enable eDiscovery capabilities'
        })
        total_points += ediscovery_max

        legal_hold_max = self._get_max_points('legal_hold')
        controls.append({
            'category': 'eDiscovery & Legal Hold',
            'control': 'Legal Hold Policies',
            'points_possible': legal_hold_max,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires M365 Compliance API',
            'data_source': 'requires_api',
            'recommendation': 'Configure legal hold for sensitive content'
        })
        total_points += legal_hold_max

        category_score = (earned_points / total_points * 100) if total_points > 0 else 0

        return {
            'category_name': 'Compliance',
            'weight_percentage': self.WEIGHTS['compliance'],
            'category_score': round(category_score, 2),
            'weighted_score': round(category_score * self.WEIGHTS['compliance'] / 100, 2),
            'total_points_possible': total_points,
            'total_points_earned': earned_points,
            'controls': controls,
            'requires_api_count': len([c for c in controls if c['data_source'] == 'requires_api'])
        }

    # ==================== IDENTITY MANAGEMENT SCORING (15%) ====================

    def score_identity_management(self) -> Dict:
        """
        Identity Management (15%)
        ├── Authentication (8%)
        └── Conditional Access (7%)
        """
        controls = []
        total_points = 0
        earned_points = 0

        try:
            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()

            # Guest user management
            guest_max = self._get_max_points('guest_access')
            guest_filter = self._add_tenant_filter("UserType = 'Guest'")
            cursor.execute(f"""
                SELECT
                    COUNT(*) as TotalGuests,
                    SUM(CASE WHEN AccountEnabled = 1 THEN 1 ELSE 0 END) as ActiveGuests
                FROM UserRecords
                WHERE {guest_filter}
            """)
            row = cursor.fetchone()
            total_guests = row.TotalGuests if row.TotalGuests else 0
            active_guests = row.ActiveGuests if row.ActiveGuests else 0

            # Score based on proper guest management
            guest_score = guest_max if total_guests == 0 else (
                int(guest_max * 0.75) if total_guests <= 10 else (
                    int(guest_max * 0.50) if total_guests <= 50 else int(guest_max * 0.25)
                )
            )

            controls.append({
                'category': 'Authentication',
                'control': 'Guest Access Governance',
                'points_possible': guest_max,
                'points_earned': guest_score,
                'status': 'PASS' if guest_score >= int(guest_max * 0.75) else 'WARNING',
                'details': f'{total_guests} guest accounts ({active_guests} active)',
                'data_source': 'database',
                'recommendation': 'Review and minimize guest accounts' if guest_score < int(guest_max * 0.75) else None
            })
            total_points += guest_max
            earned_points += guest_score

            # Self-service password reset
            sspr_max = self._get_max_points('sspr')
            sspr_filter = self._add_tenant_filter("AccountEnabled = 1")
            cursor.execute(f"""
                SELECT
                    COUNT(*) as Total,
                    SUM(CASE WHEN IsSSPRCapable = 1 THEN 1 ELSE 0 END) as SSPREnabled
                FROM UserRecords
                WHERE {sspr_filter}
            """)
            row = cursor.fetchone()
            total = row.Total if row.Total else 0
            sspr_enabled = row.SSPREnabled if row.SSPREnabled else 0
            sspr_coverage = (sspr_enabled / total * 100) if total > 0 else 0

            sspr_score = sspr_max if sspr_coverage >= 90 else (
                int(sspr_max * 0.75) if sspr_coverage >= 70 else (
                    int(sspr_max * 0.50) if sspr_coverage >= 50 else int(sspr_max * 0.25)
                )
            )

            controls.append({
                'category': 'Authentication',
                'control': 'Self-Service Password Reset',
                'points_possible': sspr_max,
                'points_earned': sspr_score,
                'status': 'PASS' if sspr_score >= int(sspr_max * 0.75) else 'WARNING',
                'details': f'{sspr_coverage:.1f}% users SSPR-capable',
                'data_source': 'database',
                'recommendation': 'Enable SSPR for all users' if sspr_score < sspr_max else None
            })
            total_points += sspr_max
            earned_points += sspr_score

            conn.close()

        except Exception as e:
            print(f"Error in identity management scoring: {e}")

        # Conditional Access - requires API
        block_legacy_max = self._get_max_points('block_legacy_auth')
        controls.append({
            'category': 'Conditional Access',
            'control': 'Block Legacy Authentication',
            'points_possible': block_legacy_max,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires Azure AD Graph API',
            'data_source': 'requires_api',
            'recommendation': 'Create CA policy to block legacy auth'
        })
        total_points += block_legacy_max

        ca_admin_mfa_max = self._get_max_points('ca_admin_mfa')
        controls.append({
            'category': 'Conditional Access',
            'control': 'Require MFA for Admins',
            'points_possible': ca_admin_mfa_max,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires Azure AD Graph API',
            'data_source': 'requires_api',
            'recommendation': 'Create CA policy for admin MFA'
        })
        total_points += ca_admin_mfa_max

        compliant_dev_max = self._get_max_points('compliant_devices')
        controls.append({
            'category': 'Conditional Access',
            'control': 'Require Compliant Devices',
            'points_possible': compliant_dev_max,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires Intune and Azure AD APIs',
            'data_source': 'requires_api',
            'recommendation': 'Require device compliance for access'
        })
        total_points += compliant_dev_max

        geo_max = self._get_max_points('geo_restrictions')
        controls.append({
            'category': 'Conditional Access',
            'control': 'Geographic Restrictions',
            'points_possible': geo_max,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires Azure AD Graph API',
            'data_source': 'requires_api',
            'recommendation': 'Configure named locations and geo-blocking'
        })
        total_points += geo_max

        session_max = self._get_max_points('session_controls')
        controls.append({
            'category': 'Conditional Access',
            'control': 'Session Controls',
            'points_possible': session_max,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires Azure AD Graph API',
            'data_source': 'requires_api',
            'recommendation': 'Configure session controls for cloud apps'
        })
        total_points += session_max

        category_score = (earned_points / total_points * 100) if total_points > 0 else 0

        return {
            'category_name': 'Identity Management',
            'weight_percentage': self.WEIGHTS['identity_management'],
            'category_score': round(category_score, 2),
            'weighted_score': round(category_score * self.WEIGHTS['identity_management'] / 100, 2),
            'total_points_possible': total_points,
            'total_points_earned': earned_points,
            'controls': controls,
            'requires_api_count': len([c for c in controls if c['data_source'] == 'requires_api'])
        }

    # ==================== COLLABORATION & PRODUCTIVITY SCORING (15%) ====================

    def score_collaboration(self) -> Dict:
        """
        Collaboration & Productivity (15%)
        ├── Teams/SharePoint Configuration (8%)
        └── Exchange/Email Security (7%)
        """
        controls = []
        total_points = 0
        earned_points = 0

        try:
            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()

            # Mailbox size management
            mailbox_max = self._get_max_points('mailbox_quota')
            mailbox_filter = self._add_tenant_filter("MailBoxSizeInMB IS NOT NULL AND MailBoxSizeInMB > 0")
            cursor.execute(f"""
                SELECT
                    COUNT(*) as Total,
                    AVG(CAST(MailBoxSizeInMB as FLOAT)) as AvgSize,
                    SUM(CASE WHEN MailBoxSizeInMB >= ProhibitSendQuotaMB * 0.9 THEN 1 ELSE 0 END) as NearQuota
                FROM UserRecords
                WHERE {mailbox_filter}
            """)
            row = cursor.fetchone()
            total_mailboxes = row.Total if row.Total else 0
            avg_size = row.AvgSize if row.AvgSize else 0
            near_quota = row.NearQuota if row.NearQuota else 0

            mailbox_score = mailbox_max if near_quota == 0 else (
                int(mailbox_max * 0.80) if near_quota <= 5 else (
                    int(mailbox_max * 0.60) if near_quota <= 20 else int(mailbox_max * 0.40)
                )
            )

            controls.append({
                'category': 'Exchange/Email',
                'control': 'Mailbox Quota Management',
                'points_possible': mailbox_max,
                'points_earned': mailbox_score,
                'status': 'PASS' if mailbox_score >= int(mailbox_max * 0.80) else 'WARNING',
                'details': f'{near_quota} mailboxes near quota (avg size: {avg_size:.1f}MB)',
                'data_source': 'database',
                'recommendation': 'Review and optimize mailbox sizes' if mailbox_score < mailbox_max else None
            })
            total_points += mailbox_max
            earned_points += mailbox_score

            # Shared mailbox management
            shared_mb_max = self._get_max_points('shared_mailbox_license')
            shared_filter = self._add_tenant_filter("IsSharedMailbox = 1")
            cursor.execute(f"""
                SELECT
                    COUNT(*) as SharedCount,
                    SUM(CASE WHEN IsLicensed = 1 THEN 1 ELSE 0 END) as LicensedShared
                FROM UserRecords
                WHERE {shared_filter}
            """)
            row = cursor.fetchone()
            shared_count = row.SharedCount if row.SharedCount else 0
            licensed_shared = row.LicensedShared if row.LicensedShared else 0

            # Shared mailboxes shouldn't have licenses (waste)
            shared_score = shared_mb_max if licensed_shared == 0 else (
                int(shared_mb_max * 0.60) if licensed_shared <= 2 else (
                    int(shared_mb_max * 0.40) if licensed_shared <= 5 else 0
                )
            )

            controls.append({
                'category': 'Exchange/Email',
                'control': 'Shared Mailbox License Optimization',
                'points_possible': shared_mb_max,
                'points_earned': shared_score,
                'status': 'WARNING' if licensed_shared > 0 else 'PASS',
                'details': f'{licensed_shared} shared mailboxes have unnecessary licenses',
                'data_source': 'database',
                'recommendation': 'Remove licenses from shared mailboxes (<50GB)' if licensed_shared > 0 else None
            })
            total_points += shared_mb_max
            earned_points += shared_score

            conn.close()

        except Exception as e:
            print(f"Error in collaboration scoring: {e}")

        # Teams/SharePoint - requires API
        teams_ext_max = self._get_max_points('teams_external')
        controls.append({
            'category': 'Teams/SharePoint',
            'control': 'Teams External Access Policies',
            'points_possible': teams_ext_max,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires Teams PowerShell',
            'data_source': 'requires_api',
            'recommendation': 'Configure external access policies for Teams'
        })
        total_points += teams_ext_max

        sp_sharing_max = self._get_max_points('sp_sharing')
        controls.append({
            'category': 'Teams/SharePoint',
            'control': 'SharePoint Sharing Settings',
            'points_possible': sp_sharing_max,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires SharePoint Online PowerShell',
            'data_source': 'requires_api',
            'recommendation': 'Configure secure external sharing settings'
        })
        total_points += sp_sharing_max

        teams_ret_max = self._get_max_points('teams_retention')
        controls.append({
            'category': 'Teams/SharePoint',
            'control': 'Teams Data Retention',
            'points_possible': teams_ret_max,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires M365 Compliance API',
            'data_source': 'requires_api',
            'recommendation': 'Set retention policies for Teams content'
        })
        total_points += teams_ret_max

        # Email Security
        dkim_max = self._get_max_points('dkim')
        controls.append({
            'category': 'Exchange/Email',
            'control': 'DKIM Email Signing',
            'points_possible': dkim_max,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires Exchange Online PowerShell',
            'data_source': 'requires_api',
            'recommendation': 'Enable DKIM signing for all domains'
        })
        total_points += dkim_max

        dmarc_max = self._get_max_points('dmarc')
        controls.append({
            'category': 'Exchange/Email',
            'control': 'DMARC Policy',
            'points_possible': dmarc_max,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires DNS verification',
            'data_source': 'requires_api',
            'recommendation': 'Implement DMARC policy (p=quarantine or p=reject)'
        })
        total_points += dmarc_max

        spf_max = self._get_max_points('spf')
        controls.append({
            'category': 'Exchange/Email',
            'control': 'SPF Records',
            'points_possible': spf_max,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires DNS verification',
            'data_source': 'requires_api',
            'recommendation': 'Configure SPF records for all domains'
        })
        total_points += spf_max

        category_score = (earned_points / total_points * 100) if total_points > 0 else 0

        return {
            'category_name': 'Collaboration & Productivity',
            'weight_percentage': self.WEIGHTS['collaboration'],
            'category_score': round(category_score, 2),
            'weighted_score': round(category_score * self.WEIGHTS['collaboration'] / 100, 2),
            'total_points_possible': total_points,
            'total_points_earned': earned_points,
            'controls': controls,
            'requires_api_count': len([c for c in controls if c['data_source'] == 'requires_api'])
        }

    # ==================== OPERATIONS & GOVERNANCE SCORING (10%) ====================

    def score_operations(self) -> Dict:
        """
        Operations & Governance (10%)
        ├── Tenant Management (5%)
        └── Monitoring & Reporting (5%)
        """
        controls = []
        total_points = 0
        earned_points = 0

        try:
            conn = pyodbc.connect(self.connection_string)
            cursor = conn.cursor()

            # License utilization
            license_util_max = self._get_max_points('license_utilization')
            license_filter = self._add_tenant_filter("TotalUnits > 0")
            cursor.execute(f"""
                SELECT
                    SUM(TotalUnits) as TotalUnits,
                    SUM(ConsumedUnits) as ConsumedUnits
                FROM Licenses
                WHERE {license_filter}
            """)
            row = cursor.fetchone()
            total_units = row.TotalUnits if row.TotalUnits else 0
            consumed_units = row.ConsumedUnits if row.ConsumedUnits else 0
            utilization = (consumed_units / total_units * 100) if total_units > 0 else 0

            # Score based on utilization (sweet spot 80-95%)
            if 80 <= utilization <= 95:
                util_score = license_util_max
            elif 70 <= utilization < 80 or 95 < utilization <= 100:
                util_score = int(license_util_max * 0.83)
            elif 60 <= utilization < 70:
                util_score = int(license_util_max * 0.50)
            else:
                util_score = int(license_util_max * 0.17)

            controls.append({
                'category': 'Tenant Management',
                'control': 'License Utilization Optimization',
                'points_possible': license_util_max,
                'points_earned': util_score,
                'status': 'PASS' if util_score >= int(license_util_max * 0.83) else 'WARNING',
                'details': f'{utilization:.1f}% utilization ({consumed_units}/{total_units} units)',
                'data_source': 'database',
                'recommendation': 'Optimize license allocation (target 80-95%)' if util_score < int(license_util_max * 0.83) else None
            })
            total_points += license_util_max
            earned_points += util_score

            # Stale user detection
            inactive_users_max = self._get_max_points('inactive_users')
            stale_filter = self._add_tenant_filter("DATEDIFF(day, LastSignInDateTime, GETDATE()) > 90 AND IsLicensed = 1 AND AccountEnabled = 1")
            cursor.execute(f"""
                SELECT
                    COUNT(*) as StaleUsers
                FROM UserRecords
                WHERE {stale_filter}
            """)
            row = cursor.fetchone()
            stale_users = row.StaleUsers if row.StaleUsers else 0

            stale_score = inactive_users_max if stale_users == 0 else (
                int(inactive_users_max * 0.75) if stale_users <= 10 else (
                    int(inactive_users_max * 0.50) if stale_users <= 50 else int(inactive_users_max * 0.25)
                )
            )

            controls.append({
                'category': 'Tenant Management',
                'control': 'Inactive User Management',
                'points_possible': inactive_users_max,
                'points_earned': stale_score,
                'status': 'WARNING' if stale_users > 10 else 'PASS',
                'details': f'{stale_users} users inactive 90+ days with licenses',
                'data_source': 'database',
                'recommendation': 'Review and remove licenses from stale users' if stale_users > 0 else None
            })
            total_points += inactive_users_max
            earned_points += stale_score

            conn.close()

        except Exception as e:
            print(f"Error in operations scoring: {e}")

        # Monitoring - requires API
        service_health_max = self._get_max_points('service_health')
        controls.append({
            'category': 'Monitoring & Reporting',
            'control': 'Service Health Monitoring',
            'points_possible': service_health_max,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires M365 Service Communications API',
            'data_source': 'requires_api',
            'recommendation': 'Configure service health alerts'
        })
        total_points += service_health_max

        usage_analytics_max = self._get_max_points('usage_analytics')
        controls.append({
            'category': 'Monitoring & Reporting',
            'control': 'Usage Analytics',
            'points_possible': usage_analytics_max,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires M365 Reports API',
            'data_source': 'requires_api',
            'recommendation': 'Enable usage analytics and reporting'
        })
        total_points += usage_analytics_max

        sec_score_tracking_max = self._get_max_points('security_score_tracking')
        controls.append({
            'category': 'Monitoring & Reporting',
            'control': 'Security Score Tracking',
            'points_possible': sec_score_tracking_max,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires Microsoft Graph Security API',
            'data_source': 'requires_api',
            'recommendation': 'Track Microsoft Secure Score monthly'
        })
        total_points += sec_score_tracking_max

        category_score = (earned_points / total_points * 100) if total_points > 0 else 0

        return {
            'category_name': 'Operations & Governance',
            'weight_percentage': self.WEIGHTS['operations'],
            'category_score': round(category_score, 2),
            'weighted_score': round(category_score * self.WEIGHTS['operations'] / 100, 2),
            'total_points_possible': total_points,
            'total_points_earned': earned_points,
            'controls': controls,
            'requires_api_count': len([c for c in controls if c['data_source'] == 'requires_api'])
        }

    # ==================== MAIN SCORING METHOD ====================

    def generate_comprehensive_score(self) -> Dict:
        """Generate complete tenant score across all categories"""
        try:
            print("Generating comprehensive tenant scores...")

            # Score each category
            security = self.score_security()
            compliance = self.score_compliance()
            identity = self.score_identity_management()
            collaboration = self.score_collaboration()
            operations = self.score_operations()

            # Calculate overall score
            overall_score = (
                security['weighted_score'] +
                compliance['weighted_score'] +
                identity['weighted_score'] +
                collaboration['weighted_score'] +
                operations['weighted_score']
            )

            # Determine maturity level
            maturity = self.get_maturity_level(overall_score)

            # Aggregate critical issues
            all_controls = []
            critical_gaps = []
            total_api_required = 0

            for category in [security, compliance, identity, collaboration, operations]:
                all_controls.extend(category.get('controls', []))
                critical_gaps.extend(category.get('critical_gaps', []))
                total_api_required += category.get('requires_api_count', 0)

            # Top priority actions
            priority_actions = []
            for control in all_controls:
                if control['status'] == 'CRITICAL' and control.get('recommendation'):
                    priority_actions.append({
                        'priority': 'CRITICAL',
                        'control': control['control'],
                        'category': control['category'],
                        'action': control['recommendation'],
                        'points_impact': control['points_possible']
                    })

            # Sort by impact
            priority_actions.sort(key=lambda x: x['points_impact'], reverse=True)

            return {
                'success': True,
                'generated_at': datetime.now().isoformat(),
                'overall_score': round(overall_score, 2),
                'maturity_level': maturity,
                'categories': {
                    'security': security,
                    'compliance': compliance,
                    'identity_management': identity,
                    'collaboration': collaboration,
                    'operations': operations
                },
                'summary': {
                    'total_controls_assessed': len(all_controls),
                    'total_controls_passing': len([c for c in all_controls if c['status'] == 'PASS']),
                    'critical_gaps_count': len(critical_gaps),
                    'controls_requiring_api': total_api_required,
                    'data_based_controls': len([c for c in all_controls if c['data_source'] == 'database'])
                },
                'critical_gaps': critical_gaps,
                'top_priority_actions': priority_actions[:10],
                'implementation_roadmap': {
                    'phase_1_immediate': 'Fix critical MFA gaps and inactive account issues',
                    'phase_2_short_term': 'Implement additional Azure AD and M365 API integrations',
                    'phase_3_medium_term': 'Complete compliance and threat protection configuration',
                    'phase_4_ongoing': 'Continuous monitoring and optimization'
                }
            }

        except Exception as e:
            print(f"Error generating comprehensive score: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }
