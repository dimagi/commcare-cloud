resource "aws_vpc" "main" {
  cidr_block           = "${var.vpc_begin_range}.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags {
    Name = "vpc-${var.env}"
  }
}

# Define the private subnets across 3 availability zones
resource "aws_subnet" "subnet-a-app-private" {
  cidr_block        = "${var.vpc_begin_range}.10.0/24"
  availability_zone = "${var.azs[0]}"
  vpc_id            = "${aws_vpc.main.id}"

  tags {
    Name = "subnet-a-app-private-${var.env}"
  }
}

resource "aws_subnet" "subnet-b-app-private" {
  cidr_block        = "${var.vpc_begin_range}.11.0/24"
  availability_zone = "${var.azs[1]}"
  vpc_id            = "${aws_vpc.main.id}"

  tags {
    Name = "subnet-b-app-private-${var.env}"
  }
}

resource "aws_subnet" "subnet-c-app-private" {
  cidr_block        = "${var.vpc_begin_range}.12.0/24"
  availability_zone = "${var.azs[2]}"
  vpc_id            = "${aws_vpc.main.id}"

  tags {
    Name = "subnet-c-app-private-${var.env}"
  }
}

# Define the public subnets across 3 availability zones
resource "aws_subnet" "subnet-a-public" {
  cidr_block              = "${var.vpc_begin_range}.20.0/24"
  availability_zone       = "${var.azs[0]}"
  vpc_id                  = "${aws_vpc.main.id}"
  map_public_ip_on_launch = "true"

  tags {
    Name = "subnet-a-public-${var.env}"
  }
}

resource "aws_subnet" "subnet-b-public" {
  cidr_block              = "${var.vpc_begin_range}.21.0/24"
  availability_zone       = "${var.azs[1]}"
  vpc_id                  = "${aws_vpc.main.id}"
  map_public_ip_on_launch = "true"

  tags {
    Name = "subnet-b-public-${var.env}"
  }
}

resource "aws_subnet" "subnet-c-public" {
  cidr_block              = "${var.vpc_begin_range}.22.0/24"
  availability_zone       = "${var.azs[2]}"
  vpc_id                  = "${aws_vpc.main.id}"
  map_public_ip_on_launch = "true"

  tags {
    Name = "subnet-c-public-${var.env}"
  }
}

# Define the utility server subnets across 3 availability zones
resource "aws_subnet" "subnet-a-util-private" {
  cidr_block        = "${var.vpc_begin_range}.30.0/24"
  availability_zone = "${var.azs[0]}"
  vpc_id            = "${aws_vpc.main.id}"

  tags {
    Name = "subnet-a-util-private-${var.env}"
  }
}

resource "aws_subnet" "subnet-b-util-private" {
  cidr_block        = "${var.vpc_begin_range}.31.0/24"
  availability_zone = "${var.azs[1]}"
  vpc_id            = "${aws_vpc.main.id}"

  tags {
    Name = "subnet-b-util-private-${var.env}"
  }
}

resource "aws_subnet" "subnet-c-util-private" {
  cidr_block        = "${var.vpc_begin_range}.32.0/24"
  availability_zone = "${var.azs[2]}"
  vpc_id            = "${aws_vpc.main.id}"

  tags {
    Name = "subnet-c-util-private-${var.env}"
  }
}

# Define the database server subnets across 3 availability zones
resource "aws_subnet" "subnet-a-db-private" {
  cidr_block        = "${var.vpc_begin_range}.40.0/24"
  availability_zone = "${var.azs[0]}"
  vpc_id            = "${aws_vpc.main.id}"

  tags {
    Name = "subnet-a-db-private-${var.env}"
  }
}

resource "aws_subnet" "subnet-b-db-private" {
  cidr_block        = "${var.vpc_begin_range}.41.0/24"
  availability_zone = "${var.azs[1]}"
  vpc_id            = "${aws_vpc.main.id}"

  tags {
    Name = "subnet-b-db-private-${var.env}"
  }
}

resource "aws_subnet" "subnet-c-db-private" {
  cidr_block        = "${var.vpc_begin_range}.42.0/24"
  availability_zone = "${var.azs[2]}"
  vpc_id            = "${aws_vpc.main.id}"

  tags {
    Name = "subnet-c-db-private-${var.env}"
  }
}

# Define route tables for public and private subnets
resource "aws_route_table" "private" {
  vpc_id = "${aws_vpc.main.id}"

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = "${aws_nat_gateway.main.id}"
  }

  # Rackspace routing
  route {
    cidr_block = "172.24.16.0/22"
    gateway_id = "vgw-8dd726e4"
  }

  route {
    cidr_block = "172.24.32.0/22"
    gateway_id = "vgw-8dd726e4"
  }
  # /Rackspace routing

  tags {
    Name = "private-${var.env}"
  }
}

