resource "aws_vpc" "main" {
  cidr_block           = "${var.vpc_begin_range}.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "vpc-${var.env}"
  }
}

resource "aws_subnet" "subnet-app-private" {
  count             = length(var.azs)
  cidr_block        = "${var.vpc_begin_range}.1${count.index}.0/24"
  availability_zone = var.azs[count.index]
  vpc_id            = aws_vpc.main.id

  tags = {
    Name = "subnet-${var.az_codes[count.index]}-app-private-${var.env}"
  }
}

resource "aws_subnet" "subnet-public" {
  count                   = length(var.azs)
  cidr_block              = "${var.vpc_begin_range}.2${count.index}.0/24"
  availability_zone       = var.azs[count.index]
  vpc_id                  = aws_vpc.main.id
  map_public_ip_on_launch = "true"

  tags = {
    Name = "subnet-${var.az_codes[count.index]}-public-${var.env}"
  }
}

resource "aws_subnet" "subnet-db-private" {
  count             = length(var.azs)
  cidr_block        = "${var.vpc_begin_range}.4${count.index}.0/24"
  availability_zone = var.azs[count.index]
  vpc_id            = aws_vpc.main.id

  tags = {
    Name = "subnet-${var.az_codes[count.index]}-db-private-${var.env}"
  }
}

resource "aws_vpn_gateway" "vpn_connections" {
  count           = length(var.vpn_connections)
  vpc_id          = aws_vpc.main.id
  amazon_side_asn = var.vpn_connections[count.index]["amazon_side_asn"]
  tags = {
    Name = "${var.vpn_connections[count.index]["name"]}-${var.env}"
  }
}

resource "aws_customer_gateway" "vpn_connections" {
  count      = length(var.vpn_connections)
  bgp_asn    = var.vpn_connections[count.index]["bgp_asn"]
  ip_address = var.vpn_connections[count.index]["ip_address"]
  type       = var.vpn_connections[count.index]["type"]
  tags = {
    Name = "${var.vpn_connections[count.index]["name"]}-${var.env}"
  }
}

resource "aws_vpn_connection" "vpn_connections" {
  count               = length(var.vpn_connections)
  customer_gateway_id = aws_customer_gateway.vpn_connections[count.index].id
  vpn_gateway_id      = aws_vpn_gateway.vpn_connections[count.index].id
  type                = var.vpn_connections[count.index]["type"]
  static_routes_only  = true
  tags = {
    Name = "${var.vpn_connections[count.index]["name"]}-${var.env}"
  }
}

resource "aws_vpn_connection_route" "vpn_connections" {
  count                  = length(var.vpn_connection_routes)
  destination_cidr_block = var.vpn_connection_routes[count.index]["destination_cidr_block"]
  vpn_connection_id      = aws_vpn_connection.vpn_connections[var.vpn_connection_routes[count.index]["vpn_connection_index"]].id
}

resource "aws_security_group" "vpn_connections" {
  count  = length(var.vpn_connections) == 0 ? 0 : 1
  name   = "vpn-connections-sg-${var.env}"
  vpc_id = aws_vpc.main.id
  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = aws_vpn_connection_route.vpn_connections.*.destination_cidr_block
  }
  tags = {
    Name = "vpn-connections-sg-${var.env}"
  }
}

