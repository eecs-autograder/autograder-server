for script in $(ls systemd_scripts)
do
    echo $script
    sudo cp systemd_scripts/$script /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable $script
    sudo systemctl start $script
done

echo "Remember to increase the nofile limit in /etc/security/limits.conf!!!!!!"
echo "Add the following lines to the bottom of that file:"
echo "*                soft    nofile          1000000"
echo "*                hard    nofile          1000000"

