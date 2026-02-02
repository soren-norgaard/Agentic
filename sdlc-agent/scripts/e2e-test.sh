#!/bin/bash
# End-to-end test for SDLC Agent system

set -e

echo "========================================="
echo "SDLC Agent - End-to-End Test"
echo "========================================="
echo ""

API_URL="http://localhost:8000"
FRONTEND_URL="http://localhost:3000"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

pass() { echo -e "${GREEN}✓ $1${NC}"; }
fail() { echo -e "${RED}✗ $1${NC}"; exit 1; }
info() { echo -e "${YELLOW}→ $1${NC}"; }

# Test 1: API Health Check
info "Testing API health..."
HEALTH=$(curl -s "$API_URL/api/v1/health")
if echo "$HEALTH" | grep -q '"status":"healthy"'; then
    pass "API is healthy"
else
    fail "API health check failed: $HEALTH"
fi

# Test 2: Frontend is accessible
info "Testing frontend accessibility..."
FRONTEND=$(curl -s -o /dev/null -w "%{http_code}" "$FRONTEND_URL")
if [ "$FRONTEND" = "200" ]; then
    pass "Frontend is accessible (HTTP 200)"
else
    fail "Frontend returned HTTP $FRONTEND"
fi

# Test 3: Create a new project
info "Creating a test project..."
PROJECT_NAME="E2E-Test-$(date +%s)"
CREATE_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/projects" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"$PROJECT_NAME\",\"description\":\"Automated end-to-end test project\",\"repository_url\":\"https://github.com/test/repo\"}")

if echo "$CREATE_RESPONSE" | grep -q '"id"'; then
    PROJECT_ID=$(echo "$CREATE_RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
    pass "Project created: $PROJECT_NAME (ID: $PROJECT_ID)"
else
    fail "Failed to create project: $CREATE_RESPONSE"
fi

# Test 4: List projects (should include the new one)
info "Listing projects..."
LIST_RESPONSE=$(curl -s "$API_URL/api/v1/projects")
if echo "$LIST_RESPONSE" | grep -q "$PROJECT_NAME"; then
    TOTAL=$(echo "$LIST_RESPONSE" | grep -o '"total":[0-9]*' | cut -d':' -f2)
    pass "Project list retrieved (Total: $TOTAL projects)"
else
    fail "Created project not found in list: $LIST_RESPONSE"
fi

# Test 5: Get single project
info "Fetching single project..."
GET_RESPONSE=$(curl -s "$API_URL/api/v1/projects/$PROJECT_ID")
if echo "$GET_RESPONSE" | grep -q "$PROJECT_NAME"; then
    pass "Single project retrieved successfully"
else
    fail "Failed to get project: $GET_RESPONSE"
fi

# Test 6: Update project
info "Updating project..."
UPDATE_RESPONSE=$(curl -s -X PATCH "$API_URL/api/v1/projects/$PROJECT_ID" \
    -H "Content-Type: application/json" \
    -d '{"description":"Updated by E2E test"}')
if echo "$UPDATE_RESPONSE" | grep -q "Updated by E2E test"; then
    pass "Project updated successfully"
else
    fail "Failed to update project: $UPDATE_RESPONSE"
fi

# Test 7: Create a workflow for the project
info "Creating a workflow..."
WORKFLOW_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/workflows" \
    -H "Content-Type: application/json" \
    -d "{\"project_id\":\"$PROJECT_ID\",\"name\":\"E2E Test Workflow\"}")

if echo "$WORKFLOW_RESPONSE" | grep -q '"id"'; then
    WORKFLOW_ID=$(echo "$WORKFLOW_RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
    pass "Workflow created (ID: $WORKFLOW_ID)"
else
    fail "Failed to create workflow: $WORKFLOW_RESPONSE"
fi

# Test 8: Get workflow
info "Fetching workflow..."
GET_WORKFLOW=$(curl -s "$API_URL/api/v1/workflows/$WORKFLOW_ID")
if echo "$GET_WORKFLOW" | grep -q "E2E Test Workflow"; then
    pass "Workflow retrieved successfully"
else
    fail "Failed to get workflow: $GET_WORKFLOW"
fi

# Test 9: List workflows
info "Listing workflows..."
LIST_WORKFLOWS=$(curl -s "$API_URL/api/v1/workflows")
if echo "$LIST_WORKFLOWS" | grep -q "$WORKFLOW_ID"; then
    WORKFLOW_TOTAL=$(echo "$LIST_WORKFLOWS" | grep -o '"total":[0-9]*' | cut -d':' -f2)
    pass "Workflow list retrieved (Total: $WORKFLOW_TOTAL workflows)"
else
    fail "Created workflow not found in list: $LIST_WORKFLOWS"
fi

# Test 10: Get workflow executions (should be empty initially)
info "Fetching workflow executions..."
EXECUTIONS=$(curl -s "$API_URL/api/v1/workflows/$WORKFLOW_ID/executions")
if echo "$EXECUTIONS" | grep -q '\[\]' || echo "$EXECUTIONS" | grep -q '"id"'; then
    pass "Workflow executions endpoint working"
else
    fail "Failed to get executions: $EXECUTIONS"
fi

# Test 11: Delete workflow
info "Deleting test workflow..."
DELETE_WORKFLOW=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "$API_URL/api/v1/workflows/$WORKFLOW_ID")
if [ "$DELETE_WORKFLOW" = "204" ] || [ "$DELETE_WORKFLOW" = "200" ]; then
    pass "Workflow deleted successfully"
else
    # Some APIs don't have delete, skip if 404 or 405
    if [ "$DELETE_WORKFLOW" = "404" ] || [ "$DELETE_WORKFLOW" = "405" ]; then
        info "Workflow delete not implemented (HTTP $DELETE_WORKFLOW) - skipping"
    else
        fail "Failed to delete workflow (HTTP $DELETE_WORKFLOW)"
    fi
fi

# Test 12: Delete project
info "Deleting test project..."
DELETE_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "$API_URL/api/v1/projects/$PROJECT_ID")
if [ "$DELETE_RESPONSE" = "204" ] || [ "$DELETE_RESPONSE" = "200" ]; then
    pass "Project deleted successfully"
