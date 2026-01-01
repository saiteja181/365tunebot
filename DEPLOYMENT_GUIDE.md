# 365 Tune Bot - Deployment Guide

## New Features Implemented

### 1. Proactive Insights & Recommendations Engine
Automated analysis and optimization detection system that provides actionable insights.

### 2. Standalone Security Scoring Service
Microservice architecture for independent deployment and scaling of security assessment.

---

## Feature 1: Proactive Insights Engine

### Overview
The Proactive Insights Engine automatically analyzes your Microsoft 365 tenant data to detect:
- Cost optimization opportunities
- Security gaps and vulnerabilities
- License utilization issues
- Activity anomalies
- Compliance concerns

### What's Included

#### Backend Components
- `proactive_insights_engine.py` - Core analysis engine
- FastAPI endpoints in `real_fastapi.py`:
  - `GET /api/insights/proactive` - Comprehensive insights report
  - `GET /api/insights/alerts` - Critical alerts requiring attention
  - `GET /api/insights/category/{category}` - Category-specific insights

#### Frontend Components
- `react-chart-app/src/components/ProactiveInsights.js` - React UI component
- Integrated into Analytics tab in `App.js`

### Features

#### Cost Optimization Detection
- Inactive users with active licenses
- Disabled accounts still holding licenses
- Email inactive users
- Estimated monthly savings calculations

#### Security Gap Analysis
- MFA enforcement tracking
- Stale guest accounts
- Accounts never used
- Security compliance metrics

#### License Utilization
- License allocation analysis
- Under-utilized license detection
- Usage rate monitoring

#### Activity Anomalies
- Department engagement analysis
- Meeting collaboration patterns
- Unusual activity detection

#### Compliance Monitoring
- Guest user governance
- Access control compliance
- Policy adherence tracking

### Health Score Calculation
- Overall tenant health score (0-100)
- Grade system (A-F)
- Automatic deductions based on severity
- Visual dashboard representation

### Using the Feature

#### Access via Web UI
1. Navigate to the Analytics tab
2. View "Proactive Insights & Recommendations" section
3. Filter by category or view all insights
4. Review priority actions

#### API Access
```bash
# Get comprehensive insights
curl "http://localhost:8000/api/insights/proactive?tenant_code=YOUR_TENANT_CODE"

# Get critical alerts
curl "http://localhost:8000/api/insights/alerts?tenant_code=YOUR_TENANT_CODE"

# Get category-specific insights
curl "http://localhost:8000/api/insights/category/cost_optimization?tenant_code=YOUR_TENANT_CODE"
```

#### Programmatic Access
```python
from proactive_insights_engine import ProactiveInsightsEngine

engine = ProactiveInsightsEngine(tenant_code="YOUR_TENANT_CODE")
report = engine.generate_comprehensive_report()

print(f"Health Score: {report['health_score']['score']}/100")
print(f"Total Insights: {report['summary']['total_insights']}")
print(f"Potential Savings: ${report['summary']['total_potential_monthly_savings']}/month")
```

### Configuration

#### Thresholds (in `proactive_insights_engine.py`)
```python
THRESHOLDS = {
    'inactive_days': 90,
    'mfa_target_percent': 95,
    'license_utilization_low': 70,
    'license_utilization_high': 95,
    'anomaly_stddev_multiplier': 2.5,
    'stale_guest_days': 180,
    'email_inactive_days': 30,
    'meeting_inactive_days': 60,
    'cost_per_unused_license': 12.0
}
```

Modify these values to adjust sensitivity and detection criteria.

---

## Feature 2: Standalone Security Scoring Service

### Overview
The security scoring system has been extracted into a standalone microservice that can be deployed independently to Azure App Service or any container platform.

### Architecture

```
Main Bot (Port 8000)              Scoring Service (Port 8001)
┌────────────────────┐           ┌──────────────────────────┐
│ - Chat Interface   │           │ - Scoring Engine         │
│ - Dashboard        │◄─────────►│ - Gap Analysis           │
│ - Insights         │   HTTP    │ - Recommendations        │
│ - License Analytics│   API     │ - Maturity Assessment    │
└────────────────────┘           └──────────────────────────┘
         │                                  │
         └──────────────┬───────────────────┘
                        │
                ┌───────▼────────┐
                │  SQL Database  │
                └────────────────┘
```

### Service Structure

```
scoring-service/
├── app.py                      # FastAPI application
├── config.py                   # Service configuration
├── requirements.txt            # Python dependencies
├── comprehensive_scoring.py    # Scoring engine (copied)
├── score_config_loader.py      # Config loader (copied)
├── data/                       # Scoring configuration
│   └── security_control_scores.xlsx
├── .env.example               # Environment template
├── Dockerfile                 # Container definition
├── .dockerignore             # Docker ignore rules
└── azure/                    # Azure deployment files
    ├── startup.sh           # Startup script
    └── web.config          # IIS configuration
```