# Define route tables for public and private subnets
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  dynamic "route" {
    for_each = var.external_routes
    content {
      # TF-UPGRADE-TODO: The automatic upgrade tool can't predict
      # which keys might be set in maps assigned here, so it has
      # produced a comprehensive set here. Consider simplifying
      # this after confirming which keys can be set in practice.

      cidr_block                 = lookup(route.value, "cidr_block", null)
      destination_prefix_list_id = lookup(route.value, "destination_prefix_list_id", null)
      egress_only_gateway_id     = lookup(route.value, "egress_only_gateway_id", null)
      gateway_id                 = lookup(route.value, "gateway_id", null)
      instance_id                = lookup(route.value, "instance_id", null)
      ipv6_cidr_block            = lookup(route.value, "ipv6_cidr_block", null)
      local_gateway_id           = lookup(route.value, "local_gateway_id", null)
      nat_gateway_id             = lookup(route.value, "nat_gateway_id", aws_nat_gateway.main.id)
      network_interface_id       = lookup(route.value, "network_interface_id", null)
      transit_gateway_id         = lookup(route.value, "transit_gateway_id", null)
      vpc_endpoint_id            = lookup(route.value, "vpc_endpoint_id", null)
      vpc_peering_connection_id  = lookup(route.value, "vpc_peering_connection_id", null)
    }
  }

  tags = {
    Name = "private-${var.env}"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  dynamic "route" {
    for_each = var.external_routes
    content {
      # TF-UPGRADE-TODO: The automatic upgrade tool can't predict
      # which keys might be set in maps assigned here, so it has
      # produced a comprehensive set here. Consider simplifying
      # this after confirming which keys can be set in practice.

      carrier_gateway_id         = lookup(route.value, "carrier_gateway_id", null)
      cidr_block                 = lookup(route.value, "cidr_block", null)
      destination_prefix_list_id = lookup(route.value, "destination_prefix_list_id", null)
      egress_only_gateway_id     = lookup(route.value, "egress_only_gateway_id", null)
      gateway_id                 = lookup(route.value, "gateway_id", aws_internet_gateway.main.id)
      instance_id                = lookup(route.value, "instance_id", null)
      ipv6_cidr_block            = lookup(route.value, "ipv6_cidr_block", null)
      local_gateway_id           = lookup(route.value, "local_gateway_id", null)
      nat_gateway_id             = lookup(route.value, "nat_gateway_id", null)
      network_interface_id       = lookup(route.value, "network_interface_id", null)
      transit_gateway_id         = lookup(route.value, "transit_gateway_id", null)
      vpc_endpoint_id            = lookup(route.value, "vpc_endpoint_id", null)
      vpc_peering_connection_id  = lookup(route.value, "vpc_peering_connection_id", null)
    }
  }

  tags = {
    Name = "public-${var.env}"
  }
}

# Associate the private subnets with the appropriate route tables
# Generic private subnets associate to the private route table

resource "aws_route_table_association" "app-private" {
  count          = length(var.azs)
  subnet_id      = aws_subnet.subnet-app-private[count.index].id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table_association" "public" {
  count          = length(var.azs)
  subnet_id      = aws_subnet.subnet-public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "db-private" {
  count          = length(var.azs)
  subnet_id      = aws_subnet.subnet-db-private[count.index].id
  route_table_id = aws_route_table.private.id
}

# Setup an Elastic IP to associate with the NAT Gateway.
resource "aws_eip" "nat_gateway" {
  vpc = true
  tags = {
    Name        = "nat-gateway-ip-${var.env}"
    Environment = "production"
    Group       = "Network"
  }
}

# Create a NAT Gateway, which will be in public subnet a
resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat_gateway.id
  subnet_id     = aws_subnet.subnet-public[0].id
  depends_on = [
    aws_internet_gateway.main,
    aws_eip.nat_gateway,
  ]
  tags = {
    Name        = "nat-gateway-${var.env}"
    Environment = "production"
    Group       = "Network"
  }
}

# Create an Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags = {
    Name        = "internet-gateway-${var.env}"
    Environment = "production"
    Group       = "Network"
  }
}

locals {
  default_egress = [
    {
      from_port   = 0
      to_port     = 0
      protocol    = "-1"
      cidr_blocks = ["0.0.0.0/0"]
    },
  ]
}

resource "aws_security_group" "proxy-sg" {
  name   = "proxy-sg-${var.env}"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [aws_vpc.main.cidr_block]
  }

  dynamic "egress" {
    for_each = local.default_egress
    content {
      # TF-UPGRADE-TODO: The automatic upgrade tool can't predict
      # which keys might be set in maps assigned here, so it has
      # produced a comprehensive set here. Consider simplifying
      # this after confirming which keys can be set in practice.

      cidr_blocks      = lookup(egress.value, "cidr_blocks", null)
      description      = lookup(egress.value, "description", null)
      from_port        = lookup(egress.value, "from_port", null)
      ipv6_cidr_blocks = lookup(egress.value, "ipv6_cidr_blocks", null)
      prefix_list_ids  = lookup(egress.value, "prefix_list_ids", null)
      protocol         = lookup(egress.value, "protocol", null)
      security_groups  = lookup(egress.value, "security_groups", null)
      self             = lookup(egress.value, "self", null)
      to_port          = lookup(egress.value, "to_port", null)
    }
  }

  tags = {
    Name = "proxy-sg-${var.env}"
  }
}

