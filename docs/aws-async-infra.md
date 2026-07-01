# AWS Infrastructure Needed for Async Workers

**Status:** NOT YET CREATED (as of 2026-06-30)
**Estimate:** 30 min setup, $0/month (all free tier)

## Resources to Create

### 1. SQS FIFO Queue
```bash
aws sqs create-queue \
  --queue-name shelterpulse-optimization.fifo \
  --attributes FifoQueue=true,ContentBasedDeduplication=false,VisibilityTimeout=120 \
  --region us-east-1
```

### 2. EFS File System
```bash
# Create file system
aws efs create-file-system \
  --performance-mode generalPurpose \
  --throughput-mode bursting \
  --tags Key=Name,Value=shelterpulse-data \
  --region us-east-1

# Create access point for DuckDB
aws efs create-access-point \
  --file-system-id fs-XXXXX \
  --posix-user Uid=1000,Gid=1000 \
  --root-directory Path=/shelterpulse,CreationInfo={OwnerUid=1000,OwnerGid=1000,Permissions=755}
```

### 3. Lambda Function
```bash
# Build and push image to ECR
docker build -f lambda/Dockerfile -t shelterpulse-worker .
aws ecr create-repository --repository-name shelterpulse-worker
docker tag shelterpulse-worker:latest $ECR_REPO:latest
docker push $ECR_REPO:latest

# Create function (VPC + EFS)
aws lambda create-function \
  --function-name shelterpulse-worker \
  --package-type Image \
  --code ImageUri=$ECR_REPO:latest \
  --role $LAMBDA_ROLE_ARN \
  --timeout 120 \
  --memory-size 1024 \
  --vpc-config SubnetIds=$SUBNET_IDS,SecurityGroupIds=$SG_ID \
  --file-system-configs Arn=$EFS_ACCESS_POINT_ARN,LocalMountPath=/mnt/efs \
  --environment Variables={API_URL=$API_URL,INTERNAL_KEY=$SECRET_KEY,DUCKDB_PATH=/mnt/efs/shelterpulse.duckdb}
```

### 4. SQS -> Lambda Event Source Mapping
```bash
aws lambda create-event-source-mapping \
  --function-name shelterpulse-worker \
  --event-source-arn arn:aws:sqs:us-east-1:ACCOUNT:shelterpulse-optimization.fifo \
  --batch-size 1
```

### 5. IAM Role for Lambda
Needs:
- `AWSLambdaBasicExecutionRole` (CloudWatch logs)
- `AWSLambdaVPCAccessExecutionRole` (VPC networking)
- `elasticfilesystem:ClientMount` + `ClientWrite` on the EFS
- `sqs:ReceiveMessage`, `sqs:DeleteMessage`, `sqs:GetQueueAttributes` on the queue

### 6. ECS Task Definition Update (EFS mount for API)
The API needs read access to the same EFS for DuckDB queries:
- Add EFS volume to existing task definition
- Mount at `/mnt/efs` in the API container
- Set `DUCKDB_PATH=/mnt/efs/shelterpulse.duckdb`

### 7. API Environment Variables (production)
Add to ECS Express Mode service:
- `QUEUE_BACKEND=sqs`
- `SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/ACCOUNT/shelterpulse-optimization.fifo`
- `INTERNAL_KEY=<generated-32-char-secret>`
- `DUCKDB_PATH=/mnt/efs/shelterpulse.duckdb`

## Cost Estimate

| Resource | Monthly cost |
|----------|-------------|
| SQS | $0 (1M requests free) |
| Lambda | $0 (1M invocations + 400K GB-s free) |
| EFS | ~$0.01 (< 100KB data) |
| **Total** | **~$0.01** |

## When to Create

Create these resources when Issue #44 (DuckDB persistence) is complete and we're
ready to promote the full async stack to production. Until then, docker-compose
with RabbitMQ is sufficient for development and demo.

## Prerequisites

- AWS session authenticated (`aws login`)
- VPC subnets and security groups from existing ECS Express Mode setup
- ECR repository for the Lambda image
