"""
Standalone Security Scoring Service
A microservice for Microsoft 365 tenant security and compliance scoring.

Designed for independent deployment to Azure App Service.
Provides RESTful API for comprehensive security assessment.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import uvicorn
from datetime import datetime
import os
import sys

# Add parent directory to path to import shared modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from comprehensive_scoring import ComprehensiveTenantScoring
from score_config_loader import score_config

app = FastAPI(
    title="365 Tune Bot - Security Scoring Service",
    description="Comprehensive Microsoft 365 tenant security and compliance scoring API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    timestamp: str


class ScoringRequest(BaseModel):
    tenant_code: str


@app.get("/", response_model=HealthResponse)
async def root():
    """Service health check and information"""
    return {
        "status": "healthy",
        "service": "Security Scoring Service",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Detailed health check endpoint"""
    return {
        "status": "healthy",
        "service": "Security Scoring Service",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/dashboard")
async def dashboard():
    """Serve the standalone dashboard UI"""
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        raise HTTPException(status_code=404, detail="Dashboard not found")


@app.get("/api/scoring/comprehensive")
async def get_comprehensive_scoring(
    tenant_code: str = Query(..., description="Tenant code for scoring analysis")
):
    """
    Get comprehensive security and compliance scoring for a tenant.

    Args:
        tenant_code: The unique identifier for the tenant to analyze

    Returns:
        Detailed scoring report including:
        - Overall security score (0-100)
        - Maturity level assessment
        - Category breakdowns (security, compliance, identity, etc.)
        - Gap analysis
        - Actionable recommendations
    """
    try:
        if not tenant_code:
            raise HTTPException(
                status_code=400,
                detail="tenant_code parameter is required"
            )

        print(f"[SCORING SERVICE] Generating comprehensive scoring for tenant: {tenant_code}")

        scorer = ComprehensiveTenantScoring(tenant_code=tenant_code)
        result = scorer.generate_comprehensive_score()

        result['tenant_code'] = tenant_code
        result['generated_at'] = datetime.now().isoformat()

        print(f"[SCORING SERVICE] Scoring completed successfully")
        if result.get('success'):
            print(f"  - Overall Score: {result.get('overall_score', 0)}/100")
            print(f"  - Maturity Level: {result.get('maturity_level', {}).get('name', 'Unknown')}")

        return result

    except Exception as e:
        print(f"[ERROR] Scoring generation failed: {str(e)}")
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate scoring: {str(e)}"
        )


@app.get("/api/scoring/categories")
async def get_scoring_categories():
    """
    Get available scoring categories and their weights.

    Returns:
        List of scoring categories with their respective weights
    """
    try:
        weights = score_config.get_all_weights()

        categories = {
            'security': {
                'name': 'Security',
                'weight': weights.get('security', 35),
                'description': 'MFA, threat protection, information protection, monitoring'
            },
            'compliance': {
                'name': 'Compliance',
                'weight': weights.get('compliance', 25),
                'description': 'Data governance, regulatory compliance, eDiscovery'
            },
            'identity_management': {
                'name': 'Identity Management',
                'weight': weights.get('identity_management', 15),
                'description': 'Guest access, SSPR, conditional access'
            },
            'collaboration': {
                'name': 'Collaboration & Productivity',
                'weight': weights.get('collaboration', 15),
                'description': 'Teams/SharePoint, mailbox management, email security'
            },
            'operations': {
                'name': 'Operations & Governance',
                'weight': weights.get('operations', 10),
                'description': 'License utilization, stale user detection, monitoring'
            }
        }

        return {
            "success": True,
            "categories": categories,
            "total_weight": sum(cat['weight'] for cat in categories.values())
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve categories: {str(e)}"
        )


@app.get("/api/scoring/maturity-levels")
async def get_maturity_levels():
    """
    Get information about maturity level scoring ranges.

    Returns:
        Maturity level definitions and score ranges
    """
    levels = [
        {
            'level': 1,
            'name': 'Initial',
            'range': '0-40',
            'color': 'red',
            'description': 'Ad-hoc processes, minimal security controls'
        },
        {
            'level': 2,
            'name': 'Managed',
            'range': '41-60',
            'color': 'orange',
            'description': 'Basic security controls in place, some documentation'
        },
        {
            'level': 3,
            'name': 'Defined',
            'range': '61-75',
            'color': 'yellow',
            'description': 'Documented processes, consistent security practices'
        },
        {
            'level': 4,
            'name': 'Optimized',
            'range': '76-90',
            'color': 'blue',
            'description': 'Proactive security, continuous improvement'
        },
        {
            'level': 5,
            'name': 'Leading',
            'range': '91-100',
            'color': 'green',
            'description': 'Industry-leading security posture, innovation'
        }
    ]

    return {
        "success": True,
        "maturity_levels": levels
    }


@app.post("/api/scoring/batch")
async def batch_scoring(tenant_codes: list[str]):
    """
    Generate scoring for multiple tenants in a single request.

    Args:
        tenant_codes: List of tenant codes to analyze

    Returns:
        Scoring results for all requested tenants
    """
    try:
        if not tenant_codes or len(tenant_codes) == 0:
            raise HTTPException(
                status_code=400,
                detail="At least one tenant_code is required"
            )

        if len(tenant_codes) > 10:
            raise HTTPException(
                status_code=400,
                detail="Maximum 10 tenants per batch request"
            )

        results = []
        for tenant_code in tenant_codes:
            try:
                scorer = ComprehensiveTenantScoring(tenant_code=tenant_code)
                result = scorer.generate_comprehensive_score()
                result['tenant_code'] = tenant_code
                results.append(result)
            except Exception as e:
                results.append({
                    'tenant_code': tenant_code,
                    'success': False,
                    'error': str(e)
                })

        return {
            "success": True,
            "total_tenants": len(tenant_codes),
            "results": results,
            "generated_at": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Batch scoring failed: {str(e)}"
        )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8001))
    print(f"Starting Security Scoring Service on port {port}...")
    print(f"API Documentation: http://localhost:{port}/docs")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