resource "aws_security_group" "alb-sg" {
  name   = "alb-sg-${var.env}"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port        = "80"
    to_port          = "80"
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  ingress {
    protocol         = "tcp"
    to_port          = "443"
    from_port        = "443"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [aws_vpc.main.cidr_block]
  }

  dynamic "egress" {
    for_each = local.default_egress
    content {
      # TF-UPGRADE-TODO: The automatic upgrade tool can't predict
      # which keys might be set in maps assigned here, so it has
      # produced a comprehensive set here. Consider simplifying
      # this after confirming which keys can be set in practice.

      cidr_blocks      = lookup(egress.value, "cidr_blocks", null)
      description      = lookup(egress.value, "description", null)
      from_port        = lookup(egress.value, "from_port", null)
      ipv6_cidr_blocks = lookup(egress.value, "ipv6_cidr_blocks", null)
      prefix_list_ids  = lookup(egress.value, "prefix_list_ids", null)
      protocol         = lookup(egress.value, "protocol", null)
      security_groups  = lookup(egress.value, "security_groups", null)
      self             = lookup(egress.value, "self", null)
      to_port          = lookup(egress.value, "to_port", null)
    }
  }

  tags = {
    Name = "alb-sg-${var.env}"
  }
}

resource "aws_security_group" "ssh" {
  name   = "ssh-sg-${var.env}"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.main.cidr_block]
  }

  tags = {
    Name = "ssh-sg-${var.env}"
  }
}

resource "aws_security_group" "app-private" {
  name   = "app-private-sg-${var.env}"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [aws_vpc.main.cidr_block]
  }

  ingress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    self      = true
  }

  dynamic "egress" {
    for_each = local.default_egress
    content {
      # TF-UPGRADE-TODO: The automatic upgrade tool can't predict
      # which keys might be set in maps assigned here, so it has
      # produced a comprehensive set here. Consider simplifying
      # this after confirming which keys can be set in practice.

      cidr_blocks      = lookup(egress.value, "cidr_blocks", null)
      description      = lookup(egress.value, "description", null)
      from_port        = lookup(egress.value, "from_port", null)
      ipv6_cidr_blocks = lookup(egress.value, "ipv6_cidr_blocks", null)
      prefix_list_ids  = lookup(egress.value, "prefix_list_ids", null)
      protocol         = lookup(egress.value, "protocol", null)
      security_groups  = lookup(egress.value, "security_groups", null)
      self             = lookup(egress.value, "self", null)
      to_port          = lookup(egress.value, "to_port", null)
    }
  }

  lifecycle {
    ignore_changes = [
      name,
      description,
    ]
  }

  tags = {
    Name = "app-private-sg-${var.env}"
  }
}

