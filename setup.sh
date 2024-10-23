#!/bin/bash

# Function to check if PostgreSQL is installed
is_postgresql_installed() {
    if command -v psql >/dev/null 2>&1; then
        return 0  # PostgreSQL is installed
    else
        return 1  # PostgreSQL is not installed
    fi
}

# Function to install PostgreSQL on Debian-based Linux
install_postgresql_linux() {
    if is_postgresql_installed; then
        echo "PostgreSQL is already installed. Skipping installation."
    else
        # Update packages
        sudo apt update

        # Install PostgreSQL Server
        sudo apt install -y postgresql postgresql-contrib

        # Start PostgreSQL service
        sudo service postgresql start
    fi
}

# Function to install PostgreSQL on macOS
install_postgresql_mac() {
    if is_postgresql_installed; then
        echo "PostgreSQL is already installed. Skipping installation."
    else
        # Install PostgreSQL using Homebrew
        brew update

        # Install PostgreSQL
        brew install postgresql@14

        # Start PostgreSQL service
        brew services start postgresql@14
    fi
}

# Detect the operating system
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "Linux detected. Installing PostgreSQL..."
    install_postgresql_linux
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo "macOS detected. Installing PostgreSQL..."
    install_postgresql_mac
else
    echo "Unsupported OS. Please install PostgreSQL manually."
    exit 1
fi

# Update packages (only for Linux systems)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    sudo apt update
fi

# Install necessary packages
pip3 install -r requirement.txt

# Create PostgreSQL database and user
if is_postgresql_installed; then
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo -u postgres psql -d postgres -c "CREATE DATABASE bank_app;"
        sudo -u postgres psql -d postgres -c "CREATE USER bank_user WITH ENCRYPTED PASSWORD 'CSCI430_CTF1_KANMJA';"
        sudo -u postgres psql -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE bank_app TO bank_user;"


        # Create tables
        sudo -u postgres psql -d bank_app -c "
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            balance NUMERIC(15, 2) DEFAULT 0.00
        );"

    elif [[ "$OSTYPE" == "darwin"* ]]; then
        psql -d postgres -c "CREATE DATABASE bank_app;"
        psql -d postgres -c "CREATE USER bank_user WITH ENCRYPTED PASSWORD 'CSCI430_CTF1_KANMJA';"
        psql -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE bank_app TO bank_user;"

        # Create tables
        psql -d bank_app -c "
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            balance NUMERIC(15, 2) DEFAULT 0.00
        );"
        
        psql -d bank_app -c "
        CREATE TABLE sessions (
            session_id SERIAL PRIMARY KEY,
            user_id INT REFERENCES users(id) ON DELETE CASCADE,
            cookie VARCHAR(255) UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );"
    fi
else
    echo "PostgreSQL is not installed. Please verify the installation."
fi

# Setup complete
echo "Setup complete. Please configure SSL and update app.py if necessary."
