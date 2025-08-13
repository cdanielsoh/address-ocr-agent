# Korean Address Extractor

A React-based web application that extracts handwritten Korean addresses from images using Upstage Document OCR and displays the results with confidence analysis using Strands Agents.

## Architecture

- **Frontend**: React SPA with Material-UI and mobile-responsive design
- **Backend**: Python FastAPI
- **OCR Service**: Upstage Document OCR via SageMaker
- **Confidence Analysis**: Strands Agents
- **Infrastructure**: AWS CDK with Python, ALB/EC2 deployment

## Project Structure

```
textract-with-agent/
├── frontend/                # React application
│   ├── src/
│   │   ├── App.tsx         # Main React component
│   │   └── ...
│   ├── package.json
│   └── .env
├── backend/                 # FastAPI application
│   ├── app/
│   │   ├── main.py         # FastAPI app entry point
│   │   ├── routers/        # API routes
│   │   ├── services/       # Business logic
│   │   └── models/         # Data models
│   ├── requirements.txt
│   └── .env
└── infrastructure/          # AWS CDK infrastructure
    ├── app.py              # CDK app entry point
    ├── stacks/             # CDK stacks
    ├── configs/            # Environment configs
    └── requirements.txt
```

## Development Setup

### Prerequisites

- Node.js 18+
- Python 3.9+
- AWS CLI configured
- AWS CDK CLI

### Frontend Setup

```bash
cd frontend
npm install
npm start              # Development server
# OR
npm run build          # Production build
```

The frontend will be available at http://localhost:3000

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your AWS credentials

# Start the server
uvicorn app.main:app --host 0.0.0.0 --port 3001 --reload
```

The backend API will be available at http://localhost:3001

### Testing

The project includes comprehensive test suites for the backend:

#### Quick Test (Automated)
```bash
cd backend
./run_tests.sh                    # Run all tests with mock services
./run_tests.sh --real-services    # Run all tests with real AWS services
./run_tests.sh --component-only   # Run only component tests
./run_tests.sh --server-only      # Start server for manual testing
```

#### Unit Tests
```bash
cd backend
python test_address_parsing.py    # Run unit tests for address parsing
```

#### Manual Testing
```bash
cd backend
python test_backend.py            # Interactive test with sample.jpeg
```

#### Test Features

- **Component Tests**: Upstage OCR service, Strands agent, address parsing
- **API Tests**: Health check, address extraction endpoint
- **Unit Tests**: Korean address regex patterns, confidence calculation
- **Mock Mode**: Test without AWS credentials
- **Real Services Mode**: Test with actual AWS services
- **Automatic Server Management**: Starts/stops FastAPI server for testing

### Infrastructure Deployment

```bash
cd infrastructure

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Bootstrap CDK (first time only)
cdk bootstrap

# Deploy development environment
cdk deploy KoreanAddressApp-dev

# Deploy production environment
cdk deploy KoreanAddressApp-prod --context environment=prod
```

## Environment Variables

### Frontend (.env)

```
REACT_APP_API_URL=http://localhost:3001/api
REACT_APP_ENVIRONMENT=development
```

### Backend (.env)

```
PORT=3001
AWS_REGION=ap-northeast-2
USE_STRANDS_AGENT=true
# AWS credentials will be provided by EC2 IAM role via STS
AWS_DEFAULT_REGION=us-west-2
# Upstage OCR SageMaker endpoint
SAGEMAKER_OCR_ENDPOINT_NAME=Endpoint-Document-OCR-1
```

## API Endpoints

### POST /api/extract-address
Extract Korean address from uploaded image using Upstage Document OCR.

**Request**: Multipart form data with image file
**Response**: 
```json
{
  "imageId": "string",
  "extractedText": "string",
  "confidence": {
    "overall": 0.85,
    "components": {
      "sido": 0.9,
      "sigungu": 0.8,
      "roadName": 0.9,
      "buildingNumber": 0.85
    }
  },
  "processingTime": 1250
}
```

### POST /api/extract-address-upstage
Extract Korean address from uploaded image using Upstage Document OCR.

**Request**: Multipart form data with image file
**Response**: Same as above, plus:
```json
{
  "ocr_provider": "upstage",
  "endpoint_name": "Endpoint-Document-OCR-1",
  "upstage_metadata": {
    "api_version": "1.1",
    "model_version": "ocr-2.2.1",
    "overall_confidence": 0.99,
    "num_billed_pages": 1,
    "total_words": 5,
    "average_word_confidence": 0.99,
    "pages_info": [{"page": 1, "width": 786, "height": 256}]
  },
  "raw_ocr_result": { ... }
}
```


### GET /api/extract-address/{imageId}/status
Get processing status for an image.

### GET /api/health
Health check endpoint.

## Features

- Camera integration for photo capture
- File upload with drag & drop
- Image preview before processing
- **Upstage Document OCR**: High-accuracy Korean text recognition
- Confidence analysis with Strands Agents
- Mobile-responsive design
- Side-by-side results display

## Strands Agents Integration

The application uses a custom Strands agent for enhanced confidence analysis of Korean address extraction. The agent includes specialized tools:

### Agent Tools

1. **validate_korean_address_format**: Validates extracted text against Korean address patterns
2. **analyze_text_quality**: Analyzes text quality metrics (Korean character ratio, length, etc.)
3. **calculate_confidence_scores**: Calculates enhanced confidence scores based on validation and quality

### Agent Configuration

- **Model**: Claude 3.7 Sonnet on Amazon Bedrock (us-west-2)
- **Purpose**: Korean address extraction confidence analysis
- **Location**: `backend/strands_agent/agent.py`

### Environment Variables

- `USE_STRANDS_AGENT=true`: Enable/disable Strands agent (falls back to mock if disabled)
- `AWS_DEFAULT_REGION=us-west-2`: Required for Bedrock access

### Requirements

The Strands agent requires:
- EC2 IAM role with Bedrock access (credentials via STS)
- Model access to Claude 3.7 Sonnet in us-west-2 region
- `strands-agents` and `strands-agents-tools` packages

## Supported Address Format

The application processes Korean addresses in the standard format:
```
시·도 + 시·군·구 + 도로명 + 건물번호 [동] [호수] (법정동명, 건물명)
예시: 서울특별시 성북구 화랑로 11길 26 103동 1602호 (하월곡동, OO아파트)
```

## Deployment

The application is designed to be deployed on AWS using:

- **VPC**: Single AZ configuration for PoC
- **ALB**: Internet-facing Application Load Balancer
- **EC2**: Auto Scaling Group with t3.medium instances
- **S3**: Bucket for temporary image storage
- **IAM**: Roles with least privilege access

### IAM Permissions

The EC2 IAM role includes permissions for:
- **SageMaker**: `InvokeEndpoint` for Upstage Document OCR
- **S3**: Read/write access to image bucket
- **Bedrock**: `InvokeModel` access to Claude 3.7 Sonnet in us-west-2
- **Systems Manager**: EC2 instance management
- **CloudWatch**: Logging and monitoring

### Authentication

- **No hardcoded credentials**: Uses EC2 IAM roles with STS for secure authentication
- **Cross-region access**: SageMaker endpoints, Bedrock in us-west-2
- **Automatic credential rotation**: Managed by AWS STS

## License

This project is licensed under the MIT License.