resource "aws_route_table" "public" {
  vpc_id = "${aws_vpc.main.id}"

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = "${aws_internet_gateway.main.id}"
  }

  # Rackspace routing
  route {
    cidr_block = "172.24.16.0/22"
    gateway_id = "vgw-8dd726e4"
  }

  route {
    cidr_block = "172.24.32.0/22"
    gateway_id = "vgw-8dd726e4"
  }
  # /Rackspace routing

  tags {
    Name = "public-${var.env}"
  }
}

# Associate the private subnets with the appropriate route tables
# Generic private subnets associate to the private route table
resource "aws_route_table_association" "prv-a" {
  subnet_id      = "${aws_subnet.subnet-a-app-private.id}"
  route_table_id = "${aws_route_table.private.id}"
}

resource "aws_route_table_association" "prv-b" {
  subnet_id      = "${aws_subnet.subnet-b-app-private.id}"
  route_table_id = "${aws_route_table.private.id}"
}

resource "aws_route_table_association" "prv-c" {
  subnet_id      = "${aws_subnet.subnet-c-app-private.id}"
  route_table_id = "${aws_route_table.private.id}"
}

# Generic public subnets associate to the public route table
resource "aws_route_table_association" "pub-a" {
  subnet_id      = "${aws_subnet.subnet-a-public.id}"
  route_table_id = "${aws_route_table.public.id}"
}

resource "aws_route_table_association" "pub-b" {
  subnet_id      = "${aws_subnet.subnet-b-public.id}"
  route_table_id = "${aws_route_table.public.id}"
}

resource "aws_route_table_association" "pub-c" {
  subnet_id      = "${aws_subnet.subnet-c-public.id}"
  route_table_id = "${aws_route_table.public.id}"
}

# Database private subnets associate to the private route table
resource "aws_route_table_association" "prv-db-a" {
  subnet_id      = "${aws_subnet.subnet-a-db-private.id}"
  route_table_id = "${aws_route_table.private.id}"
}

resource "aws_route_table_association" "prv-db-b" {
  subnet_id      = "${aws_subnet.subnet-b-db-private.id}"
  route_table_id = "${aws_route_table.private.id}"
}

resource "aws_route_table_association" "prv-db-c" {
  subnet_id      = "${aws_subnet.subnet-c-db-private.id}"
  route_table_id = "${aws_route_table.private.id}"
}

# Utility server private subnets associate to the private route table
resource "aws_route_table_association" "prv-util-a" {
  subnet_id      = "${aws_subnet.subnet-a-util-private.id}"
  route_table_id = "${aws_route_table.private.id}"
}

resource "aws_route_table_association" "prv-util-b" {
  subnet_id      = "${aws_subnet.subnet-b-util-private.id}"
  route_table_id = "${aws_route_table.private.id}"
}

resource "aws_route_table_association" "prv-util-c" {
  subnet_id      = "${aws_subnet.subnet-c-util-private.id}"
  route_table_id = "${aws_route_table.private.id}"
}

# Setup an Elastic IP to associate with the NAT Gateway.
resource "aws_eip" "nat_gateway" {
  vpc = true
}

# Create a NAT Gateway, which will be in public subnet a
resource "aws_nat_gateway" "main" {
  allocation_id = "${aws_eip.nat_gateway.id}"
  subnet_id     = "${aws_subnet.subnet-a-public.id}"
  depends_on    = ["aws_internet_gateway.main", "aws_eip.nat_gateway"]
}

# Create an Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = "${aws_vpc.main.id}"
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

  egress {
      from_port = 0
      to_port = 0
      protocol = "-1"
      cidr_blocks = ["0.0.0.0/0"]
  }

  tags {
    Name = "proxy-sg-${var.env}"
  }
}

resource "aws_security_group" "rds" {
  name   = "rds-${var.env}"
  vpc_id = "${aws_vpc.main.id}"

  ingress {
    from_port = "5432"
    to_port = "5432"
    protocol = "tcp"
    cidr_blocks = [
      "${aws_subnet.subnet-a-app-private.cidr_block}",
      "${aws_subnet.subnet-b-app-private.cidr_block}",
      "${aws_subnet.subnet-c-app-private.cidr_block}"
    ]
    ipv6_cidr_blocks = ["::/0"]
  }

  egress {
      from_port = 0
      to_port = 0
      protocol = "-1"
      cidr_blocks = ["0.0.0.0/0"]
  }

  lifecycle {
    ignore_changes = ["name", "description"]
  }
  tags {
    Name = "rds-${var.env}"
  }
}
