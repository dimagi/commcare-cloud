data "aws_route53_zone" "existing-zone-name" {
  name         = "${var.domain_name}"
  private_zone = "${var.private_zone}"
}

resource "aws_route53_record" "zone-record-create" {
  zone_id = "${data.aws_route53_zone.existing-zone-name.zone_id}"
  name    = "${var.route_names}"
  type    = "${var.type}"
  ttl     = "${var.ttl}"
  records = ["${var.records}"]
}
