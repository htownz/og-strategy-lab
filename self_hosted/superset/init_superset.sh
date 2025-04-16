#!/bin/bash

# Wait for Superset to be available
echo "Waiting for Superset to start..."
until $(curl --output /dev/null --silent --head --fail http://superset:8088); do
    echo "Waiting for Superset to start..."
    sleep 5
done

# Create an admin user
echo "Creating admin user..."
superset fab create-admin \
    --username admin \
    --firstname Admin \
    --lastname User \
    --email admin@example.com \
    --password admin

# Initialize the database
echo "Initializing database..."
superset db upgrade

# Load examples
echo "Loading examples..."
superset load_examples

# Setup roles
echo "Setting up roles..."
superset init

# Load the OG Strategy Lab dashboard
echo "Loading OG Strategy Lab dashboard..."
superset import-dashboards -p /app/dashboards/og_strategy_lab_dashboards.json

echo "Superset initialization complete!"
