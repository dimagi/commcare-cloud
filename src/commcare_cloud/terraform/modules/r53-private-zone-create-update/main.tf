resource "aws_route53_zone" "create-private-r53-zone" {
  name = "${var.domain_name}"

  vpc {
    vpc_id = "${var.zone_vpc_id}"
  }
}

resource "aws_route53_record" "create-record-r53-pri-zone" {
  zone_id = "${aws_route53_zone.create-private-r53-zone.zone_id}"
  name    = "${var.route_names}"
  type    = "${var.type}"
  ttl     = "${var.ttl}"
  records = ["${var.records}"]
}
