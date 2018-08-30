resource "aws_vpc" "g2-tf-vpc" {
  cidr_block           = "${var.vpc_begin_range}.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags {
    Name = "g2-tf-${var.company}"
  }
}

# Define the private subnets across 3 availability zones
resource "aws_subnet" "subnet-a-app-private" {
  cidr_block        = "${var.vpc_begin_range}.10.0/24"
  availability_zone = "${var.azs[0]}"
  vpc_id            = "${aws_vpc.g2-tf-vpc.id}"

  tags {
    Name = "g2-tf-a-app-private-${var.env}"
  }
}

resource "aws_subnet" "subnet-b-app-private" {
  cidr_block        = "${var.vpc_begin_range}.11.0/24"
  availability_zone = "${var.azs[1]}"
  vpc_id            = "${aws_vpc.g2-tf-vpc.id}"

  tags {
    Name = "g2-tf-b-app-private-${var.env}"
  }
}

resource "aws_subnet" "subnet-c-app-private" {
  cidr_block        = "${var.vpc_begin_range}.12.0/24"
  availability_zone = "${var.azs[2]}"
  vpc_id            = "${aws_vpc.g2-tf-vpc.id}"

  tags {
    Name = "g2-tf-c-app-private-${var.env}"
  }
}

# Define the public subnets across 3 availability zones
resource "aws_subnet" "subnet-a-public" {
  cidr_block              = "${var.vpc_begin_range}.20.0/24"
  availability_zone       = "${var.azs[0]}"
  vpc_id                  = "${aws_vpc.g2-tf-vpc.id}"
  map_public_ip_on_launch = "true"

  tags {
    Name = "g2-tf-a-public-${var.env}"
  }
}

resource "aws_subnet" "subnet-b-public" {
  cidr_block              = "${var.vpc_begin_range}.21.0/24"
  availability_zone       = "${var.azs[1]}"
  vpc_id                  = "${aws_vpc.g2-tf-vpc.id}"
  map_public_ip_on_launch = "true"

  tags {
    Name = "g2-tf-b-public-${var.env}"
  }
}

resource "aws_subnet" "subnet-c-public" {
  cidr_block              = "${var.vpc_begin_range}.22.0/24"
  availability_zone       = "${var.azs[2]}"
  vpc_id                  = "${aws_vpc.g2-tf-vpc.id}"
  map_public_ip_on_launch = "true"

  tags {
    Name = "g2-tf-c-public-${var.env}"
  }
}

# Define the utility server subnets across 3 availability zones
resource "aws_subnet" "subnet-a-util-private" {
  cidr_block        = "${var.vpc_begin_range}.30.0/24"
  availability_zone = "${var.azs[0]}"
  vpc_id            = "${aws_vpc.g2-tf-vpc.id}"

  tags {
    Name = "g2-tf-a-util-private-${var.env}"
  }
}

resource "aws_subnet" "subnet-b-util-private" {
  cidr_block        = "${var.vpc_begin_range}.31.0/24"
  availability_zone = "${var.azs[1]}"
  vpc_id            = "${aws_vpc.g2-tf-vpc.id}"

  tags {
    Name = "g2-tf-b-util-private-${var.env}"
  }
}

resource "aws_subnet" "subnet-c-util-private" {
  cidr_block        = "${var.vpc_begin_range}.32.0/24"
  availability_zone = "${var.azs[2]}"
  vpc_id            = "${aws_vpc.g2-tf-vpc.id}"

  tags {
    Name = "g2-tf-c-util-private-${var.env}"
  }
}

# Define the database server subnets across 3 availability zones
resource "aws_subnet" "subnet-a-db-private" {
  cidr_block        = "${var.vpc_begin_range}.40.0/24"
  availability_zone = "${var.azs[0]}"
  vpc_id            = "${aws_vpc.g2-tf-vpc.id}"

  tags {
    Name = "g2-tf-a-db-private-${var.env}"
  }
}

resource "aws_subnet" "subnet-b-db-private" {
  cidr_block        = "${var.vpc_begin_range}.41.0/24"
  availability_zone = "${var.azs[1]}"
  vpc_id            = "${aws_vpc.g2-tf-vpc.id}"

  tags {
    Name = "g2-tf-b-db-private-${var.env}"
  }
}

resource "aws_subnet" "subnet-c-db-private" {
  cidr_block        = "${var.vpc_begin_range}.42.0/24"
  availability_zone = "${var.azs[2]}"
  vpc_id            = "${aws_vpc.g2-tf-vpc.id}"

  tags {
    Name = "g2-tf-c-db-private-${var.env}"
  }
}

