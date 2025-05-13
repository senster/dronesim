# Frontend Infrastructure

This directory contains the AWS CDK infrastructure code for deploying the Ocean Cleanup Hackathon frontend application.

## Architecture

The frontend is deployed as a Single Page Application (SPA) using the following AWS services:
- **S3**: Stores the static website files
- **CloudFront**: Content delivery network for global distribution
- **Route53**: (Optional) For custom domain configuration
- **ACM**: (Optional) For SSL certificate management

## Prerequisites

- AWS CLI configured with appropriate credentials
- Node.js 14.x or later
- AWS CDK v2 installed globally (`npm install -g aws-cdk`) or use the provided scripts

## Deployment

### Using the provided scripts:

1. Bootstrap your AWS environment (if not already done):
   ```
   ./bin/bootstrap.sh
   ```

2. Deploy the stack:
   ```
   ./bin/deploy.sh
   ```

### Manual deployment:

1. Install dependencies:
   ```
   cd infra
   npm install
   ```

2. Build the TypeScript code:
   ```
   npm run build
   ```

3. Deploy the stack:
   ```
   npx cdk deploy
   ```

## Frontend Development

1. Create a frontend directory at the same level as the infra directory:
   ```
   mkdir -p ../frontend
   ```

2. Initialize your frontend application (React, Vue, Angular, etc.) in this directory.

3. Build your frontend application:
   ```
   cd ../frontend
   npm run build
   ```

4. The infrastructure will automatically deploy the contents of the `frontend/build` directory.

## Configuration

Edit the `cdk.json` file to customize deployment parameters:

```json
{
  "context": {
    "frontend": {
      "domainName": "your-domain.com",
      "certificateArn": "arn:aws:acm:us-east-1:123456789012:certificate/uuid",
      "enableCustomDomain": true,
      "priceClass": "PriceClass_100"
    }
  }
}
```