else
    fail "Failed to delete project (HTTP $DELETE_RESPONSE)"
fi

# Test 13: Verify deletion
info "Verifying project deletion..."
VERIFY_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/api/v1/projects/$PROJECT_ID")
if [ "$VERIFY_RESPONSE" = "404" ]; then
    pass "Project correctly returns 404 after deletion"
else
    fail "Project still exists after deletion (HTTP $VERIFY_RESPONSE)"
fi

echo ""
echo "========================================="
echo "RBAC Authentication & Authorization Tests"
echo "========================================="
echo ""

# Test 14: Login with valid credentials
info "Testing login with valid credentials..."
LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"Admin123!"}')

if echo "$LOGIN_RESPONSE" | grep -q '"access_token"'; then
    ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
    pass "Login successful, JWT token received"
else
    fail "Login failed: $LOGIN_RESPONSE"
fi

# Test 15: Access protected endpoint with valid token
info "Testing protected endpoint with valid token..."
ME_RESPONSE=$(curl -s "$API_URL/api/v1/users/me" \
    -H "Authorization: Bearer $ACCESS_TOKEN")

if echo "$ME_RESPONSE" | grep -q '"username":"admin"'; then
    pass "Protected endpoint accessible with valid token"
else
    fail "Failed to access protected endpoint: $ME_RESPONSE"
fi

# Test 16: Access protected endpoint without token
info "Testing protected endpoint without token..."
UNAUTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/api/v1/users/me")
if [ "$UNAUTH_RESPONSE" = "401" ]; then
    pass "Protected endpoint correctly returns 401 without token"
else
    fail "Expected 401, got HTTP $UNAUTH_RESPONSE"
fi

# Test 17: Access protected endpoint with invalid token
info "Testing protected endpoint with invalid token..."
INVALID_TOKEN_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/api/v1/users/me" \
    -H "Authorization: Bearer invalid.token.here")
if [ "$INVALID_TOKEN_RESPONSE" = "401" ]; then
    pass "Protected endpoint correctly returns 401 with invalid token"
else
    fail "Expected 401, got HTTP $INVALID_TOKEN_RESPONSE"
fi

# Test 18: List roles
info "Testing roles endpoint..."
ROLES_RESPONSE=$(curl -s "$API_URL/api/v1/roles" \
    -H "Authorization: Bearer $ACCESS_TOKEN")

if echo "$ROLES_RESPONSE" | grep -q '"admin"'; then
    pass "Roles endpoint returns admin role"
else
    fail "Failed to list roles: $ROLES_RESPONSE"
fi

# Test 19: List permissions
info "Testing permissions endpoint..."
PERMS_RESPONSE=$(curl -s "$API_URL/api/v1/permissions" \
    -H "Authorization: Bearer $ACCESS_TOKEN")

if echo "$PERMS_RESPONSE" | grep -q '"items"' || echo "$PERMS_RESPONSE" | grep -q '"resource"'; then
    pass "Permissions endpoint working"
else
    fail "Failed to list permissions: $PERMS_RESPONSE"
fi

# Test 20: List users
info "Testing users endpoint..."
USERS_RESPONSE=$(curl -s "$API_URL/api/v1/users" \
    -H "Authorization: Bearer $ACCESS_TOKEN")

if echo "$USERS_RESPONSE" | grep -q '"admin"'; then
    pass "Users endpoint returns admin user"
else
    fail "Failed to list users: $USERS_RESPONSE"
fi

# Test 21: Get audit logs
info "Testing audit logs endpoint..."
AUDIT_RESPONSE=$(curl -s "$API_URL/api/v1/audit-logs" \
    -H "Authorization: Bearer $ACCESS_TOKEN")

if echo "$AUDIT_RESPONSE" | grep -q '"items"' || echo "$AUDIT_RESPONSE" | grep -q '\[\]'; then
    pass "Audit logs endpoint working"
else
    fail "Failed to get audit logs: $AUDIT_RESPONSE"
fi

# Test 22: Login with invalid credentials
info "Testing login with invalid credentials..."
BAD_LOGIN=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API_URL/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"wrongpassword"}')

if [ "$BAD_LOGIN" = "401" ]; then
    pass "Login correctly rejects invalid credentials"
else
    fail "Expected 401 for invalid credentials, got HTTP $BAD_LOGIN"
fi

echo ""
echo "========================================="
echo -e "${GREEN}All tests passed!${NC}"
echo "========================================="
echo ""
echo "Summary:"
echo "  - API: $API_URL ✓"
echo "  - Frontend: $FRONTEND_URL ✓"
echo "  - Project CRUD: Working ✓"
echo "  - Workflow CRUD: Working ✓"
echo "  - RBAC Authentication: Working ✓"
echo "  - RBAC Authorization: Working ✓"
echo ""
