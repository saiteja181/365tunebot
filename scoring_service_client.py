"""
Client for Security Scoring Service
Allows main bot to call the scoring service via REST API
"""

import requests
from typing import Dict, Optional
import os
from datetime import datetime


class ScoringServiceClient:
    """
    Client for interacting with the standalone Security Scoring Service.

    Supports both local and remote scoring service deployments.
    """

    def __init__(self, service_url: Optional[str] = None):
        """
        Initialize scoring service client.

        Args:
            service_url: URL of the scoring service. If not provided, uses environment variable
                        SCORING_SERVICE_URL or defaults to local development URL.
        """
        self.service_url = service_url or os.getenv(
            'SCORING_SERVICE_URL',
            'http://localhost:8001'
        )
        self.timeout = 60
        self.session = requests.Session()

    def health_check(self) -> Dict:
        """
        Check if the scoring service is healthy and available.

        Returns:
            Dict with health status information
        """
        try:
            response = self.session.get(
                f"{self.service_url}/health",
                timeout=5
            )
            response.raise_for_status()
            return {
                'success': True,
                'available': True,
                **response.json()
            }
        except requests.RequestException as e:
            return {
                'success': False,
                'available': False,
                'error': str(e)
            }

    def get_comprehensive_scoring(self, tenant_code: str) -> Dict:
        """
        Get comprehensive security scoring for a tenant.

        Args:
            tenant_code: The tenant code to score

        Returns:
            Dict with scoring results or error information
        """
        try:
            print(f"[SCORING CLIENT] Requesting scoring for tenant: {tenant_code}")

            response = self.session.get(
                f"{self.service_url}/api/scoring/comprehensive",
                params={'tenant_code': tenant_code},
                timeout=self.timeout
            )

            response.raise_for_status()
            result = response.json()

            print(f"[SCORING CLIENT] Received scoring response")
            return result

        except requests.Timeout:
            print(f"[SCORING CLIENT] Request timeout after {self.timeout}s")
            return {
                'success': False,
                'error': 'Scoring service request timed out',
                'timeout': True
            }

        except requests.RequestException as e:
            print(f"[SCORING CLIENT] Request failed: {str(e)}")
            return {
                'success': False,
                'error': f'Failed to connect to scoring service: {str(e)}',
                'service_url': self.service_url
            }

        except Exception as e:
            print(f"[SCORING CLIENT] Unexpected error: {str(e)}")
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }

    def get_scoring_categories(self) -> Dict:
        """
        Get available scoring categories and their weights.

        Returns:
            Dict with category information
        """
        try:
            response = self.session.get(
                f"{self.service_url}/api/scoring/categories",
                timeout=10
            )
            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            return {
                'success': False,
                'error': str(e)
            }

    def get_maturity_levels(self) -> Dict:
        """
        Get maturity level definitions.

        Returns:
            Dict with maturity level information
        """
        try:
            response = self.session.get(
                f"{self.service_url}/api/scoring/maturity-levels",
                timeout=10
            )
            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            return {
                'success': False,
                'error': str(e)
            }

    def batch_scoring(self, tenant_codes: list) -> Dict:
        """
        Get scoring for multiple tenants in a single request.

        Args:
            tenant_codes: List of tenant codes (max 10)

        Returns:
            Dict with batch scoring results
        """
        try:
            if len(tenant_codes) > 10:
                return {
                    'success': False,
                    'error': 'Maximum 10 tenants per batch request'
                }

            response = self.session.post(
                f"{self.service_url}/api/scoring/batch",
                json=tenant_codes,
                timeout=self.timeout * 2
            )
            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            return {
                'success': False,
                'error': str(e)
            }

    def __enter__(self):
        """Context manager support"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close session on context manager exit"""
        self.session.close()


class ScoringServiceWithFallback:
    """
    Scoring service client with automatic fallback to local scoring.

    If the remote scoring service is unavailable, falls back to using
    the local ComprehensiveTenantScoring class directly.
    """

    def __init__(self, service_url: Optional[str] = None):
        """
        Initialize with fallback support.

        Args:
            service_url: URL of the remote scoring service
        """
        self.client = ScoringServiceClient(service_url)
        self.use_fallback = False

        try:
            from comprehensive_scoring import ComprehensiveTenantScoring
            self.local_scorer_available = True
            self.ComprehensiveTenantScoring = ComprehensiveTenantScoring
        except ImportError:
            self.local_scorer_available = False

    def get_comprehensive_scoring(self, tenant_code: str) -> Dict:
        """
        Get scoring with automatic fallback to local implementation.

        Args:
            tenant_code: The tenant code to score

        Returns:
            Dict with scoring results
        """
        health = self.client.health_check()

        if health['available']:
            result = self.client.get_comprehensive_scoring(tenant_code)
            if result.get('success'):
                return result

        if self.local_scorer_available:
            print("[SCORING] Remote service unavailable, using local fallback")
            try:
                scorer = self.ComprehensiveTenantScoring(tenant_code=tenant_code)
                result = scorer.generate_comprehensive_score()
                result['source'] = 'local_fallback'
                return result
            except Exception as e:
                return {
                    'success': False,
                    'error': f'Both remote and local scoring failed: {str(e)}'
                }

        return {
            'success': False,
            'error': 'Scoring service unavailable and no local fallback available'
        }


if __name__ == "__main__":
    DEFAULT_TENANT_CODE = "6c657194-e896-4367-a285-478e3ef159b6"

    print("Testing Scoring Service Client...")
    print("=" * 60)

    client = ScoringServiceClient()

    print("\n1. Health Check:")
    health = client.health_check()
    print(f"   Service Available: {health.get('available')}")
    print(f"   Status: {health.get('status')}")

    if health.get('available'):
        print(f"\n2. Comprehensive Scoring:")
        result = client.get_comprehensive_scoring(DEFAULT_TENANT_CODE)
        if result.get('success'):
            print(f"   Overall Score: {result.get('overall_score')}/100")
            print(f"   Maturity Level: {result.get('maturity_level', {}).get('name')}")
        else:
            print(f"   Error: {result.get('error')}")

        print(f"\n3. Scoring Categories:")
        categories = client.get_categories()
        if categories.get('success'):
            print(f"   Categories: {len(categories.get('categories', {}))}")
    else:
        print("\nScoring service is not available.")
        print("Make sure the service is running: python scoring-service/app.py")
