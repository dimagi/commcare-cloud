resource "aws_vpc" "main" {
  cidr_block           = "${var.vpc_begin_range}.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags {
    Name = "vpc-${var.env}"
  }
}

resource "aws_subnet" "subnet-app-private" {
  count = "${length(var.azs)}"
  cidr_block        = "${var.vpc_begin_range}.1${count.index}.0/24"
  availability_zone = "${var.azs[count.index]}"
  vpc_id            = "${aws_vpc.main.id}"

  tags {
    Name = "subnet-${var.az_codes[count.index]}-app-private-${var.env}"
  }
}

resource "aws_subnet" "subnet-public" {
  count = "${length(var.azs)}"
  cidr_block              = "${var.vpc_begin_range}.2${count.index}.0/24"
  availability_zone       = "${var.azs[count.index]}"
  vpc_id                  = "${aws_vpc.main.id}"
  map_public_ip_on_launch = "true"

  tags {
    Name = "subnet-${var.az_codes[count.index]}-public-${var.env}"
  }
}

resource "aws_subnet" "subnet-db-private" {
  count = "${length(var.azs)}"
  cidr_block        = "${var.vpc_begin_range}.4${count.index}.0/24"
  availability_zone = "${var.azs[count.index]}"
  vpc_id            = "${aws_vpc.main.id}"

  tags {
    Name = "subnet-${var.az_codes[count.index]}-db-private-${var.env}"
  }
}

# Define route tables for public and private subnets
resource "aws_route_table" "private" {
  vpc_id = "${aws_vpc.main.id}"

  route = [{
    cidr_block = "0.0.0.0/0"
    nat_gateway_id = "${aws_nat_gateway.main.id}"
  }, "${var.external_routes}"]

  tags {
    Name = "private-${var.env}"
  }
}

resource "aws_route_table" "public" {
  vpc_id = "${aws_vpc.main.id}"

  route = [{
    cidr_block = "0.0.0.0/0"
    gateway_id = "${aws_internet_gateway.main.id}"
  }, "${var.external_routes}"]

  tags {
    Name = "public-${var.env}"
  }
}

# Associate the private subnets with the appropriate route tables
# Generic private subnets associate to the private route table

resource "aws_route_table_association" "app-private" {
  count = "${length(var.azs)}"
  subnet_id      = "${aws_subnet.subnet-app-private.*.id[count.index]}"
  route_table_id = "${aws_route_table.private.id}"
}

resource "aws_route_table_association" "public" {
  count = "${length(var.azs)}"
  subnet_id      = "${aws_subnet.subnet-public.*.id[count.index]}"
  route_table_id = "${aws_route_table.public.id}"
}

resource "aws_route_table_association" "db-private" {
  count = "${length(var.azs)}"
  subnet_id      = "${aws_subnet.subnet-db-private.*.id[count.index]}"
  route_table_id = "${aws_route_table.private.id}"
}

# Setup an Elastic IP to associate with the NAT Gateway.
resource "aws_eip" "nat_gateway" {
  vpc = true
}

# Create a NAT Gateway, which will be in public subnet a
resource "aws_nat_gateway" "main" {
  allocation_id = "${aws_eip.nat_gateway.id}"
  subnet_id     = "${aws_subnet.subnet-public.*.id[0]}"
  depends_on    = ["aws_internet_gateway.main", "aws_eip.nat_gateway"]
}

# Create an Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = "${aws_vpc.main.id}"
}

locals {
  default_egress = [{
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }]
}

resource "aws_security_group" "proxy-sg" {
  name   = "proxy-sg-${var.env}"
  vpc_id = "${aws_vpc.main.id}"

  ingress {
    from_port =         "80"
    to_port =           "80"
    protocol =          "tcp"
    cidr_blocks =       ["0.0.0.0/0"]
    ipv6_cidr_blocks =  ["::/0"]
  }

  ingress {
    protocol =          "tcp"
    to_port =           "443"
    from_port =         "443"
    cidr_blocks =       ["0.0.0.0/0"]
    ipv6_cidr_blocks =  ["::/0"]
  }

  egress = "${local.default_egress}"

  tags {
    Name = "proxy-sg-${var.env}"
  }
}

resource "aws_security_group" "ssh" {
  name   = "ssh-sg-${var.env}"
  vpc_id = "${aws_vpc.main.id}"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["${aws_vpc.main.cidr_block}"]
  }

  tags {
    Name = "ssh-sg-${var.env}"
  }
}

resource "aws_security_group" "app-private" {
  name   = "app-private-sg-${var.env}"
  vpc_id = "${aws_vpc.main.id}"

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["${aws_vpc.main.cidr_block}"]
  }

  ingress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    self      = true
  }

  egress = "${local.default_egress}"

  lifecycle {
    ignore_changes = ["name", "description"]
  }

  tags {
    Name = "app-private-sg-${var.env}"
  }
}


resource "aws_security_group" "rds" {
  name   = "rds-${var.env}"
  vpc_id = "${aws_vpc.main.id}"

  ingress {
    from_port = "5432"
    to_port = "5432"
    protocol = "tcp"
    cidr_blocks = ["${aws_subnet.subnet-app-private.*.cidr_block}"]
    ipv6_cidr_blocks = ["::/0"]
  }

  egress = "${local.default_egress}"

  lifecycle {
    ignore_changes = ["name", "description"]
  }
  tags {
    Name = "rds-${var.env}"
  }
}

resource "aws_security_group" "elasticache" {
  name   = "elasticache-${var.env}"
  vpc_id = "${aws_vpc.main.id}"

  ingress {
    from_port = "6379"
    to_port = "6379"
    protocol = "tcp"
    cidr_blocks = ["${aws_subnet.subnet-app-private.*.cidr_block}"]
    ipv6_cidr_blocks = ["::/0"]
  }

  egress = "${local.default_egress}"

  tags {
    Name = "elasticache-${var.env}"
  }
}
