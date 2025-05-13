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

# Bootstrap the AWS environment
echo "Bootstrapping AWS environment..."
npx cdk bootstrap