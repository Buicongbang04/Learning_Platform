mock_provider "aws" {}

variables {
  prefix = "devops-ex-test0000"
  name   = "reports"
}

run "plans" {
  command = plan
}
