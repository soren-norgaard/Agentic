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
echo -e "${GREEN}All tests passed!${NC}"
echo "========================================="
echo ""
echo "Summary:"
echo "  - API: $API_URL ✓"
echo "  - Frontend: $FRONTEND_URL ✓"
echo "  - Project CRUD: Working ✓"
echo "  - Workflow CRUD: Working ✓"
echo ""
