resource "aws_db_subnet_group" "db" {
  name       = "${var.prefix}-db"
  subnet_ids = [for subnet in aws_subnet.db : subnet.id]
}

# TODO 5: database không có IP public, mã hoá lưu trữ, mật khẩu không nằm trong code hay state.
resource "aws_db_instance" "db" {
  identifier              = "${var.prefix}-olist"
  engine                  = "postgres"
  engine_version          = "16"
  instance_class          = "db.t4g.micro"
  allocated_storage       = 20
  db_name                 = "olist"
  username                = "olist"
  password                = "olist-dev-123"
  db_subnet_group_name    = aws_db_subnet_group.db.name
  vpc_security_group_ids  = [aws_security_group.db.id]
  publicly_accessible     = true
  storage_encrypted       = false
  backup_retention_period = 7
  skip_final_snapshot     = true
}
