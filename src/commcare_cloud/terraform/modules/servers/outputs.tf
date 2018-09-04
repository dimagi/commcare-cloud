output "count" {
  value = "${aws_instance.server.count}"
}

output "server" {
  value = "${aws_instance.server.*.id}"
}

output "server_private_ip" {
  value = "${aws_instance.server.*.private_ip}"
}