resource "aws_security_group" "db-private" {
  /* Allow traffic on all ports coming from the app-private subnets
  (i.e. the non-db ec2 instances) */

  name   = "db-private-sg-${var.env}"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = aws_subnet.subnet-app-private.*.cidr_block
  }

  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = aws_subnet.subnet-public.*.cidr_block
  }

  ingress {
    from_port   = 6432
    to_port     = 6432
    protocol    = "tcp"
    cidr_blocks = aws_subnet.subnet-public.*.cidr_block
  }

  ingress {
    from_port   = 6432
    to_port     = 6432
    protocol    = "tcp"
    cidr_blocks = aws_subnet.subnet-db-private.*.cidr_block
  }

  ingress {
    from_port   = 2049
    to_port     = 2049
    protocol    = "tcp"
    cidr_blocks = aws_subnet.subnet-public.*.cidr_block
  }

  ingress {
    from_port   = 2049
    to_port     = 2049
    protocol    = "udp"
    cidr_blocks = aws_subnet.subnet-public.*.cidr_block
  }

  ingress {
    from_port   = 111
    to_port     = 111
    protocol    = "tcp"
    cidr_blocks = aws_subnet.subnet-public.*.cidr_block
  }

  ingress {
    from_port   = 111
    to_port     = 111
    protocol    = "udp"
    cidr_blocks = aws_subnet.subnet-public.*.cidr_block
  }

  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = aws_subnet.subnet-public.*.cidr_block
  }

  ingress {
    from_port = 9200
    to_port   = 9200
    protocol  = "tcp"
    cidr_blocks = [
      "${var.openvpn_ip}/32",
    ]
  }

  ingress {
    from_port = 25984
    to_port   = 25984
    protocol  = "tcp"
    cidr_blocks = [
      "${var.openvpn_ip}/32",
    ]
  }

  ingress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    self      = true
  }

  dynamic "egress" {
    for_each = local.default_egress
    content {
      # TF-UPGRADE-TODO: The automatic upgrade tool can't predict
      # which keys might be set in maps assigned here, so it has
      # produced a comprehensive set here. Consider simplifying
      # this after confirming which keys can be set in practice.
      cidr_blocks      = lookup(egress.value, "cidr_blocks", null)
      description      = lookup(egress.value, "description", null)
      from_port        = lookup(egress.value, "from_port", null)
      ipv6_cidr_blocks = lookup(egress.value, "ipv6_cidr_blocks", null)
      prefix_list_ids  = lookup(egress.value, "prefix_list_ids", null)
      protocol         = lookup(egress.value, "protocol", null)
      security_groups  = lookup(egress.value, "security_groups", null)
      self             = lookup(egress.value, "self", null)
      to_port          = lookup(egress.value, "to_port", null)
    }
  }

  tags = {
    Name = "db-private-sg-${var.env}"
  }
}

resource "aws_security_group" "rds" {
  name   = "rds-${var.env}"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port        = "5432"
    to_port          = "5432"
    protocol         = "tcp"
    cidr_blocks      = flatten([aws_subnet.subnet-app-private.*.cidr_block, aws_subnet.subnet-db-private.*.cidr_block])
    ipv6_cidr_blocks = ["::/0"]
  }

  dynamic "egress" {
    for_each = local.default_egress
    content {
      # TF-UPGRADE-TODO: The automatic upgrade tool can't predict
      # which keys might be set in maps assigned here, so it has
      # produced a comprehensive set here. Consider simplifying
      # this after confirming which keys can be set in practice.

      cidr_blocks      = lookup(egress.value, "cidr_blocks", null)
      description      = lookup(egress.value, "description", null)
      from_port        = lookup(egress.value, "from_port", null)
      ipv6_cidr_blocks = lookup(egress.value, "ipv6_cidr_blocks", null)
      prefix_list_ids  = lookup(egress.value, "prefix_list_ids", null)
      protocol         = lookup(egress.value, "protocol", null)
      security_groups  = lookup(egress.value, "security_groups", null)
      self             = lookup(egress.value, "self", null)
      to_port          = lookup(egress.value, "to_port", null)
    }
  }

  lifecycle {
    ignore_changes = [
      name,
      description,
    ]
  }
  tags = {
    Name = "rds-${var.env}"
  }
}

resource "aws_security_group" "elasticache" {
  name   = "elasticache-${var.env}"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port        = "6379"
    to_port          = "6379"
    protocol         = "tcp"
    cidr_blocks      = flatten([aws_subnet.subnet-app-private.*.cidr_block, aws_subnet.subnet-public.*.cidr_block])
    ipv6_cidr_blocks = ["::/0"]
  }

  dynamic "egress" {
    for_each = local.default_egress
    content {
      # TF-UPGRADE-TODO: The automatic upgrade tool can't predict
      # which keys might be set in maps assigned here, so it has
      # produced a comprehensive set here. Consider simplifying
      # this after confirming which keys can be set in practice.

      cidr_blocks      = lookup(egress.value, "cidr_blocks", null)
      description      = lookup(egress.value, "description", null)
      from_port        = lookup(egress.value, "from_port", null)
      ipv6_cidr_blocks = lookup(egress.value, "ipv6_cidr_blocks", null)
      prefix_list_ids  = lookup(egress.value, "prefix_list_ids", null)
      protocol         = lookup(egress.value, "protocol", null)
      security_groups  = lookup(egress.value, "security_groups", null)
      self             = lookup(egress.value, "self", null)
      to_port          = lookup(egress.value, "to_port", null)
    }
  }

  tags = {
    Name = "elasticache-${var.env}"
  }
}
