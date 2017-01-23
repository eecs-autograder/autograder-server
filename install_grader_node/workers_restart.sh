for script in ag_celery_submissions.service ag_celery_deferred.service
do
    echo $script
    sudo cp systemd_scripts/$script /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl stop $script
    sudo systemctl start $script
done

