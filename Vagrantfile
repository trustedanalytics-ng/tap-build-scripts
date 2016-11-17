# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure(2) do |config|
  config.vm.define "gpf" do |config|

    config.ssh.insert_key = false

    config.vm.box = "frensjan/centos-7-64-lxc"
    config.vm.box_check_update = false
    config.vm.hostname = "gpf"

    if Vagrant.has_plugin?("vagrant-proxyconf")
      if ENV["http_proxy"]
        config.proxy.http = ENV["http_proxy"]
      end
      if ENV["HTTP_PROXY"]
        config.proxy.http = ENV["HTTP_PROXY"]
      end
      if ENV["https_proxy"]
        config.proxy.https = ENV["https_proxy"]
      end
      if ENV["HTTPS_PROXY"]
        config.proxy.https = ENV["HTTP_PROXY"]
      end
      if ENV["no_proxy"]
        config.proxy.no_proxy = ENV["no_proxy"]
      end
      if ENV["NO_PROXY"]
        config.proxy.no_proxy = ENV["NO_PROXY"]
      end
    end

    config.vm.provision "ansible", run: "always" do |ansible|
      ansible.playbook = "tap-packager.yml"
      ansible.skip_tags = "skip_on_vagrant"
      ansible.extra_vars = {
        TARGET_REGULAR_USER: "vagrant",
        REGULAR_USER_HOME: "/home/vagrant"
      }

      if config.proxy.http and config.proxy.https
        ansible.extra_vars['proxy_env'] = {
           http_proxy: config.proxy.http,
           https_proxy: config.proxy.https,
           no_proxy: config.proxy.no_proxy
         } 
      end
    end
  end
end
