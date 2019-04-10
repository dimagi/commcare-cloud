output "openvpn-access-sg" {
  value = "${aws_security_group.openvpn-access-sg.id}"
}

output "openvpn-server-ip" {
  value = "${aws_instance.vpn_host.private_ip}"
}