# Define route tables for public and private subnets
resource "aws_route_table" "g2-tf-private" {
  vpc_id = "${aws_vpc.g2-tf-vpc.id}"

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = "${aws_nat_gateway.g2-tf-ngw.id}"
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
    Name = "g2-tf-private"
  }
}

resource "aws_route_table" "g2-tf-public" {
  vpc_id = "${aws_vpc.g2-tf-vpc.id}"

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = "${aws_internet_gateway.g2-tf-igw.id}"
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
    Name = "g2-tf-public"
  }
}

# Associate the private subnets with the appropriate route tables
# Generic private subnets associate to the private route table
resource "aws_route_table_association" "prv-a" {
  subnet_id      = "${aws_subnet.subnet-a-app-private.id}"
  route_table_id = "${aws_route_table.g2-tf-private.id}"
}

resource "aws_route_table_association" "prv-b" {
  subnet_id      = "${aws_subnet.subnet-b-app-private.id}"
  route_table_id = "${aws_route_table.g2-tf-private.id}"
}

resource "aws_route_table_association" "prv-c" {
  subnet_id      = "${aws_subnet.subnet-c-app-private.id}"
  route_table_id = "${aws_route_table.g2-tf-private.id}"
}

# Generic public subnets associate to the public route table
resource "aws_route_table_association" "pub-a" {
  subnet_id      = "${aws_subnet.subnet-a-public.id}"
  route_table_id = "${aws_route_table.g2-tf-public.id}"
}

resource "aws_route_table_association" "pub-b" {
  subnet_id      = "${aws_subnet.subnet-b-public.id}"
  route_table_id = "${aws_route_table.g2-tf-public.id}"
}

resource "aws_route_table_association" "pub-c" {
  subnet_id      = "${aws_subnet.subnet-c-public.id}"
  route_table_id = "${aws_route_table.g2-tf-public.id}"
}

# Database private subnets associate to the private route table
resource "aws_route_table_association" "prv-db-a" {
  subnet_id      = "${aws_subnet.subnet-a-db-private.id}"
  route_table_id = "${aws_route_table.g2-tf-private.id}"
}

resource "aws_route_table_association" "prv-db-b" {
  subnet_id      = "${aws_subnet.subnet-b-db-private.id}"
  route_table_id = "${aws_route_table.g2-tf-private.id}"
}

resource "aws_route_table_association" "prv-db-c" {
  subnet_id      = "${aws_subnet.subnet-c-db-private.id}"
  route_table_id = "${aws_route_table.g2-tf-private.id}"
}

# Utility server private subnets associate to the private route table
resource "aws_route_table_association" "prv-util-a" {
  subnet_id      = "${aws_subnet.subnet-a-util-private.id}"
  route_table_id = "${aws_route_table.g2-tf-private.id}"
}

resource "aws_route_table_association" "prv-util-b" {
  subnet_id      = "${aws_subnet.subnet-b-util-private.id}"
  route_table_id = "${aws_route_table.g2-tf-private.id}"
}

resource "aws_route_table_association" "prv-util-c" {
  subnet_id      = "${aws_subnet.subnet-c-util-private.id}"
  route_table_id = "${aws_route_table.g2-tf-private.id}"
}

# Setup an Elastic IP to associate with the NAT Gateway.
resource "aws_eip" "g2-tf-ngw-eip" {
  vpc = true
}

# Create a NAT Gateway, which will be in public subnet a
resource "aws_nat_gateway" "g2-tf-ngw" {
  allocation_id = "${aws_eip.g2-tf-ngw-eip.id}"
  subnet_id     = "${aws_subnet.subnet-a-public.id}"
  depends_on    = ["aws_internet_gateway.g2-tf-igw", "aws_eip.g2-tf-ngw-eip"]
}

# Create an Internet Gateway
resource "aws_internet_gateway" "g2-tf-igw" {
  vpc_id = "${aws_vpc.g2-tf-vpc.id}"
}

# Create an All Hosts security group that allows traffic to flow freely within the VPC
# NOTE: Depending upon requirements, this may need to be adjusted to be more restrictive.
resource "aws_security_group" "vpc-all-hosts-sg" {
  name   = "g2-tf-all-hosts-${var.env}"
  vpc_id = "${aws_vpc.g2-tf-vpc.id}"

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["${var.vpc_begin_range}.0.0/16"]
    #security_groups = ["${var.openvpn-access-sg}"]
  }

  ingress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    self      = true
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags {
    Name = "g2-tf-all-hosts"
  }
}

