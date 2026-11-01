output "instance_id" {
  value = aws_instance.sandbox.id
}

output "budget_name" {
  value = aws_budgets_budget.monthly.name
}
