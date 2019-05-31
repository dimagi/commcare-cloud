python_version=$(python3.6 --version)
if [ "$python_version" != "Python 3.6.8" ]; then
    sudo wget https://www.python.org/ftp/python/3.6.8/Python-3.6.8.tgz
    sudo tar xzf Python-3.6.8.tgz
    cd Python-3.6.8
    sudo ./configure --enable-optimizations
    make
    sudo make altinstall
    cd ..
    rm Python-3.6.8.tgz
    rm -r Python-3.6.8
fi
