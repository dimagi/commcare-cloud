data "aws_route53_zone" "existing-zone-name" {
  name         = "${var.domain_name}"
  private_zone = "${var.private_zone}"
}

resource "aws_route53_record" "zone-record-create" {
  count   = "${var.create_record == "true" ? 1 : 0}"
  zone_id = "${data.aws_route53_zone.existing-zone-name.zone_id}"
  name    = "${var.route_names}"
  type    = "${var.record_type}"
  ttl     = "${var.ttl}"
  records = ["${var.records}"]
}
