output "runtime_role_arn" {
  value = aws_iam_role.runtime.arn
}

output "lambda_role_arn" {
  value = aws_iam_role.lambda.arn
}

output "gateway_role_arn" {
  value = aws_iam_role.gateway.arn
}
