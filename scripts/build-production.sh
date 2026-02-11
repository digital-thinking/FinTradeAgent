#!/bin/bash

# Production Build Script for FinTradeAgent
# This script builds both frontend and backend for production deployment

set -e  # Exit on any error
set -u  # Exit on undefined variable

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
BUILD_DIR="${PROJECT_ROOT}/build"
DIST_DIR="${PROJECT_ROOT}/dist"
FRONTEND_DIR="${PROJECT_ROOT}/frontend"
BACKEND_DIR="${PROJECT_ROOT}/backend"

# Build metadata
BUILD_VERSION=${BUILD_VERSION:-$(git rev-parse --short HEAD)}
BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
BUILD_ENVIRONMENT=${BUILD_ENVIRONMENT:-production}

echo -e "${BLUE}🚀 Starting FinTradeAgent Production Build${NC}"
echo -e "${BLUE}Version: ${BUILD_VERSION}${NC}"
echo -e "${BLUE}Date: ${BUILD_DATE}${NC}"
echo -e "${BLUE}Environment: ${BUILD_ENVIRONMENT}${NC}"
echo ""

# Function to log messages
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    log_info "Checking build prerequisites..."
    
    # Check Node.js
    if ! command -v node &> /dev/null; then
        log_error "Node.js is not installed"
        exit 1
    fi
    
    # Check npm
    if ! command -v npm &> /dev/null; then
        log_error "npm is not installed"
        exit 1
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed"
        exit 1
    fi
    
    # Check git (for version info)
    if ! command -v git &> /dev/null; then
        log_warn "Git is not installed - using default version"
        BUILD_VERSION="1.0.0"
    fi
    
    log_info "Prerequisites check passed ✅"
}

# Function to clean build directories
clean_build_dirs() {
    log_info "Cleaning build directories..."
    
    rm -rf "${BUILD_DIR}"
    rm -rf "${DIST_DIR}"
    rm -rf "${FRONTEND_DIR}/dist"
    
    mkdir -p "${BUILD_DIR}"
    mkdir -p "${DIST_DIR}"
    
    log_info "Build directories cleaned ✅"
}

# Function to build frontend
build_frontend() {
    log_info "Building frontend for production..."
    
    cd "${FRONTEND_DIR}"
    
    # Install dependencies
    log_info "Installing frontend dependencies..."
    npm ci --production=false
    
    # Run security audit
    log_info "Running security audit..."
    npm audit --audit-level high || log_warn "Security audit found issues"
    
    # Run tests
    log_info "Running frontend tests..."
    npm run test:run || {
        log_error "Frontend tests failed"
        exit 1
    }
    
    # Build for production
    log_info "Building frontend bundle..."
    export VITE_APP_VERSION="${BUILD_VERSION}"
    export VITE_BUILD_DATE="${BUILD_DATE}"
    npm run build:prod
    
    # Verify build output
    if [ ! -d "${FRONTEND_DIR}/dist" ]; then
        log_error "Frontend build failed - dist directory not found"
        exit 1
    fi
    
    # Analyze bundle size
    log_info "Analyzing bundle size..."
    npm run analyze:bundle || log_warn "Bundle analysis failed"
    
    # Copy build output
    cp -r "${FRONTEND_DIR}/dist" "${BUILD_DIR}/frontend"
    
    log_info "Frontend build completed ✅"
}

# Function to build backend
build_backend() {
    log_info "Building backend for production..."
    
    cd "${BACKEND_DIR}"
    
    # Create virtual environment for build
    log_info "Setting up Python virtual environment..."
    python3 -m venv "${BUILD_DIR}/venv"
    source "${BUILD_DIR}/venv/bin/activate"
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install dependencies
    log_info "Installing backend dependencies..."
    pip install -r requirements.txt
    
    # Install production-only dependencies
    pip install gunicorn uvloop httptools
    
    # Run backend tests
    log_info "Running backend tests..."
    cd "${PROJECT_ROOT}"
    python -m pytest tests/ -v --tb=short || {
        log_error "Backend tests failed"
        exit 1
    }
    
    # Create backend distribution
    log_info "Creating backend distribution..."
    mkdir -p "${BUILD_DIR}/backend"
    
    # Copy source code
    cp -r "${PROJECT_ROOT}/src" "${BUILD_DIR}/backend/"
    cp -r "${PROJECT_ROOT}/backend" "${BUILD_DIR}/backend/"
    
    # Copy configuration files
    cp "${PROJECT_ROOT}/.env.production" "${BUILD_DIR}/backend/"
    cp "${PROJECT_ROOT}/requirements.txt" "${BUILD_DIR}/backend/"
    
    # Create requirements file for production
    pip freeze > "${BUILD_DIR}/backend/requirements-production.txt"
    
    # Compile Python bytecode
    log_info "Compiling Python bytecode..."
    python -m compileall "${BUILD_DIR}/backend" -q
    
    log_info "Backend build completed ✅"
}

