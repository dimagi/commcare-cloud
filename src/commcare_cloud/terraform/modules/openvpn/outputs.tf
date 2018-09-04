output "openvpn-access-sg" {
  value = "${aws_security_group.openvpn-access-sg.id}"
}
