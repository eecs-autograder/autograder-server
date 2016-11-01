for script in $(ls systemd_scripts)
do
    echo $script
    sudo cp systemd_scripts/$script /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable $script
    sudo systemctl start $script
done

echo "Remember to increase the nofile limit in /etc/security/limits.conf!!!!!!"