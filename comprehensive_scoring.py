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


class ComprehensiveTenantScoring:
    """
    Comprehensive tenant scoring system with weighted categories
    """

    # Category weights (must sum to 100)
    WEIGHTS = {
        'security': 35,
        'compliance': 25,
        'identity_management': 15,
        'collaboration': 15,
        'operations': 10
    }

    # Maturity levels
    MATURITY_LEVELS = {
        (0, 40): {'level': 1, 'name': 'Initial', 'description': 'Ad-hoc configuration', 'color': 'red'},
        (41, 60): {'level': 2, 'name': 'Managed', 'description': 'Basic security implemented', 'color': 'orange'},
        (61, 75): {'level': 3, 'name': 'Defined', 'description': 'Standard practices followed', 'color': 'yellow'},
        (76, 90): {'level': 4, 'name': 'Optimized', 'description': 'Best practices implemented', 'color': 'blue'},
        (91, 100): {'level': 5, 'name': 'Leading', 'description': 'Advanced security posture', 'color': 'green'}
    }

    def __init__(self):
        self.connection_string = (
            f'DRIVER={{ODBC Driver 17 for SQL Server}};'
            f'SERVER={SQL_SERVER};'
            f'DATABASE={SQL_DATABASE};'
            f'UID={SQL_USERNAME};'
            f'PWD={SQL_PASSWORD}'
        )

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
            # MFA enabled for all users (20 pts) - CRITICAL SECURITY CONTROL
            cursor.execute("""
                SELECT
                    COUNT(*) as Total,
                    SUM(CASE WHEN IsMFADisabled = 0 THEN 1 ELSE 0 END) as MFAEnabled
                FROM UserRecords
                WHERE AccountStatus = 'Active'
            """)
            row = cursor.fetchone()
            total_users = row.Total if row.Total else 0
            mfa_enabled = row.MFAEnabled if row.MFAEnabled else 0
            mfa_coverage = (mfa_enabled / total_users * 100) if total_users > 0 else 0

            # Graduated scoring for MFA - more stringent for modern security standards
            if mfa_coverage >= 98:
                mfa_score = 20
            elif mfa_coverage >= 90:
                mfa_score = 17
            elif mfa_coverage >= 80:
                mfa_score = 14
            elif mfa_coverage >= 70:
                mfa_score = 10
            elif mfa_coverage >= 50:
                mfa_score = 6
            elif mfa_coverage >= 25:
                mfa_score = 3
            else:
                mfa_score = 0

            # Determine status with more nuanced criteria
            if mfa_score < 10:
                mfa_status = 'CRITICAL'
                mfa_recommendation = f'URGENT: Enable MFA for all {total_users - mfa_enabled} remaining users immediately. Current {mfa_coverage:.1f}% coverage is below minimum security standards.'
            elif mfa_score < 17:
                mfa_status = 'WARNING'
                mfa_recommendation = f'Enable MFA for remaining {total_users - mfa_enabled} users to reach 98%+ coverage (industry best practice).'
            else:
                mfa_status = 'PASS'
                mfa_recommendation = None

            controls.append({
                'category': 'Identity & Access',
                'control': 'MFA Enforcement',
                'points_possible': 20,
                'points_earned': mfa_score,
                'status': mfa_status,
                'details': f'{mfa_coverage:.1f}% coverage ({mfa_enabled}/{total_users} users)',
                'data_source': 'database',
                'recommendation': mfa_recommendation
            })
            total_points += 20
            earned_points += mfa_score

            # MFA enabled for all admin accounts (15 pts)
            cursor.execute("""
                SELECT
                    COUNT(*) as TotalAdmins,
                    SUM(CASE WHEN IsMFADisabled = 0 THEN 1 ELSE 0 END) as AdminsMFAEnabled
                FROM UserRecords
                WHERE IsAdmin = 1 AND AccountStatus = 'Active'
            """)
            row = cursor.fetchone()
            total_admins = row.TotalAdmins if row.TotalAdmins else 0
            admins_mfa = row.AdminsMFAEnabled if row.AdminsMFAEnabled else 0
            admin_mfa_coverage = (admins_mfa / total_admins * 100) if total_admins > 0 else 0

            admin_mfa_score = 15 if admin_mfa_coverage == 100 else (
                10 if admin_mfa_coverage >= 80 else (
                    5 if admin_mfa_coverage >= 50 else 0
                )
            )

            controls.append({
                'category': 'Identity & Access',
                'control': 'Admin MFA Enforcement',
                'points_possible': 15,
                'points_earned': admin_mfa_score,
                'status': 'CRITICAL' if admin_mfa_score < 15 else 'PASS',
                'details': f'{admin_mfa_coverage:.1f}% coverage ({admins_mfa}/{total_admins} admins)',
                'data_source': 'database',
                'recommendation': 'Enforce MFA for ALL admin accounts immediately' if admin_mfa_score < 15 else None
            })
            total_points += 15
            earned_points += admin_mfa_score

            # Password age compliance (10 pts)
            cursor.execute("""
                SELECT
                    COUNT(*) as Total,
                    SUM(CASE WHEN DATEDIFF(day, LastPasswordChangeDateTime, GETDATE()) <= 90 THEN 1 ELSE 0 END) as RecentPassword
                FROM UserRecords
                WHERE AccountStatus = 'Active' AND LastPasswordChangeDateTime IS NOT NULL
            """)
            row = cursor.fetchone()
            total_pwd = row.Total if row.Total else 0
            recent_pwd = row.RecentPassword if row.RecentPassword else 0
            pwd_compliance = (recent_pwd / total_pwd * 100) if total_pwd > 0 else 0

            pwd_score = 10 if pwd_compliance >= 90 else (
                7 if pwd_compliance >= 70 else (
                    4 if pwd_compliance >= 50 else 0
                )
            )

            controls.append({
                'category': 'Identity & Access',
                'control': 'Password Age Policy',
                'points_possible': 10,
                'points_earned': pwd_score,
                'status': 'PASS' if pwd_score >= 7 else 'WARNING',
                'details': f'{pwd_compliance:.1f}% passwords changed in last 90 days',
                'data_source': 'database',
                'recommendation': 'Implement password expiration policy' if pwd_score < 7 else None
            })
            total_points += 10
            earned_points += pwd_score

            # Inactive account management (10 pts)
            cursor.execute("""
                SELECT
                    COUNT(*) as InactiveWithLicenses
                FROM UserRecords
                WHERE AccountStatus != 'Active' AND IsLicensed = 1
            """)
            row = cursor.fetchone()
            inactive_licensed = row.InactiveWithLicenses if row.InactiveWithLicenses else 0

            # Score based on how few inactive accounts have licenses
            inactive_score = 10 if inactive_licensed == 0 else (
                7 if inactive_licensed <= 5 else (
                    4 if inactive_licensed <= 20 else 0
                )
            )

            controls.append({
                'category': 'Identity & Access',
                'control': 'Inactive Account Management',
                'points_possible': 10,
                'points_earned': inactive_score,
                'status': 'PASS' if inactive_score >= 7 else 'WARNING',
                'details': f'{inactive_licensed} inactive accounts still have licenses',
                'data_source': 'database',
                'recommendation': 'Remove licenses from inactive accounts' if inactive_score < 10 else None
            })
            total_points += 10
            earned_points += inactive_score

            # Emergency access accounts configured (10 pts)
            # This requires additional data - marking as needs configuration
            controls.append({
                'category': 'Identity & Access',
                'control': 'Emergency Access Accounts',
                'points_possible': 10,
                'points_earned': 0,
                'status': 'REQUIRES_CONFIG',
                'details': 'Requires M365 API integration',
                'data_source': 'requires_api',
                'recommendation': 'Configure break-glass admin accounts with documented procedures'
            })
            total_points += 10

            # Privileged Identity Management (20 pts)
            controls.append({
                'category': 'Identity & Access',
                'control': 'Privileged Identity Management (PIM)',
                'points_possible': 20,
                'points_earned': 0,
                'status': 'REQUIRES_CONFIG',
                'details': 'Requires M365 API integration',
                'data_source': 'requires_api',
                'recommendation': 'Enable Azure AD PIM for just-in-time admin access'
            })
            total_points += 20

            # --- Threat Protection (10%) ---
            controls.append({
                'category': 'Threat Protection',
                'control': 'Microsoft Defender for Office 365',
                'points_possible': 25,
                'points_earned': 0,
                'status': 'REQUIRES_CONFIG',
                'details': 'Requires M365 API integration',
                'data_source': 'requires_api',
                'recommendation': 'Enable Defender for Office 365 P1 or P2'
            })
            total_points += 25

            controls.append({
                'category': 'Threat Protection',
                'control': 'Anti-phishing Policies',
                'points_possible': 20,
                'points_earned': 0,
                'status': 'REQUIRES_CONFIG',
                'details': 'Requires Security & Compliance Center API',
                'data_source': 'requires_api',
                'recommendation': 'Configure anti-phishing policies for all domains'
            })
            total_points += 20

            controls.append({
                'category': 'Threat Protection',
                'control': 'Safe Links Enabled',
                'points_possible': 15,
                'points_earned': 0,
                'status': 'REQUIRES_CONFIG',
                'details': 'Requires M365 API integration',
                'data_source': 'requires_api',
                'recommendation': 'Enable Safe Links for email and Office apps'
            })
            total_points += 15

            controls.append({
                'category': 'Threat Protection',
                'control': 'Safe Attachments Enabled',
                'points_possible': 15,
                'points_earned': 0,
                'status': 'REQUIRES_CONFIG',
                'details': 'Requires M365 API integration',
                'data_source': 'requires_api',
                'recommendation': 'Enable Safe Attachments with dynamic delivery'
            })
            total_points += 15

            controls.append({
                'category': 'Threat Protection',
                'control': 'Anti-malware Policies',
                'points_possible': 15,
                'points_earned': 0,
                'status': 'REQUIRES_CONFIG',
                'details': 'Requires Security & Compliance Center API',
                'data_source': 'requires_api',
                'recommendation': 'Configure anti-malware policies'
            })
            total_points += 15

            controls.append({
                'category': 'Threat Protection',
                'control': 'Zero-hour Auto Purge (ZAP)',
                'points_possible': 10,
                'points_earned': 0,
                'status': 'REQUIRES_CONFIG',
                'details': 'Requires Exchange Online PowerShell',
                'data_source': 'requires_api',
                'recommendation': 'Enable ZAP for phishing and malware'
            })
            total_points += 10

            # --- Information Protection (10%) ---
            controls.append({
                'category': 'Information Protection',
                'control': 'Sensitivity Labels',
                'points_possible': 25,
                'points_earned': 0,
                'status': 'REQUIRES_CONFIG',
                'details': 'Requires M365 Compliance API',
                'data_source': 'requires_api',
                'recommendation': 'Create and publish sensitivity labels'
            })
            total_points += 25

            controls.append({
                'category': 'Information Protection',
                'control': 'DLP Policies for Sensitive Data',
                'points_possible': 25,
                'points_earned': 0,
                'status': 'REQUIRES_CONFIG',
                'details': 'Requires M365 Compliance API',
                'data_source': 'requires_api',
                'recommendation': 'Implement DLP policies for PII, credit cards, etc.'
            })
            total_points += 25

            controls.append({
                'category': 'Information Protection',
                'control': 'Encryption Policies',
                'points_possible': 20,
                'points_earned': 0,
                'status': 'REQUIRES_CONFIG',
                'details': 'Requires M365 Compliance API',
                'data_source': 'requires_api',
                'recommendation': 'Enable email encryption and OME'
            })
            total_points += 20

            controls.append({
                'category': 'Information Protection',
                'control': 'Azure Information Protection',
                'points_possible': 15,
                'points_earned': 0,
                'status': 'REQUIRES_CONFIG',
                'details': 'Requires Azure API',
                'data_source': 'requires_api',
                'recommendation': 'Integrate Azure Information Protection'
            })
            total_points += 15

            controls.append({
                'category': 'Information Protection',
                'control': 'Auto-labeling Rules',
                'points_possible': 15,
                'points_earned': 0,
                'status': 'REQUIRES_CONFIG',
                'details': 'Requires M365 Compliance API',
                'data_source': 'requires_api',
                'recommendation': 'Configure auto-labeling based on sensitive content'
            })
            total_points += 15

            # --- Security Monitoring (5%) ---
            controls.append({
                'category': 'Security Monitoring',
                'control': 'Unified Audit Log Enabled',
                'points_possible': 40,
                'points_earned': 0,
                'status': 'REQUIRES_CONFIG',
                'details': 'Requires Exchange Online PowerShell',
                'data_source': 'requires_api',
                'recommendation': 'Enable unified audit logging'
            })
            total_points += 40

            controls.append({
                'category': 'Security Monitoring',
                'control': 'Alert Policies Configured',
                'points_possible': 30,
                'points_earned': 0,
                'status': 'REQUIRES_CONFIG',
                'details': 'Requires M365 Compliance API',
                'data_source': 'requires_api',
                'recommendation': 'Create alert policies for security events'
            })
            total_points += 30

            controls.append({
                'category': 'Security Monitoring',
                'control': 'Sign-in Risk Policies',
                'points_possible': 30,
                'points_earned': 0,
                'status': 'REQUIRES_CONFIG',
                'details': 'Requires Azure AD Identity Protection',
                'data_source': 'requires_api',
                'recommendation': 'Configure sign-in risk policies'
            })
            total_points += 30

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
        controls.append({
            'category': 'Data Governance',
            'control': 'Retention Policies Configured',
            'points_possible': 30,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires M365 Compliance API',
            'data_source': 'requires_api',
            'recommendation': 'Configure retention policies for all workloads'
        })
        total_points += 30

        controls.append({
            'category': 'Data Governance',
            'control': 'Records Management',
            'points_possible': 25,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires M365 Compliance API',
            'data_source': 'requires_api',
            'recommendation': 'Enable records management for important content'
        })
        total_points += 25

        controls.append({
            'category': 'Data Governance',
            'control': 'Information Barriers',
            'points_possible': 20,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires M365 Compliance API',
            'data_source': 'requires_api',
            'recommendation': 'Configure information barriers if needed'
        })
        total_points += 20

        controls.append({
            'category': 'Data Governance',
            'control': 'Communication Compliance',
            'points_possible': 25,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires M365 Compliance API',
            'data_source': 'requires_api',
            'recommendation': 'Enable communication compliance policies'
        })
        total_points += 25

        controls.append({
            'category': 'Regulatory Compliance',
            'control': 'Compliance Manager Score',
            'points_possible': 40,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires M365 Compliance API',
            'data_source': 'requires_api',
            'recommendation': 'Achieve >70% Compliance Manager score'
        })
        total_points += 40

        controls.append({
            'category': 'Regulatory Compliance',
            'control': 'Compliance Templates',
            'points_possible': 30,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires M365 Compliance API',
            'data_source': 'requires_api',
            'recommendation': 'Apply relevant compliance templates (GDPR, HIPAA, etc.)'
        })
        total_points += 30

        controls.append({
            'category': 'Regulatory Compliance',
            'control': 'Compliance Assessments',
            'points_possible': 30,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires documentation review',
            'data_source': 'requires_api',
            'recommendation': 'Document and track compliance assessments'
        })
        total_points += 30

        controls.append({
            'category': 'eDiscovery & Legal Hold',
            'control': 'eDiscovery Cases',
            'points_possible': 50,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires M365 Compliance API',
            'data_source': 'requires_api',
            'recommendation': 'Enable eDiscovery capabilities'
        })
        total_points += 50

        controls.append({
            'category': 'eDiscovery & Legal Hold',
            'control': 'Legal Hold Policies',
            'points_possible': 50,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires M365 Compliance API',
            'data_source': 'requires_api',
            'recommendation': 'Configure legal hold for sensitive content'
        })
        total_points += 50

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
            cursor.execute("""
                SELECT
                    COUNT(*) as TotalGuests,
                    SUM(CASE WHEN AccountStatus = 'Active' THEN 1 ELSE 0 END) as ActiveGuests
                FROM UserRecords
                WHERE UserType = 'Guest'
            """)
            row = cursor.fetchone()
            total_guests = row.TotalGuests if row.TotalGuests else 0
            active_guests = row.ActiveGuests if row.ActiveGuests else 0

            # Score based on proper guest management
            guest_score = 20 if total_guests == 0 else (
                15 if total_guests <= 10 else (
                    10 if total_guests <= 50 else 5
                )
            )

            controls.append({
                'category': 'Authentication',
                'control': 'Guest Access Governance',
                'points_possible': 20,
                'points_earned': guest_score,
                'status': 'PASS' if guest_score >= 15 else 'WARNING',
                'details': f'{total_guests} guest accounts ({active_guests} active)',
                'data_source': 'database',
                'recommendation': 'Review and minimize guest accounts' if guest_score < 15 else None
            })
            total_points += 20
            earned_points += guest_score

            # Self-service password reset
            cursor.execute("""
                SELECT
                    COUNT(*) as Total,
                    SUM(CASE WHEN IsSSPRCapable = 1 THEN 1 ELSE 0 END) as SSPREnabled
                FROM UserRecords
                WHERE AccountStatus = 'Active'
            """)
            row = cursor.fetchone()
            total = row.Total if row.Total else 0
            sspr_enabled = row.SSPREnabled if row.SSPREnabled else 0
            sspr_coverage = (sspr_enabled / total * 100) if total > 0 else 0

            sspr_score = 20 if sspr_coverage >= 90 else (
                15 if sspr_coverage >= 70 else (
                    10 if sspr_coverage >= 50 else 5
                )
            )

            controls.append({
                'category': 'Authentication',
                'control': 'Self-Service Password Reset',
                'points_possible': 20,
                'points_earned': sspr_score,
                'status': 'PASS' if sspr_score >= 15 else 'WARNING',
                'details': f'{sspr_coverage:.1f}% users SSPR-capable',
                'data_source': 'database',
                'recommendation': 'Enable SSPR for all users' if sspr_score < 20 else None
            })
            total_points += 20
            earned_points += sspr_score

            conn.close()

        except Exception as e:
            print(f"Error in identity management scoring: {e}")

        # Conditional Access - requires API
        controls.append({
            'category': 'Conditional Access',
            'control': 'Block Legacy Authentication',
            'points_possible': 20,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires Azure AD Graph API',
            'data_source': 'requires_api',
            'recommendation': 'Create CA policy to block legacy auth'
        })
        total_points += 20

        controls.append({
            'category': 'Conditional Access',
            'control': 'Require MFA for Admins',
            'points_possible': 20,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires Azure AD Graph API',
            'data_source': 'requires_api',
            'recommendation': 'Create CA policy for admin MFA'
        })
        total_points += 20

        controls.append({
            'category': 'Conditional Access',
            'control': 'Require Compliant Devices',
            'points_possible': 15,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires Intune and Azure AD APIs',
            'data_source': 'requires_api',
            'recommendation': 'Require device compliance for access'
        })
        total_points += 15

        controls.append({
            'category': 'Conditional Access',
            'control': 'Geographic Restrictions',
            'points_possible': 10,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires Azure AD Graph API',
            'data_source': 'requires_api',
            'recommendation': 'Configure named locations and geo-blocking'
        })
        total_points += 10

        controls.append({
            'category': 'Conditional Access',
            'control': 'Session Controls',
            'points_possible': 15,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires Azure AD Graph API',
            'data_source': 'requires_api',
            'recommendation': 'Configure session controls for cloud apps'
        })
        total_points += 15

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
            cursor.execute("""
                SELECT
                    COUNT(*) as Total,
                    AVG(CAST(MailBoxSizeInMB as FLOAT)) as AvgSize,
                    SUM(CASE WHEN MailBoxSizeInMB >= ProhibitSendQuotaMB * 0.9 THEN 1 ELSE 0 END) as NearQuota
                FROM UserRecords
                WHERE MailBoxSizeInMB IS NOT NULL AND MailBoxSizeInMB > 0
            """)
            row = cursor.fetchone()
            total_mailboxes = row.Total if row.Total else 0
            avg_size = row.AvgSize if row.AvgSize else 0
            near_quota = row.NearQuota if row.NearQuota else 0

            mailbox_score = 25 if near_quota == 0 else (
                20 if near_quota <= 5 else (
                    15 if near_quota <= 20 else 10
                )
            )

            controls.append({
                'category': 'Exchange/Email',
                'control': 'Mailbox Quota Management',
                'points_possible': 25,
                'points_earned': mailbox_score,
                'status': 'PASS' if mailbox_score >= 20 else 'WARNING',
                'details': f'{near_quota} mailboxes near quota (avg size: {avg_size:.1f}MB)',
                'data_source': 'database',
                'recommendation': 'Review and optimize mailbox sizes' if mailbox_score < 25 else None
            })
            total_points += 25
            earned_points += mailbox_score

            # Shared mailbox management
            cursor.execute("""
                SELECT
                    COUNT(*) as SharedCount,
                    SUM(CASE WHEN IsLicensed = 1 THEN 1 ELSE 0 END) as LicensedShared
                FROM UserRecords
                WHERE IsSharedMailbox = 1
            """)
            row = cursor.fetchone()
            shared_count = row.SharedCount if row.SharedCount else 0
            licensed_shared = row.LicensedShared if row.LicensedShared else 0

            # Shared mailboxes shouldn't have licenses (waste)
            shared_score = 25 if licensed_shared == 0 else (
                15 if licensed_shared <= 2 else (
                    10 if licensed_shared <= 5 else 0
                )
            )

            controls.append({
                'category': 'Exchange/Email',
                'control': 'Shared Mailbox License Optimization',
                'points_possible': 25,
                'points_earned': shared_score,
                'status': 'WARNING' if licensed_shared > 0 else 'PASS',
                'details': f'{licensed_shared} shared mailboxes have unnecessary licenses',
                'data_source': 'database',
                'recommendation': 'Remove licenses from shared mailboxes (<50GB)' if licensed_shared > 0 else None
            })
            total_points += 25
            earned_points += shared_score

            conn.close()

        except Exception as e:
            print(f"Error in collaboration scoring: {e}")

        # Teams/SharePoint - requires API
        controls.append({
            'category': 'Teams/SharePoint',
            'control': 'Teams External Access Policies',
            'points_possible': 20,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires Teams PowerShell',
            'data_source': 'requires_api',
            'recommendation': 'Configure external access policies for Teams'
        })
        total_points += 20

        controls.append({
            'category': 'Teams/SharePoint',
            'control': 'SharePoint Sharing Settings',
            'points_possible': 20,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires SharePoint Online PowerShell',
            'data_source': 'requires_api',
            'recommendation': 'Configure secure external sharing settings'
        })
        total_points += 20

        controls.append({
            'category': 'Teams/SharePoint',
            'control': 'Teams Data Retention',
            'points_possible': 10,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires M365 Compliance API',
            'data_source': 'requires_api',
            'recommendation': 'Set retention policies for Teams content'
        })
        total_points += 10

        # Email Security
        controls.append({
            'category': 'Exchange/Email',
            'control': 'DKIM Email Signing',
            'points_possible': 20,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires Exchange Online PowerShell',
            'data_source': 'requires_api',
            'recommendation': 'Enable DKIM signing for all domains'
        })
        total_points += 20

        controls.append({
            'category': 'Exchange/Email',
            'control': 'DMARC Policy',
            'points_possible': 20,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires DNS verification',
            'data_source': 'requires_api',
            'recommendation': 'Implement DMARC policy (p=quarantine or p=reject)'
        })
        total_points += 20

        controls.append({
            'category': 'Exchange/Email',
            'control': 'SPF Records',
            'points_possible': 15,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires DNS verification',
            'data_source': 'requires_api',
            'recommendation': 'Configure SPF records for all domains'
        })
        total_points += 15

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
            cursor.execute("""
                SELECT
                    SUM(TotalUnits) as TotalUnits,
                    SUM(ConsumedUnits) as ConsumedUnits
                FROM Licenses
                WHERE TotalUnits > 0
            """)
            row = cursor.fetchone()
            total_units = row.TotalUnits if row.TotalUnits else 0
            consumed_units = row.ConsumedUnits if row.ConsumedUnits else 0
            utilization = (consumed_units / total_units * 100) if total_units > 0 else 0

            # Score based on utilization (sweet spot 80-95%)
            if 80 <= utilization <= 95:
                util_score = 30
            elif 70 <= utilization < 80 or 95 < utilization <= 100:
                util_score = 25
            elif 60 <= utilization < 70:
                util_score = 15
            else:
                util_score = 5

            controls.append({
                'category': 'Tenant Management',
                'control': 'License Utilization Optimization',
                'points_possible': 30,
                'points_earned': util_score,
                'status': 'PASS' if util_score >= 25 else 'WARNING',
                'details': f'{utilization:.1f}% utilization ({consumed_units}/{total_units} units)',
                'data_source': 'database',
                'recommendation': 'Optimize license allocation (target 80-95%)' if util_score < 25 else None
            })
            total_points += 30
            earned_points += util_score

            # Stale user detection
            cursor.execute("""
                SELECT
                    COUNT(*) as StaleUsers
                FROM UserRecords
                WHERE DATEDIFF(day, LastSignInDateTime, GETDATE()) > 90
                AND IsLicensed = 1
                AND AccountStatus = 'Active'
            """)
            row = cursor.fetchone()
            stale_users = row.StaleUsers if row.StaleUsers else 0

            stale_score = 20 if stale_users == 0 else (
                15 if stale_users <= 10 else (
                    10 if stale_users <= 50 else 5
                )
            )

            controls.append({
                'category': 'Tenant Management',
                'control': 'Inactive User Management',
                'points_possible': 20,
                'points_earned': stale_score,
                'status': 'WARNING' if stale_users > 10 else 'PASS',
                'details': f'{stale_users} users inactive 90+ days with licenses',
                'data_source': 'database',
                'recommendation': 'Review and remove licenses from stale users' if stale_users > 0 else None
            })
            total_points += 20
            earned_points += stale_score

            conn.close()

        except Exception as e:
            print(f"Error in operations scoring: {e}")

        # Monitoring - requires API
        controls.append({
            'category': 'Monitoring & Reporting',
            'control': 'Service Health Monitoring',
            'points_possible': 20,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires M365 Service Communications API',
            'data_source': 'requires_api',
            'recommendation': 'Configure service health alerts'
        })
        total_points += 20

        controls.append({
            'category': 'Monitoring & Reporting',
            'control': 'Usage Analytics',
            'points_possible': 15,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires M365 Reports API',
            'data_source': 'requires_api',
            'recommendation': 'Enable usage analytics and reporting'
        })
        total_points += 15

        controls.append({
            'category': 'Monitoring & Reporting',
            'control': 'Security Score Tracking',
            'points_possible': 15,
            'points_earned': 0,
            'status': 'REQUIRES_CONFIG',
            'details': 'Requires Microsoft Graph Security API',
            'data_source': 'requires_api',
            'recommendation': 'Track Microsoft Secure Score monthly'
        })
        total_points += 15

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
