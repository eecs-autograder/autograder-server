for script in ag_celery_submissions.service ag_celery_deferred.service
do
    echo $script
    sudo systemctl stop $script
done
