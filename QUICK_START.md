# Quick Start Guide

Get the trading platform up and running in 5 minutes.

## Prerequisites

- Linux (Ubuntu 20.04+)
- Python 3.10+
- Docker & Docker Compose
- 4GB RAM minimum

## Installation (One-time)

```bash
# Clone repository
git clone <repository-url>
cd trading-platform

# Run installation
./install.sh

# Review configuration
nano .env.development
```

## Daily Usage

### Start System
```bash
./run.sh
```

Access at: http://localhost:3000

### Stop System
```bash
./stop.sh
```

### Run Tests
```bash
./test.sh
```

## Common Commands

```bash
# Development mode (default)
./run.sh development

# Testing mode
./run.sh testing

# Run specific tests
./test.sh unit
./test.sh integration
./test.sh trailing-stop

# View logs
tail -f logs/api_gateway.log
tail -f logs/*.log

# Check service status
ps -p $(cat logs/api_gateway.pid)
```

## Service URLs

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API Gateway | http://localhost:5000 |
| WebSocket | http://localhost:5001 |
| Analytics | http://localhost:5002 |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |
| InfluxDB | http://localhost:8086 |

## Troubleshooting

### Services won't start
```bash
# Check Docker
docker-compose ps

# Check logs
tail -f logs/*.log

# Restart infrastructure
docker-compose restart
```

### Database issues
```bash
# Run migrations
source venv/bin/activate
alembic upgrade head
```

### Port conflicts
```bash
# Check ports
sudo netstat -tulpn | grep -E '5000|5001|5002'

# Update .env.development with different ports
```

## Next Steps

1. Read [SCRIPTS_GUIDE.md](SCRIPTS_GUIDE.md) for detailed documentation
2. Review [README.md](README.md) for project overview
3. Check [TESTING_ENVIRONMENT.md](TESTING_ENVIRONMENT.md) for testing guide
4. See [API_POSITION_ENDPOINTS.md](API_POSITION_ENDPOINTS.md) for API docs

## Support

- Check logs: `logs/` directory
- Review: [SCRIPTS_GUIDE.md](SCRIPTS_GUIDE.md) troubleshooting section
- Create issue with error details

---

**Happy Trading! 🚀**
