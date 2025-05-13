#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { FrontendStack } from '../lib/frontend-stack';
import { FrontendDeployment } from '../lib/frontend-deployment';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';

const app = new cdk.App();

// Deploy the frontend infrastructure stack
const frontendStack = new FrontendStack(app, 'OceanCleanupFrontendStack');

// Get the deployment configuration
const deploymentConfig = app.node.tryGetContext('deployment') || {};
const sourceRepository = deploymentConfig.sourceRepository || '';
const sourceBranch = deploymentConfig.sourceBranch || 'main';
const buildCommand = deploymentConfig.buildCommand || 'npm run build';

// Only create the pipeline stack if a source repository is specified
if (sourceRepository) {
  // Create a pipeline stack that depends on the frontend stack
  const pipelineStack = new cdk.Stack(app, 'OceanCleanupFrontendPipelineStack', {
    env: frontendStack.environment,
  });

  // Import the S3 bucket from the frontend stack
  const siteBucketName = cdk.Fn.importValue('OceanCleanupFrontendStack:BucketName');
  const siteBucket = s3.Bucket.fromBucketName(pipelineStack, 'ImportedSiteBucket', siteBucketName);

  // Import the CloudFront distribution ID from the frontend stack
  const distributionId = cdk.Fn.importValue('OceanCleanupFrontendStack:DistributionId');

  // Create the deployment pipeline
  new FrontendDeployment(pipelineStack, 'FrontendDeployment', {
    sourceRepository,
    sourceBranch,
    buildCommand,
    siteBucket,
    distributionId,
  });
}