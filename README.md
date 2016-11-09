# grand-platform-factory
Tool for preparing TAP deploy package.
Required Ansible version: `2.2`

## Handling proxy
In order to run grand-platform-factory behind proxy, execute following command:
```
./RUN.sh --extra-vars='{"proxy_env": {"http_proxy":"<HTTP_PROXY>", "https_proxy":"<HTTPS_PROXY>"}}'
```
## Using Vagrant container

1. Install Vagrant: https://www.vagrantup.com/docs/installation/
2. Install lxc: `sudo apt install lxc`
3. Install Vagrant lxc plugin: `vagrant plugin install vagrant-lxc`
4. If you are hiding behind proxy, install vagrant-proxyconf plugin: `vagrant plugin install vagrant-proxyconf`

Now container can be started by running `vagrant up` command. Use `vagrant ssh` in order to access the container.

Recreating container:
```
vagrant destroy && vagrant up
```
Rerunning tap-packager.yml playbook on container: 
```
ansible-playbook --skip-tags=skip_on_vagrant --private-key=.vagrant/machines/tcagent/lxc/private_key -u vagrant -i .vagrant/provisioners/ansible/inventory/vagrant_ansible_inventory tap-packager.yml -v
```