### API Endpoints

#### Health Check
```bash
GET /health
GET /
```

#### Comprehensive Scoring
```bash
GET /api/scoring/comprehensive?tenant_code=TENANT_CODE

Response:
{
  "success": true,
  "overall_score": 75.5,
  "maturity_level": {
    "level": 3,
    "name": "Defined",
    "color": "yellow"
  },
  "categories": {...},
  "summary": {...},
  "tenant_code": "...",
  "generated_at": "2025-12-26T..."
}
```

#### Get Categories
```bash
GET /api/scoring/categories

Response:
{
  "success": true,
  "categories": {
    "security": {"name": "Security", "weight": 35, ...},
    ...
  }
}
```

#### Get Maturity Levels
```bash
GET /api/scoring/maturity-levels
```

#### Batch Scoring
```bash
POST /api/scoring/batch
Content-Type: application/json

["tenant1", "tenant2", "tenant3"]
```

### Deployment Options

#### Option 1: Local Development

1. Navigate to scoring service directory:
```bash
cd scoring-service
```

2. Create `.env` file:
```bash
cp .env.example .env
# Edit .env with your SQL Server credentials
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the service:
```bash
python app.py
```

Service will be available at `http://localhost:8001`

#### Option 2: Docker Container

1. Build the image:
```bash
cd scoring-service
docker build -t scoring-service:latest .
```

2. Run the container:
```bash
docker run -d \
  -p 8001:8001 \
  -e SQL_SERVER=your_server.database.windows.net \
  -e SQL_DATABASE=your_database \
  -e SQL_USERNAME=your_username \
  -e SQL_PASSWORD=your_password \
  --name scoring-service \
  scoring-service:latest
```

#### Option 3: Azure App Service (Recommended)

##### Prerequisites
- Azure CLI installed
- Azure subscription
- Resource group created

##### Deployment Steps

1. **Create App Service Plan**
```bash
az appservice plan create \
  --name scoring-service-plan \
  --resource-group your-resource-group \
  --sku B1 \
  --is-linux
```

2. **Create Web App**
```bash
az webapp create \
  --name your-scoring-service \
  --resource-group your-resource-group \
  --plan scoring-service-plan \
  --runtime "PYTHON|3.11"
```

3. **Configure Environment Variables**
```bash
az webapp config appsettings set \
  --name your-scoring-service \
  --resource-group your-resource-group \
  --settings \
    SQL_SERVER="your_server.database.windows.net" \
    SQL_DATABASE="your_database" \
    SQL_USERNAME="your_username" \
    SQL_PASSWORD="your_password" \
    ENVIRONMENT="production" \
    LOG_LEVEL="INFO"
```

4. **Deploy Code**

Option A: Deploy from local directory
```bash
cd scoring-service
az webapp up \
  --name your-scoring-service \
  --resource-group your-resource-group
```

Option B: Deploy from GitHub
```bash
az webapp deployment source config \
  --name your-scoring-service \
  --resource-group your-resource-group \
  --repo-url https://github.com/your-repo/scoring-service \
  --branch main \
  --manual-integration
```

5. **Configure Startup Command**
```bash
az webapp config set \
  --name your-scoring-service \
  --resource-group your-resource-group \
  --startup-file "python app.py"
```

6. **Verify Deployment**
```bash
curl https://your-scoring-service.azurewebsites.net/health
```

##### Configure Firewall
If using Azure SQL Database, add App Service IP to firewall:

```bash
# Get outbound IPs
az webapp show \
  --name your-scoring-service \
  --resource-group your-resource-group \
  --query outboundIpAddresses

# Add to SQL firewall in Azure Portal
```

### Integrating with Main Bot

#### Option 1: Direct Client Usage

Update `real_fastapi.py` to use the scoring service client:

```python
from scoring_service_client import ScoringServiceClient

# Initialize client
scoring_client = ScoringServiceClient(
    service_url="https://your-scoring-service.azurewebsites.net"
)

# Use in endpoint
@app.get("/api/scoring/comprehensive")
async def get_comprehensive_scoring(tenant_code: Optional[str] = None):
    tenant_code = tenant_code or DEFAULT_TENANT_CODE
    result = scoring_client.get_comprehensive_scoring(tenant_code)
    return result
```

#### Option 2: Client with Fallback

For production resilience, use the fallback client:

