# OG Strategy Lab: Self-Hosted

This is the self-hosted version of OG Strategy Lab, an advanced options trading signal platform designed for high-performance deployment on Railway, Render, or other cloud platforms.

## Features

- **Real-time Signal Processing**: Advanced pattern recognition for options trading signals
- **Discord Integration**: Automated alerts sent to your Discord server
- **Alpaca API Integration**: Paper trading and live trading capabilities
- **Socket.IO Real-time Updates**: Live updates on all connected clients
- **RESTful API**: Comprehensive API for integration with other systems
- **Scalable Architecture**: Designed for reliability and performance

## Quick Start

### Prerequisites

- Python 3.9+
- PostgreSQL database
- Discord Bot Token and Channel ID
- Alpaca API Key and Secret

### Installation

1. Clone this repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file based on `.env.example`:
   ```bash
   cp .env.example .env
   # Edit .env file with your credentials
   ```
5. Run the application:
   ```bash
   flask run --host=0.0.0.0
   ```

### Docker Deployment

1. Build the Docker image:
   ```bash
   docker build -t og-strategy-lab .
   ```
2. Run the container:
   ```bash
   docker run -p 5000:5000 --env-file .env og-strategy-lab
   ```

## Railway Deployment

1. Create a new project on Railway.app
2. Add the necessary environment variables:
   - `FLASK_SECRET_KEY`
   - `DATABASE_URL` (Railway PostgreSQL plugin will provide this automatically if added)
   - `DISCORD_TOKEN`
   - `DISCORD_CHANNEL_ID`
   - `ALPACA_API_KEY`
   - `ALPACA_SECRET_KEY`
   - `ALPACA_BASE_URL`
3. Deploy from GitHub repository
4. (Optional) Configure a custom domain

## API Documentation

### Authentication

Authentication is not implemented in this base version but can be added with JWT or API keys.

### Signal Endpoints

- `GET /api/signals` - Get all signals
- `POST /api/signals` - Create a new signal
- `GET /api/signals/{id}` - Get signal by ID

### Alpaca Integration

- `GET /api/account` - Get account information
- `GET /api/positions` - Get current positions
- `GET /api/orders` - Get orders

### System Endpoints

- `GET /api/health` - Health check endpoint
- `GET /system/test_discord` - Test Discord notification
- `GET /system/test_signal` - Generate a test signal

## Configuration

All configuration is done through environment variables. See `.env.example` for available options.

## License

This software is proprietary. © 2025 OG Strategy Lab. All rights reserved.

## Support

For support, please contact [support@ogstrategylab.com](mailto:support@ogstrategylab.com)