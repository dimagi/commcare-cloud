def authorize_key(config, key_path)
    if key_path.nil?
      fail "Public key not found at following paths: #{key_paths.join(', ')}"
    end

    full_key_path = File.expand_path(key_path)

    if File.exists?(full_key_path)
      config.vm.provision 'file',
        run: 'once',
        source: full_key_path,
        destination: '/home/vagrant/.ssh/id_rsa'

      config.vm.provision 'shell',
        privileged: true,
        run: 'once',
        inline:
          'chown vagrant:vagrant /home/vagrant/.ssh/id_rsa && ' +
          'chmod 600 /home/vagrant/.ssh/id_rsa && ' +
          'echo "Done!"'
    end
end
