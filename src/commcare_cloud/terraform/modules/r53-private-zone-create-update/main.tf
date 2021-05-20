resource "aws_route53_zone" "create-private-r53-zone" {
  count  = var.create == true ? 1 : 0
  name   = var.domain_name

  vpc {
    vpc_id = var.zone_vpc_id
  }
}

resource "aws_route53_record" "create-record-r53-pri-zone" {
  count   = var.create_record == true ? 1 : 0
  zone_id = aws_route53_zone.create-private-r53-zone[count.index].zone_id
  name    = var.route_names
  type    = var.type
  ttl     = var.ttl
  records = var.records
}
