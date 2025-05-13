#!/bin/bash

# Exit on error
set -e

# Navigate to the infra directory
cd "$(dirname "$0")/.."

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
  echo "Installing dependencies..."
  npm install
fi

# Build TypeScript files
echo "Building TypeScript files..."
npm run build

# Deploy the stack
echo "Deploying CloudFront frontend stack..."
npx cdk deploy OceanCleanupFrontendStack --require-approval never