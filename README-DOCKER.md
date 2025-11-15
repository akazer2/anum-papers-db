# Docker Deployment Guide

This guide explains how to deploy the Anum Papers Database application using Docker on your home server.

## Prerequisites

- Docker and Docker Compose installed on your server
- GROBID service already running (either in Docker or on the host)
- Port 8501 available (other Streamlit app uses 8050)

## Quick Start

1. **Create data directory** (for database persistence):
   ```bash
   mkdir -p data
   ```

2. **Build and start the application**:
   ```bash
   docker-compose up -d --build
   ```

3. **Access the application**:
   Open your browser to `http://your-server-ip:8501`

## Configuration

### Environment Variables

You can configure the application using environment variables in `docker-compose.yml`:

- **DATABASE_PATH**: Path to SQLite database file (default: `/app/data/anum_papers.db`)
- **GROBID_URL**: URL to GROBID service (default: `http://grobid:8070`)

### GROBID Connection

Since GROBID is already running on your server, you need to configure how the app connects to it:

#### Option 1: GROBID on Same Docker Network
If GROBID is running in Docker on the same network, use the service name:
```yaml
environment:
  - GROBID_URL=http://grobid:8070
```

#### Option 2: GROBID on Host Network
If GROBID is running on the host (not in Docker), use:
```yaml
environment:
  - GROBID_URL=http://host.docker.internal:8070
```

#### Option 3: GROBID on Specific IP
If you know the IP address:
```yaml
environment:
  - GROBID_URL=http://192.168.20.139:8070
```

#### Option 4: Use Host Network Mode
You can also run the app with host network mode to access GROBID on localhost:
```yaml
services:
  app:
    network_mode: host
```

Then set:
```yaml
environment:
  - GROBID_URL=http://localhost:8070
```

## Docker Compose Commands

### Build the image:
```bash
docker-compose build
```

### Start the application:
```bash
docker-compose up -d
```

### View logs:
```bash
docker-compose logs -f
```

### Stop the application:
```bash
docker-compose down
```

### Restart the application:
```bash
docker-compose restart
```

### Update and rebuild:
```bash
docker-compose down
docker-compose up -d --build
```

## Database Management

### Database Location
The database is stored in the `./data/` directory on your host machine, which is mounted as a volume in the container. This ensures data persistence across container restarts.

### Database Initialization
The application will automatically initialize the database on first run if it doesn't exist. The schema is loaded from `schema.sql`.

### Backup Database
To backup the database:
```bash
cp data/anum_papers.db data/anum_papers.db.backup
```

### Restore Database
To restore from backup:
```bash
cp data/anum_papers.db.backup data/anum_papers.db
docker-compose restart
```

## Troubleshooting

### Application won't start
1. Check logs: `docker-compose logs app`
2. Verify port 8501 is not in use: `netstat -tuln | grep 8501`
3. Check Docker is running: `docker ps`

### Can't connect to GROBID
1. Verify GROBID is running: `curl http://grobid-url:8070/api/isalive`
2. Check network configuration in `docker-compose.yml`
3. Try accessing GROBID from within the container:
   ```bash
   docker-compose exec app curl http://grobid-url:8070/api/isalive
   ```

### Database errors
1. Check file permissions on `./data/` directory
2. Verify database file exists: `ls -la data/anum_papers.db`
3. Check container logs for initialization errors

### Port conflicts
If port 8501 is already in use, change it in `docker-compose.yml`:
```yaml
ports:
  - "8502:8501"  # Use 8502 on host, 8501 in container
```

## Production Considerations

### Security
- Consider using a reverse proxy (nginx, traefik) in front of the application
- Set up SSL/TLS certificates for HTTPS
- Restrict network access as needed

### Performance
- Monitor resource usage: `docker stats anum-papers-db`
- Adjust memory limits if needed in `docker-compose.yml`

### Backups
- Set up automated backups of the `./data/` directory
- Consider using a volume backup solution

### Updates
- Pull latest code changes
- Rebuild and restart: `docker-compose up -d --build`

## File Structure

```
anum-papers-db/
├── Dockerfile              # Container image definition
├── docker-compose.yml      # Service orchestration
├── .dockerignore          # Files to exclude from build
├── app.py                 # Streamlit application
├── db.py                  # Database layer
├── models.py              # Data models
├── citation_parser.py      # Citation parsing logic
├── schema.sql             # Database schema
├── requirements.txt       # Python dependencies
├── data/                  # Database storage (created on first run)
│   └── anum_papers.db    # SQLite database file
└── README-DOCKER.md       # This file
```

## Support

For issues or questions:
1. Check application logs: `docker-compose logs -f app`
2. Verify GROBID connectivity
3. Check database file permissions and existence

