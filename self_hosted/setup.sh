#!/bin/bash

# Setup script for OG Strategy Lab self-hosted deployment

# Check if docker and docker-compose are installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.template .env
    echo "IMPORTANT: Please edit the .env file and fill in your API keys and passwords."
    echo "Then run this script again."
    exit 1
fi

# Build and start the containers
echo "Building and starting OG Strategy Lab containers..."
docker-compose up -d

echo "Waiting for containers to start..."
sleep 10

echo "===================================================="
echo "OG Strategy Lab Self-Hosted Setup Complete!"
echo "===================================================="
echo ""
echo "Access your applications at:"
echo "- OG Strategy Lab: http://localhost:5000"
echo "- Superset Dashboard: http://localhost:8088"
echo "- Appsmith UI Builder: http://localhost:8080"
echo "- Uptime Kuma Monitoring: http://localhost:3001"
echo "- RocketChat (if enabled): http://localhost:3000"
echo "- Metabase (if enabled): http://localhost:3030"
echo ""
echo "For more information, check the README.md file."
echo "===================================================="
