echo "First: make sure you that you aren't logged in in a way that has ssh-agent forwarding. Second: Did you remember to add this machine's ssh key to class7's authorized_keys file? If not, kill this script and go do that"
read -n 1

mkdir ~/media_root
sudo apt install -y sshfs autossh
ssh jameslp@class7.eecs.umich.edu echo "Connected to class7 via ssh!"

