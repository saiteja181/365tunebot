# Security Scoring Service

Standalone microservice for Microsoft 365 tenant security and compliance scoring.

## Overview

This service provides comprehensive security posture assessment across 5 weighted categories:
- Security (35%)
- Compliance (25%)
- Identity Management (15%)
- Collaboration & Productivity (15%)
- Operations & Governance (10%)

## Quick Start

### Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your database credentials
```

3. Run the service:
```bash
python app.py
```

Service will start on `http://localhost:8001`

### API Documentation

Once running, visit:
- Swagger UI: `http://localhost:8001/docs`
- ReDoc: `http://localhost:8001/redoc`

## API Endpoints

### Health Check
```bash
GET /health
```

### Comprehensive Scoring
```bash
GET /api/scoring/comprehensive?tenant_code=YOUR_TENANT_CODE
```

### Scoring Categories
```bash
GET /api/scoring/categories
```

### Maturity Levels
```bash
GET /api/scoring/maturity-levels
```

### Batch Scoring
```bash
POST /api/scoring/batch
Content-Type: application/json

["tenant1", "tenant2", "tenant3"]
```

## Docker Deployment

Build and run with Docker:

```bash
docker build -t scoring-service .
docker run -d -p 8001:8001 \
  -e SQL_SERVER=your_server \
  -e SQL_DATABASE=your_db \
  -e SQL_USERNAME=your_user \
  -e SQL_PASSWORD=your_password \
  scoring-service
```

## Azure App Service Deployment

See `../DEPLOYMENT_GUIDE.md` for detailed Azure deployment instructions.

Quick deploy:

```bash
az webapp up \
  --name your-scoring-service \
  --resource-group your-rg \
  --runtime "PYTHON|3.11"
```

## Configuration

### Environment Variables

Required:
- `SQL_SERVER` - SQL Server hostname
- `SQL_DATABASE` - Database name
- `SQL_USERNAME` - Database username
- `SQL_PASSWORD` - Database password

Optional:
- `PORT` - Service port (default: 8001)
- `ENVIRONMENT` - Environment name (default: development)
- `LOG_LEVEL` - Logging level (default: INFO)

### Scoring Configuration

Modify scoring weights and control points in:
- `data/security_control_scores.xlsx`

No code changes needed. The service automatically loads configuration from Excel.

## Database Requirements

The service requires access to the following tables:
- `UserRecords` - User activity and license data
- `Licenses` - License allocation and consumption

All queries are automatically filtered by `TenantCode` for multi-tenant support.

## Security

### SQL Injection Protection
- Parameterized queries used throughout
- Input validation on all endpoints
- Tenant isolation enforced

### Authentication
Currently uses simple query parameters. For production:
- Implement JWT authentication
- Add API key validation
- Use managed identities for Azure resources

## Monitoring

### Health Checks
The `/health` endpoint provides service status for monitoring tools.

### Logging
Logs include:
- Request/response timing
- Tenant code being scored
- Score calculations
- Error details

### Metrics
Track these metrics for production:
- Response time
- Success rate
- Tenant scores over time
- Database query performance

## Troubleshooting

### Service Won't Start
- Check Python version (3.11+ required)
- Verify all dependencies installed
- Ensure environment variables set

### Database Connection Failed
- Verify SQL Server credentials
- Check firewall rules
- Test with: `pip install pyodbc && python -c "import pyodbc; print(pyodbc.drivers())"`

### Slow Response Times
- Check database query performance
- Monitor SQL Server DTU usage
- Consider adding caching layer
- Review network latency to database

## Development

### Project Structure
```
scoring-service/
├── app.py                      # FastAPI application
├── config.py                   # Configuration loading
├── comprehensive_scoring.py    # Scoring engine
├── score_config_loader.py      # Excel config loader
├── requirements.txt            # Dependencies
├── Dockerfile                  # Container definition
└── data/                       # Configuration files
    └── security_control_scores.xlsx
```

### Adding New Controls

1. Open `data/security_control_scores.xlsx`
2. Add control definition with weight
3. Implement check in `comprehensive_scoring.py`
4. No service restart needed (config loaded per request)

### Testing

```python
# Test the service
import requests

response = requests.get(
    'http://localhost:8001/api/scoring/comprehensive',
    params={'tenant_code': 'your-tenant-code'}
)

print(response.json())
```

## License

Part of the 365 Tune Bot project.

## Support

For issues or questions, refer to the main project documentation.
