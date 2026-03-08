#!/bin/bash

# Configuration
BACKEND_URL="http://localhost:8000"
AUTHZ_URL="http://localhost:4000"
TENANT_ID="00000000-0000-0000-0000-000000000000"
USER_EMAIL="admin@spt.com"
USER_PASSWORD="r@ndom11"

echo "1. Requesting developer token from Backend..."
TOKEN_RESPONSE=$(curl -s -X POST "$BACKEND_URL/api/auth/dev-token" \
  -H "Content-Type: application/json" \
  -d "{
    \"tenant_id\": \"$TENANT_ID\",
    \"email\": \"$USER_EMAIL\",
    \"password\": \"$USER_PASSWORD\"
  }")

ACCESS_TOKEN=$(echo $TOKEN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))")

if [ -z "$ACCESS_TOKEN" ]; then
    echo "Error: Failed to get access token from backend."
    echo "Response: $TOKEN_RESPONSE"
    exit 1
fi

echo "Successfully obtained token."
echo ""

echo "2. Testing AuthZ Service (Health Check)..."
curl -s "$AUTHZ_URL/health"
echo ""
echo ""

echo "3. Testing AuthZ Service (Protected Route: /api/projects) with Bearer Token..."
curl -i -s "$AUTHZ_URL/api/projects" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "X-Tenant-Id: $TENANT_ID"

echo ""
echo "------------------------------------------------"
echo "Test complete."
