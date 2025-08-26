#!/bin/bash

# MySQL Test Data Creation Script
# This script creates test data - assumes it's called only on first run

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if MySQL is ready
wait_for_mysql() {
    log_info "Waiting for MySQL to be ready..."
    for i in $(seq 1 120); do
        # First check with root user since we need admin privileges
        if mysql -h mysql -P 3306 -u root -p"${MYSQL_ROOT_PASSWORD}" -e 'SELECT 1' >/dev/null 2>&1; then
            log_success "MySQL is ready!"
            return 0
        fi
        echo -n "."
        sleep 1
    done
    log_error "MySQL failed to start within 120 seconds"
    exit 1
}

# Check if sample databases already exist
check_existing_databases() {
    log_info "Checking if sample databases already exist..."
    
    # Check if ALL test databases exist (we need all 4) - use root user
    EXISTING_DBS=$(mysql -h mysql -P 3306 -u root -p"${MYSQL_ROOT_PASSWORD}" -e "
        SELECT COUNT(*) FROM information_schema.schemata 
        WHERE schema_name IN ('test_ecommerce', 'test_analytics', 'test_inventory', 'test_hr');
    " --silent --skip-column-names 2>/dev/null || echo "0")
    
    if [ "$EXISTING_DBS" -eq 4 ]; then
        log_warning "All sample databases already exist (found $EXISTING_DBS/4 databases)"
        log_info "Skipping test data creation - data already fully initialized"
        exit 0
    elif [ "$EXISTING_DBS" -gt 0 ]; then
        log_warning "Some sample databases exist (found $EXISTING_DBS/4 databases)"
        log_info "Proceeding with initialization to create missing databases"
    else
        log_info "No sample databases found - proceeding with full initialization"
    fi
}

# Create test data using SQL script
create_test_data() {
    log_info "Creating comprehensive test data..."
    
    # Use root user to create databases and data
    if mysql -h mysql -P 3306 -u root -p"${MYSQL_ROOT_PASSWORD}" < /scripts/create-test-data.sql; then
        log_success "Test data creation completed successfully!"
        
        # Grant permissions to the specified MYSQL_USER for all test databases
        grant_user_permissions
    else
        log_error "Failed to create test data!"
        exit 1
    fi
}

# Grant permissions to MYSQL_USER for all test databases
grant_user_permissions() {
    log_info "Granting permissions to user '${MYSQL_USER}' for the 4 test databases only..."
    
    # Create the user if it doesn't exist and grant permissions for ONLY the 4 test databases
    mysql -h mysql -P 3306 -u root -p"${MYSQL_ROOT_PASSWORD}" <<EOF
-- Create user if not exists
CREATE USER IF NOT EXISTS '${MYSQL_USER}'@'%' IDENTIFIED BY '${MYSQL_PASSWORD}';

-- Grant ALL privileges ONLY on the 4 specific test databases we created
GRANT ALL PRIVILEGES ON test_ecommerce.* TO '${MYSQL_USER}'@'%';
GRANT ALL PRIVILEGES ON test_analytics.* TO '${MYSQL_USER}'@'%';
GRANT ALL PRIVILEGES ON test_inventory.* TO '${MYSQL_USER}'@'%';
GRANT ALL PRIVILEGES ON test_hr.* TO '${MYSQL_USER}'@'%';

-- Note: Default database ${MYSQL_DATABASE} permissions handled separately if needed
-- Note: System databases (information_schema, performance_schema) are auto-accessible

FLUSH PRIVILEGES;
EOF

    if [ $? -eq 0 ]; then
        log_success "Permissions granted successfully to user '${MYSQL_USER}' for 4 test databases"
    else
        log_error "Failed to grant permissions to user '${MYSQL_USER}'"
        exit 1
    fi
}

# Main execution
main() {
    log_info "Starting MySQL test data initialization..."
    
    # Wait for MySQL to be ready
    wait_for_mysql
    
    # Check if sample databases already exist (exit if they do)
    check_existing_databases
    
    # Create test data
    create_test_data
    
    log_success "Test data initialization completed successfully!"
}

# Execute main function
main "$@"
