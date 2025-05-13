# Frontend Deployment Guide

This guide explains how to deploy the frontend SPA to AWS CloudFront.

## Manual Deployment

1. Build your frontend application:
   ```
   cd ../frontend
   npm install
   npm run build
   ```

2. Deploy the infrastructure:
   ```
   cd ../infra
   npm install
   npm run build
   cdk deploy
   ```

3. After deployment, the CloudFront distribution URL will be displayed in the output.

## Automated Deployment

To set up automated deployments using AWS CodePipeline:

1. Create a GitHub personal access token with repo permissions.

2. Store the token in AWS Secrets Manager:
   ```
   aws secretsmanager create-secret --name github-token --secret-string YOUR_GITHUB_TOKEN
   ```

3. Update the `cdk.json` file with your GitHub repository information:
   ```json
   {
     "context": {
       "deployment": {
         "sourceRepository": "username/repo",
         "sourceBranch": "main",
         "buildCommand": "npm run build"
       }
     }
   }
   ```

4. Deploy the pipeline:
   ```
   cdk deploy OceanCleanupFrontendPipelineStack
   ```

## Custom Domain Setup

To use a custom domain:

1. Register a domain in Route 53 or configure an existing domain to use Route 53 as the DNS service.

2. Request an SSL certificate in AWS Certificate Manager (ACM) for your domain.

3. Update the `cdk.json` file:
   ```json
   {
     "context": {
       "frontend": {
         "domainName": "your-domain.com",
         "certificateArn": "arn:aws:acm:us-east-1:123456789012:certificate/uuid",
         "enableCustomDomain": true
       }
     }
   }
   ```

4. Deploy the stack:
   ```
   cdk deploy
   ```