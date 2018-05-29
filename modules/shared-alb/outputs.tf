output "alb-id" {
  value = "${aws_lb.shared-alb.id}"
}

output "alb-zone-id" {
  value = "${aws_lb.shared-alb.zone_id}"
}

output "alb-dns-name" {
  value = "${aws_lb.shared-alb.dns_name}"
}

#output "alb-listener" {
#  value = "${aws_lb_listener.shared-ssl.arn}"
#}
