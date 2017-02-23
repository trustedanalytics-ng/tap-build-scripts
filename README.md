# TAP Build Script (TBS)
TBS is a tool for building all base infrastructure components and apps. It prepares TAP deployment package.

## Prerequisites
In order to run TBS, Centos developer machine with some software dependencies is needed.

* Prepare developer machine which meet following requirements:
 * operating system: CentOS 7.2 (linux);
 * 100 GB disk free space;
 * at least 4 GB RAM;
 * access to the Internet network.
* Log into prepared developer machine.
* Install neccessary dependencies:
 * epel-release: `yum install -y epel-release`,
 * ansible dependencies: `yum install -y python-pip python-devel pycrypto gcc gcc-c++ libffi libffi-devel openssl-devel wget unzip`
 * ansible in version 2.2.0.0: `pip install ansible==2.2.0.0`,
 * git client: `yum install -y git`.

## Warning
During build SELinux will be disabled. Enable it after TBS build if you find it necessary.

## Running TBS
In order to run TBS follow the commands:
* Log into developer machine.
* Clone this repository.
* Fetch repository submodules: `git submodule init && git submodule update`.
* Modify group vars, and inventory if it is neccessary. Default values can be used.
* Run TBS script: `./RUN.sh`.

Warning: Running TBS script you agree with Oracle Java license.

## TAP deployment package
Deployment package will be available at `/root/TAP-0.8.0.99999.tar.gz` after running above script.

## Deploying TAP
Once you built TAP deployment package you can untar it and run deployment scripts. For instructions please follow below link:
https://github.com/trustedanalytics-ng/platform-wiki/blob/master/Platform-Deployment/platform_deployment_manual.md

## Handling proxy
In order to run grand-platform-factory behind proxy, execute following command:
```
./RUN.sh --extra-vars='{proxy_env: {http_proxy: "<HTTP_PROXY>", https_proxy: "<HTTPS_PROXY>", no_proxy: "<NO_PROXY>"}}'
```
## Testing with Vagrant container

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
vagrant provision
```

