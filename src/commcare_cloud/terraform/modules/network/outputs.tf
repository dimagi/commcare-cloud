output "subnets-app-private" {
  value = "${zipmap(var.az_codes, aws_subnet.subnet-app-private.*.id)}"
}

output "subnets-public" {
  value = "${zipmap(var.az_codes, aws_subnet.subnet-public.*.id)}"
}

output "subnets-db-private" {
  value = "${zipmap(var.az_codes, aws_subnet.subnet-db-private.*.id)}"
}

output "vpc-id" {
  value = "${aws_vpc.main.id}"
}

output "vpc-cidr" {
  value = "${aws_vpc.main.cidr_block}"
}

output "proxy-sg" {
  value = "${aws_security_group.proxy-sg.id}"
}

output "rds-sg" {
  value = "${aws_security_group.rds.id}"
}

output "elasticache-sg" {
  value = "${aws_security_group.elasticache.id}"
}

output "app-private-sg" {
  value = "${aws_security_group.app-private.id}"
}

output "db-private-sg" {
  value = "${aws_security_group.db-private.id}"
}

output "ssh-sg" {
  value = "${aws_security_group.ssh.id}"
}

output "vpn-connections-sg" {
  value = "${aws_security_group.vpn_connections.id}"
}
