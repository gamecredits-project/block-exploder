# GameCredits Block Explorer

How to run the development environment:

1. `cd env && vagrant up` - Start the Vagrant virtual machine
2. `vagrant ssh` - Log in to the virtual machine
3. Disable transparent hugepages so Mongo works properly https://docs.mongodb.com/manual/tutorial/transparent-huge-pages/. Reload vagrant after this step.
4. `sudo apt update && sudo apt upgrade -y` - Update the server
5. `sudo apt install python-pip -y` - Install pip
6. `sudo pip install -I ansible==2.3.0` - Install Ansible
7. `ansible-playbook /exploder/env/configure-vagrant.yml` - Run the configuration
8. Manually add MongoDB user - https://docs.mongodb.com/manual/tutorial/create-users/

The Swagger UI should be available on [http://localhost:8080/api/ui/](http://127.0.0.1:8080/api/ui/)
The WebSocket UI should be available on [http://localhost:8080/socket.io] 

## FAQ

To run test coverage: `test-coverage`

#### Unsupported locale setting:

1. `export LC_ALL="en_US.UTF-8"`
2. `export LC_CTYPE="en_US.UTF-8"`
3. `sudo dpkg-reconfigure locales` - Than press Enter twice

#### Example of adding a MongoDB user:

1. `mongo` - Enter the MongoDB cli
1. `use exploder` - Select the database
1. `db.createUser({ user: "mongouser", pwd: "mongopass", roles: [{ role: "readWrite", db: "exploder" }] })` - Adds the user