# GameCredits Block Explorer

How to run the development environment:

1. `cd env && vagrant up` - Start the Vagrant virtual machine
2. `vagrant ssh` - Log in to the virtual machine
3. Disable transparent hugepages so Mongo works properly https://docs.mongodb.com/manual/tutorial/transparent-huge-pages/. Reload vagrant after this step.
4. `pip install --upgrade pip` - Upgrade pip
5. `sudo pip install --upgrade setuptools` - Upgrade setuptools to latest version
6. `sudo pip install -I ansible==2.3.0` - Install Ansible
7. `ansible-playbook /exploder/env/configure-vagrant.yml` - Run the configuration

The Swagger UI should be available on [http://localhost:8080/api/ui/](http://127.0.0.1:8080/api/ui/)