```python
from scoring_service_client import ScoringServiceWithFallback

# Initialize with fallback
scoring = ScoringServiceWithFallback(
    service_url="https://your-scoring-service.azurewebsites.net"
)

# Automatically falls back to local scoring if service unavailable
result = scoring.get_comprehensive_scoring(tenant_code)
```

#### Environment Variables

Add to main bot's `.env`:
```bash
SCORING_SERVICE_URL=https://your-scoring-service.azurewebsites.net
```

### Monitoring and Logging

#### Azure Application Insights

1. Enable Application Insights:
```bash
az webapp config appsettings set \
  --name your-scoring-service \
  --resource-group your-resource-group \
  --settings \
    APPINSIGHTS_INSTRUMENTATIONKEY="your-key"
```

2. View logs:
```bash
az webapp log tail \
  --name your-scoring-service \
  --resource-group your-resource-group
```

#### Health Monitoring

Set up health check endpoint monitoring:
```bash
az webapp config set \
  --name your-scoring-service \
  --resource-group your-resource-group \
  --health-check-path "/health"
```

### Scaling

#### Vertical Scaling (Upgrade Plan)
```bash
az appservice plan update \
  --name scoring-service-plan \
  --resource-group your-resource-group \
  --sku P1V2
```

#### Horizontal Scaling (Add Instances)
```bash
az appservice plan update \
  --name scoring-service-plan \
  --resource-group your-resource-group \
  --number-of-workers 3
```

#### Auto-scaling
```bash
az monitor autoscale create \
  --resource-group your-resource-group \
  --resource your-scoring-service \
  --resource-type Microsoft.Web/sites \
  --name scoring-autoscale \
  --min-count 1 \
  --max-count 5 \
  --count 2
```

---

## Testing

### Test Proactive Insights

1. Start main bot:
```bash
python real_fastapi.py
```

2. Access endpoints:
```bash
# Test insights generation
curl "http://localhost:8000/api/insights/proactive"

# Test alerts
curl "http://localhost:8000/api/insights/alerts"
```

3. Open browser: `http://localhost:3000` > Analytics tab

### Test Scoring Service

1. Start scoring service:
```bash
cd scoring-service
python app.py
```

2. Test endpoints:
```bash
# Health check
curl http://localhost:8001/health

# Get scoring
curl "http://localhost:8001/api/scoring/comprehensive?tenant_code=6c657194-e896-4367-a285-478e3ef159b6"
```

3. Test client:
```bash
python scoring_service_client.py
```

---

## Troubleshooting

### Proactive Insights Issues

**Problem**: No insights generated
- Check database connection
- Verify tenant_code is correct
- Check SQL Server firewall rules

**Problem**: API timeout
- Increase timeout in axios requests
- Check database query performance
- Consider adding caching

### Scoring Service Issues

**Problem**: Service won't start
- Check Python version (3.11+)
- Verify all dependencies installed
- Check environment variables set

**Problem**: Database connection failed
- Verify SQL Server credentials
- Check firewall rules
- Test connection with pyodbc directly

**Problem**: Azure deployment failed
- Check deployment logs: `az webapp log tail`
- Verify startup command configured
- Check App Service plan has sufficient resources

---

## Best Practices

### Security
1. Use managed identities for Azure resources
2. Store secrets in Azure Key Vault
3. Enable HTTPS only
4. Implement rate limiting
5. Add authentication/authorization

### Performance
1. Enable caching for scoring results (TTL: 5-10 minutes)
2. Use connection pooling for database
3. Monitor query performance
4. Implement circuit breakers for external calls

### Reliability
1. Use fallback client for scoring service
2. Implement retry logic with exponential backoff
3. Set up health checks and alerts
4. Monitor service availability
5. Have rollback plan ready

### Cost Optimization
1. Use B-series App Service plans for dev/test
2. Scale down during off-hours
3. Monitor resource utilization
4. Use reserved instances for production

---

## Support

For issues or questions:
1. Check logs: `az webapp log tail`
2. Review API documentation: `http://your-service/docs`
3. Test with provided client scripts
4. Check database connectivity and credentials

---

## Next Steps

### Recommended Enhancements

1. **Scheduled Insights Reports**
   - Email daily/weekly summaries
   - Teams/Slack notifications
   - Automated alerts for critical issues

2. **Historical Trending**
   - Track metrics over time
   - Compare period-over-period
   - Identify trends and patterns

3. **Custom Thresholds**
   - Allow per-tenant configuration
   - User-defined alert rules
   - Configurable sensitivity levels

4. **API Authentication**
   - Add JWT/OAuth2 authentication
   - API key management
   - Rate limiting per client

5. **Advanced Analytics**
   - Predictive modeling
   - Anomaly detection with ML
   - Benchmark against industry standards
