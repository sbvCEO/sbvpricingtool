#!/bin/bash

# Function to check and set up environment
setup_env() {
    local service_dir=$1
    if [ ! -f "$service_dir/.env" ]; then
        if [ -f "$service_dir/.env.example" ]; then
            echo "Creating .env for $service_dir from .env.example"
            cp "$service_dir/.env.example" "$service_dir/.env"
        else
            echo "No .env or .env.example found in $service_dir. Skipping env setup."
        fi
    fi
}

echo "Starting all servers..."

# Clear previous PIDs if they exist
rm -f .server.pids

# 1. Start saas-authz-service
echo "Starting saas-authz-service (port 4000)..."
setup_env "saas-authz-service"
(cd saas-authz-service && npm run dev > ../saas-authz-service.log 2>&1) &
echo $! >> .server.pids

# 2. Start backend uvicorn
echo "Starting backend uvicorn (port 8000)..."
setup_env "backend"
(cd backend && . .venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8000 > ../backend.log 2>&1) &
echo $! >> .server.pids

# 3. Start frontend
echo "Starting frontend (port 5173)..."
setup_env "frontend"
(cd frontend && npm run dev > ../frontend.log 2>&1) &
echo $! >> .server.pids

echo "------------------------------------------------"
echo "All servers started in the background."
echo "PIDs saved in .server.pids"
echo "Logs available in:"
echo "  - saas-authz-service.log"
echo "  - backend.log"
echo "  - frontend.log"
echo ""
echo "To test the AuthZ service authentication, run: ./test-api.sh"
echo "------------------------------------------------"