# Function to create deployment package
create_deployment_package() {
    log_info "Creating deployment package..."
    
    cd "${BUILD_DIR}"
    
    # Create deployment structure
    mkdir -p "${DIST_DIR}/fintradeagent"
    
    # Copy built assets
    cp -r frontend "${DIST_DIR}/fintradeagent/"
    cp -r backend "${DIST_DIR}/fintradeagent/"
    
    # Copy deployment scripts
    cp -r "${PROJECT_ROOT}/scripts/deployment" "${DIST_DIR}/fintradeagent/" 2>/dev/null || log_warn "No deployment scripts found"
    
    # Copy Docker files
    cp "${PROJECT_ROOT}/Dockerfile" "${DIST_DIR}/fintradeagent/" 2>/dev/null || log_warn "No Dockerfile found"
    cp "${PROJECT_ROOT}/docker-compose.production.yml" "${DIST_DIR}/fintradeagent/" 2>/dev/null || log_warn "No docker-compose.production.yml found"
    
    # Create build info file
    cat > "${DIST_DIR}/fintradeagent/build-info.json" << EOF
{
  "version": "${BUILD_VERSION}",
  "build_date": "${BUILD_DATE}",
  "environment": "${BUILD_ENVIRONMENT}",
  "git_commit": "$(git rev-parse HEAD 2>/dev/null || echo 'unknown')",
  "git_branch": "$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'unknown')",
  "build_host": "$(hostname)",
  "build_user": "$(whoami)"
}
EOF
    
    # Create installation script
    cat > "${DIST_DIR}/fintradeagent/install.sh" << 'EOF'
#!/bin/bash
# Installation script for FinTradeAgent production deployment

echo "Installing FinTradeAgent..."

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "This script should not be run as root" 
   exit 1
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "Docker is required but not installed"
    exit 1
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose is required but not installed"
    exit 1
fi

echo "Prerequisites check passed"

# Load environment variables
if [ -f ".env.production" ]; then
    echo "Loading production environment..."
    export $(cat .env.production | grep -v ^# | xargs)
fi

# Start services
echo "Starting FinTradeAgent services..."
docker-compose -f docker-compose.production.yml up -d

echo "FinTradeAgent installation completed!"
echo "Access the application at: https://localhost"
EOF
    
    chmod +x "${DIST_DIR}/fintradeagent/install.sh"
    
    # Create compressed archive
    log_info "Creating compressed archive..."
    cd "${DIST_DIR}"
    tar -czf "fintradeagent-${BUILD_VERSION}.tar.gz" fintradeagent/
    
    # Create checksums
    sha256sum "fintradeagent-${BUILD_VERSION}.tar.gz" > "fintradeagent-${BUILD_VERSION}.tar.gz.sha256"
    
    log_info "Deployment package created ✅"
    log_info "Package: ${DIST_DIR}/fintradeagent-${BUILD_VERSION}.tar.gz"
}

# Function to run build verification
verify_build() {
    log_info "Verifying build output..."
    
    # Check frontend build
    if [ ! -f "${BUILD_DIR}/frontend/index.html" ]; then
        log_error "Frontend build verification failed - index.html not found"
        exit 1
    fi
    
    # Check backend files
    if [ ! -d "${BUILD_DIR}/backend/backend" ]; then
        log_error "Backend build verification failed - backend directory not found"
        exit 1
    fi
    
    # Check if main files exist
    required_files=(
        "${BUILD_DIR}/frontend/assets"
        "${BUILD_DIR}/backend/backend/main_production.py"
        "${BUILD_DIR}/backend/.env.production"
        "${BUILD_DIR}/backend/requirements.txt"
    )
    
    for file in "${required_files[@]}"; do
        if [ ! -e "$file" ]; then
            log_error "Required file not found: $file"
            exit 1
        fi
    done
    
    log_info "Build verification passed ✅"
}

# Function to display build summary
display_summary() {
    echo ""
    echo -e "${GREEN}🎉 Build completed successfully!${NC}"
    echo ""
    echo -e "${BLUE}Build Summary:${NC}"
    echo -e "  Version: ${BUILD_VERSION}"
    echo -e "  Date: ${BUILD_DATE}"
    echo -e "  Environment: ${BUILD_ENVIRONMENT}"
    echo ""
    echo -e "${BLUE}Output:${NC}"
    echo -e "  Frontend: ${BUILD_DIR}/frontend"
    echo -e "  Backend: ${BUILD_DIR}/backend"
    echo -e "  Package: ${DIST_DIR}/fintradeagent-${BUILD_VERSION}.tar.gz"
    echo ""
    
    # Display file sizes
    if command -v du &> /dev/null; then
        echo -e "${BLUE}Build Sizes:${NC}"
        echo -e "  Frontend: $(du -sh "${BUILD_DIR}/frontend" | cut -f1)"
        echo -e "  Backend: $(du -sh "${BUILD_DIR}/backend" | cut -f1)"
        echo -e "  Package: $(du -sh "${DIST_DIR}/fintradeagent-${BUILD_VERSION}.tar.gz" | cut -f1)"
        echo ""
    fi
    
    echo -e "${YELLOW}Next steps:${NC}"
    echo -e "  1. Review build output in ${BUILD_DIR}"
    echo -e "  2. Test deployment package: ${DIST_DIR}/fintradeagent-${BUILD_VERSION}.tar.gz"
    echo -e "  3. Deploy to production environment"
}

# Main execution
main() {
    cd "${PROJECT_ROOT}"
    
    check_prerequisites
    clean_build_dirs
    build_frontend
    build_backend
    create_deployment_package
    verify_build
    display_summary
    
    log_info "Production build completed successfully! 🎉"
}

# Run main function
main "$@"