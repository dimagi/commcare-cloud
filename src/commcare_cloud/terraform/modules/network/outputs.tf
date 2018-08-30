output "subnet-a-app-private" {
  value = "${aws_subnet.subnet-a-app-private.id}"
}

output "subnet-b-app-private" {
  value = "${aws_subnet.subnet-b-app-private.id}"
}

output "subnet-c-app-private" {
  value = "${aws_subnet.subnet-c-app-private.id}"
}

output "subnet-a-public" {
  value = "${aws_subnet.subnet-a-public.id}"
}

output "subnet-b-public" {
  value = "${aws_subnet.subnet-b-public.id}"
}

output "subnet-c-public" {
  value = "${aws_subnet.subnet-c-public.id}"
}

output "subnet-a-util-private" {
  value = "${aws_subnet.subnet-a-util-private.id}"
}

output "subnet-b-util-private" {
  value = "${aws_subnet.subnet-b-util-private.id}"
}

output "subnet-c-util-private" {
  value = "${aws_subnet.subnet-c-util-private.id}"
}

output "subnet-a-db-private" {
  value = "${aws_subnet.subnet-a-db-private.id}"
}

output "subnet-b-db-private" {
  value = "${aws_subnet.subnet-b-db-private.id}"
}

output "subnet-c-db-private" {
  value = "${aws_subnet.subnet-c-db-private.id}"
}

output "vpc-all-hosts-sg" {
  value = "${aws_security_group.vpc-all-hosts-sg.id}"
}

output "g2-access-sg" {
  value = "${aws_security_group.g2-access-sg.id}"
}

output "vpc-id" {
  value = "${aws_vpc.g2-tf-vpc.id}"
}

output "vpc-cidr" {
  value = "${aws_vpc.g2-tf-vpc.cidr_block}"
}

#Sang - New

output "proxy-sg" {
  value = "${aws_security_group.proxy-sg.id}"
}
output "django-sg" {
  value = "${aws_security_group.django-sg.id}"
}
output "celery-sg" {
  value = "${aws_security_group.celery-sg.id}"
}
output "pillowtop-sg" {
  value = "${aws_security_group.pillowtop-sg.id}"
}
output "formplayer-sg" {
  value = "${aws_security_group.formplayer-sg.id}"
}
output "kafka-sg" {
  value = "${aws_security_group.kafka-sg.id}"
}
output "es-sg" {
  value = "${aws_security_group.es-sg.id}"
}
output "airflow-sg" {
  value = "${aws_security_group.airflow-sg.id}"
}
output "touchforms-sg" {
  value = "${aws_security_group.touchforms-sg.id}"
}
output "rabbitmq-sg" {
  value = "${aws_security_group.rabbitmq-sg.id}"
}
