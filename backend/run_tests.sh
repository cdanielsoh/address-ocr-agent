#!/bin/bash
# Test runner script for Korean Address Extractor Backend

set -e

echo "🚀 Korean Address Extractor Backend Test Runner"
echo "=============================================="

# Check if we're in the backend directory
if [ ! -f "app/main.py" ]; then
    echo "❌ Error: Please run this script from the backend directory"
    exit 1
fi

# Check if sample image exists
if [ ! -f "../sample.jpeg" ]; then
    echo "❌ Error: sample.jpeg not found in parent directory"
    exit 1
fi

# Function to cleanup background processes
cleanup() {
    echo "🧹 Cleaning up..."
    if [ ! -z "$SERVER_PID" ]; then
        echo "Stopping FastAPI server (PID: $SERVER_PID)..."
        kill $SERVER_PID 2>/dev/null || true
        wait $SERVER_PID 2>/dev/null || true
    fi
}
trap cleanup EXIT

# Parse command line arguments
REAL_SERVICES=false
COMPONENT_ONLY=false
SERVER_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --real-services)
            REAL_SERVICES=true
            shift
            ;;
        --component-only)
            COMPONENT_ONLY=true
            shift
            ;;
        --server-only)
            SERVER_ONLY=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --real-services    Use real AWS services (requires AWS credentials)"
            echo "  --component-only   Run only component tests (no API server)"
            echo "  --server-only      Start server only (no tests)"
            echo "  --help, -h         Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                      # Run all tests with mock services"
            echo "  $0 --real-services     # Run all tests with real AWS services"
            echo "  $0 --component-only    # Run only component tests"
            echo "  $0 --server-only       # Start server for manual testing"
            exit 0
            ;;
        *)
            echo "❌ Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3.12 -m venv venv
fi

echo "📦 Activating virtual environment..."
source venv/bin/activate

echo "📦 Installing/updating dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Set environment variables
export PORT=3001
export AWS_REGION=us-west-2
export USE_STRANDS_AGENT=${REAL_SERVICES}
export AWS_DEFAULT_REGION=us-west-2

if [ "$REAL_SERVICES" = true ]; then
    echo "⚠️  Using real AWS services - ensure you have proper credentials configured"
    echo "   This will test: Upstage SageMaker endpoint and Bedrock"
    # Check AWS credentials
    if ! python3 -c "import boto3; boto3.Session().get_credentials()" 2>/dev/null; then
        echo "❌ Error: AWS credentials not configured properly"
        echo "   Please configure AWS credentials using:"
        echo "   - aws configure"
        echo "   - AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables"
        echo "   - EC2 IAM role (when deployed)"
        exit 1
    fi
else
    echo "🎭 Using mock services (except Upstage OCR which requires real endpoint)"
fi

if [ "$COMPONENT_ONLY" = true ]; then
    echo ""
    echo "🧪 Running component tests only..."
    if [ "$REAL_SERVICES" = true ]; then
        python test_backend.py --real-services
    else
        python test_backend.py
    fi
    exit $?
fi

if [ "$SERVER_ONLY" = true ]; then
    echo ""
    echo "🌐 Starting FastAPI server for manual testing..."
    echo "   Server will be available at: http://localhost:3001"
    echo "   API docs at: http://localhost:3001/docs"
    echo "   Press Ctrl+C to stop"
    echo ""
    python -m uvicorn app.main:app --host 0.0.0.0 --port 3001 --reload
    exit 0
fi

# Start FastAPI server in background
echo ""
echo "🌐 Starting FastAPI server..."
python -m uvicorn app.main:app --host 0.0.0.0 --port 3001 &
SERVER_PID=$!

# Wait for server to start
echo "⏳ Waiting for server to start..."
for i in {1..10}; do
    if curl -s http://localhost:3001/api/health > /dev/null 2>&1; then
        echo "✅ Server is ready!"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "❌ Server failed to start within 10 seconds"
        exit 1
    fi
    sleep 1
done

# Run tests
echo ""
echo "🧪 Running backend tests..."
if [ "$REAL_SERVICES" = true ]; then
    python test_backend.py --real-services
else
    python test_backend.py
fi

TEST_EXIT_CODE=$?

# Server will be stopped by cleanup trap
echo ""
echo "✅ Test run completed!"
exit $TEST_EXIT_CODE