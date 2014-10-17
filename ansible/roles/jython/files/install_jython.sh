set -e
wget -O /tmp/jython-installer-2.5.3.jar http://search.maven.org/remotecontent?filepath=org/python/jython-installer/2.5.3/jython-installer-2.5.3.jar
sudo java -jar /tmp/jython-installer-2.5.3.jar --silent -d /usr/local/lib/jython
sudo ln -s /usr/local/lib/jython/bin/jython /usr/local/bin/
wget -O /tmp/ez_setup.py http://peak.telecommunity.com/dist/ez_setup.py
sudo jython /tmp/ez_setup.py
rm /tmp/ez_setup.py
rm /tmp/jython-installer-2.5.3.jar
