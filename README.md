# GameCredits Block Explorer

How to run the development environment:

1. `cd env && vagrant up` - Start the Vagrant virtual machine
2. `vagrant ssh` - log in to the virtual machine
3. `sudo pip install ansible` - Install Ansible
4. `ansible-playbook /code/env/configure-vagrant.yml` - run the configuration

The Swagger UI should be available on [http://localhost:8080/api/ui/](http://127.0.0.1:8080/api/ui/)