resource "aws_security_group" "g2-access-sg" {
  name   = "g2-access"
  vpc_id = "${aws_vpc.g2-tf-vpc.id}"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["216.236.254.242/32","107.23.51.203/32"]
  }

  egress {
    from_port   = -1
    to_port     = -1
    protocol    = "icmp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags {
    Name = "g2-access"
  }
}

#Create proxy-sg
resource "aws_security_group" "proxy-sg" {
  name   = "proxy-sg-${var.env}"
  vpc_id = "${aws_vpc.g2-tf-vpc.id}"

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["${var.vpc_begin_range}.0.0/16"]
    #security_groups = ["${var.openvpn-access-sg}"]
  }

  ingress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    self      = true
  }

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
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags {
    Name = "proxy-sg-${var.env}"
  }
}

#Create django-sg
resource "aws_security_group" "django-sg" {
  name   = "django-sg-${var.env}"
  vpc_id = "${aws_vpc.g2-tf-vpc.id}"

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["${var.vpc_begin_range}.0.0/16"]
    #security_groups = ["${var.openvpn-access-sg}"]
  }

  ingress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    self      = true
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags {
    Name = "django-sg-${var.env}"
  }
}

#Create airflow-sg
resource "aws_security_group" "airflow-sg" {
  name   = "airflow-sg-${var.env}"
  vpc_id = "${aws_vpc.g2-tf-vpc.id}"

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["${var.vpc_begin_range}.0.0/16"]
    #security_groups = ["${var.openvpn-access-sg}"]
  }

  ingress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    self      = true
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags {
    Name = "airflow-sg-${var.env}"
  }
}

#Create celery-sg
resource "aws_security_group" "celery-sg" {
  name   = "celery-sg-${var.env}"
  vpc_id = "${aws_vpc.g2-tf-vpc.id}"

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["${var.vpc_begin_range}.0.0/16"]
    #security_groups = ["${var.openvpn-access-sg}"]
  }

  ingress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    self      = true
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags {
    Name = "celery-sg-${var.env}"
  }
}

#Create rabbitmq-sg
resource "aws_security_group" "rabbitmq-sg" {
  name   = "rabbitmq-sg-${var.env}"
  vpc_id = "${aws_vpc.g2-tf-vpc.id}"

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["${var.vpc_begin_range}.0.0/16"]
    #security_groups = ["${var.openvpn-access-sg}"]
  }

  ingress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    self      = true
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags {
    Name = "rabbitmq-sg-${var.env}"
  }
}

#Create touchforms-sg
resource "aws_security_group" "touchforms-sg" {
  name   = "touchforms-sg-${var.env}"
  vpc_id = "${aws_vpc.g2-tf-vpc.id}"

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["${var.vpc_begin_range}.0.0/16"]
    #security_groups = ["${var.openvpn-access-sg}"]
  }

  ingress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    self      = true
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags {
    Name = "touchforms-sg-${var.env}"
  }
}

#Create es-sg
resource "aws_security_group" "es-sg" {
  name   = "es-sg-${var.env}"
  vpc_id = "${aws_vpc.g2-tf-vpc.id}"

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["${var.vpc_begin_range}.0.0/16"]
    #security_groups = ["${var.openvpn-access-sg}"]
  }

  ingress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    self      = true
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags {
    Name = "es-sg-${var.env}"
  }
}

#Create formplayer-sg
resource "aws_security_group" "formplayer-sg" {
  name   = "formplayer-sg-${var.env}"
  vpc_id = "${aws_vpc.g2-tf-vpc.id}"

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["${var.vpc_begin_range}.0.0/16"]
    #security_groups = ["${var.openvpn-access-sg}"]
  }

  ingress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    self      = true
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags {
    Name = "formplayer-sg-${var.env}"
  }
}

#Create kafka-sg
resource "aws_security_group" "kafka-sg" {
  name   = "kafka-sg-${var.env}"
  vpc_id = "${aws_vpc.g2-tf-vpc.id}"

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["${var.vpc_begin_range}.0.0/16"]
    #security_groups = ["${var.openvpn-access-sg}"]
  }

  ingress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    self      = true
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags {
    Name = "kafka-sg-${var.env}"
  }
}

#Create pillowtop-sg
resource "aws_security_group" "pillowtop-sg" {
  name   = "pillowtop-sg-${var.env}"
  vpc_id = "${aws_vpc.g2-tf-vpc.id}"

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["${var.vpc_begin_range}.0.0/16"]
    #security_groups = ["${var.openvpn-access-sg}"]
  }

  ingress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    self      = true
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags {
    Name = "pillowtop-sg-${var.env}"
  }
}
