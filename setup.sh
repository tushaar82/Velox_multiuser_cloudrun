#!/bin/bash

# Setup script for the Multi-User Algorithmic Trading Platform

set -e

echo "=========================================="
echo "Trading Platform Setup"
echo "=========================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "Error: Python 3.11 or higher is required. Found: $python_version"
    exit 1
fi
echo "✓ Python $python_version found"
echo ""

# Create virtual environment
echo "Creating Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1
echo "✓ pip upgraded"
echo ""

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt
echo "✓ Dependencies installed"
echo ""

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✓ .env file created"
    echo "⚠ Please edit .env file with your configuration"
else
    echo "✓ .env file already exists"
fi
echo ""

# Check Docker
echo "Checking Docker..."
if command -v docker &> /dev/null; then
    echo "✓ Docker found"
    
    # Check if Docker is running
    if docker info > /dev/null 2>&1; then
        echo "✓ Docker is running"
        
        # Start infrastructure services
        echo ""
        read -p "Start infrastructure services (PostgreSQL, Redis, InfluxDB)? (y/n) " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "Starting services with docker-compose..."
            docker-compose up -d
            echo "✓ Services started"
            echo ""
            echo "Waiting for services to be ready..."
            sleep 10
            docker-compose ps
        fi
    else
        echo "⚠ Docker is not running. Please start Docker and run: docker-compose up -d"
    fi
else
    echo "⚠ Docker not found. Please install Docker to run infrastructure services."
fi
echo ""

echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env file with your configuration"
echo "2. Start infrastructure: docker-compose up -d"
echo "3. Run database migrations (when available)"
echo "4. Start services"
echo ""
echo "To activate the virtual environment:"
echo "  source venv/bin/activate"
echo ""
