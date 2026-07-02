output "sqs_queue_url" {
  description = "SQS FIFO queue URL - set as SQS_QUEUE_URL env var on the API"
  value       = aws_sqs_queue.jobs.url
}

output "sqs_queue_arn" {
  description = "SQS FIFO queue ARN"
  value       = aws_sqs_queue.jobs.arn
}

output "sqs_dlq_url" {
  description = "Dead letter queue URL for failed jobs"
  value       = aws_sqs_queue.jobs_dlq.url
}

output "ecr_worker_repository_url" {
  description = "ECR repo URL for the Lambda worker image"
  value       = aws_ecr_repository.worker.repository_url
}

output "lambda_function_arn" {
  description = "Lambda worker function ARN"
  value       = aws_lambda_function.worker.arn
}

output "lambda_function_name" {
  description = "Lambda worker function name - used by deploy.yml to update code"
  value       = aws_lambda_function.worker.function_name
}

output "efs_file_system_id" {
  description = "EFS file system ID - attach to ECS task for shared DuckDB access"
  value       = aws_efs_file_system.data.id
}

output "efs_access_point_arn" {
  description = "EFS access point ARN"
  value       = aws_efs_access_point.shelterpulse.arn
}
