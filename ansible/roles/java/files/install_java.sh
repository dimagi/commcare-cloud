set -e
wget -O /tmp/jdk.tar.gz --no-check-certificate --no-cookies --header "Cookie: oraclelicense=accept-securebackup-cookie" http://download.oracle.com/otn-pub/java/jdk/7u67-b01/jdk-7u67-linux-x64.tar.gz
tar -xvf /tmp/jdk.tar.gz -C /tmp/
mkdir -p /usr/lib/jvm
cd /tmp
rm -rf /usr/lib/jvm/jdk1.7.0 || true
rm -rf /usr/lib/jvm/jdk1.7.0_67 || true
mv jdk1.7.0_67/ /usr/lib/jvm/
ln -s /usr/lib/jvm/jdk1.7.0_67/ /usr/lib/jvm/jdk1.7.0
update-alternatives --install "/usr/bin/java" "java" "/usr/lib/jvm/jdk1.7.0/bin/java" 1
update-alternatives --install "/usr/bin/javac" "javac" "/usr/lib/jvm/jdk1.7.0/bin/javac" 1
update-alternatives --install "/usr/bin/javaws" "javaws" "/usr/lib/jvm/jdk1.7.0/bin/javaws" 1
update-alternatives --config java
java -version
echo 'java=installed' > /usr/lib/jvm/success.txt
