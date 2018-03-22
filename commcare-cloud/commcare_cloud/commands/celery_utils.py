from collections import defaultdict
from memoized import memoized


@memoized
def get_celery_processes(environment_name):
    from commcare_cloud.environment.main import get_environment
    environment = get_environment(environment_name)
    app_processes_config = environment.translated_app_processes_config
    return app_processes_config.celery_processes


def get_celery_worker_name(environment_name, comma_separated_queue_name, worker_num):
    from commcare_cloud.environment.main import get_environment
    environment = get_environment(environment_name)
    environment_environment = environment.meta_config.deploy_env
    project = environment.fab_settings_config.project
    return "{project}-{environment}-celery_{comma_separated_queue_name}_{worker_num}".format(
        project=project,
        environment=environment_environment,
        comma_separated_queue_name=comma_separated_queue_name,
        worker_num=worker_num
    )


def get_celery_workers_config(environment_name):
    """
    :return: convert the celery_processes in app-processes to map them to
    {
      queue_name : {
            host: worker_name
        }
    }
    For ex:
    'kafka0':
        email_queue: worker_name
    to
    {
        email_queue: {
            kafka0: [commcare-hq-staging-celery_email_queue_0]
        }
    }
    """
    celery_worker_config = {}
    celery_processes = get_celery_processes(environment_name)
    for host, celery_processes_list in celery_processes.items():
        if host != 'None':
            for comma_separated_queue_names, details in celery_processes_list.items():
                # split comma separated names to individual workers
                for queue_name in comma_separated_queue_names.split(','):
                    # ignore flower and celery periodic as celery workers
                    if queue_name not in ['flower', 'celery_periodic']:
                        if not celery_worker_config.get(queue_name):
                            celery_worker_config[queue_name] = defaultdict(list)

                        if details.get('num_workers', 1) > 1:
                            for num in range(details.get('num_workers')):
                                celery_worker_name = get_celery_worker_name(
                                    environment_name, comma_separated_queue_names, num)
                                celery_worker_config[queue_name][host].append(celery_worker_name)
                        else:
                            celery_worker_name = get_celery_worker_name(environment_name,
                                                                        comma_separated_queue_names, 0)
                            celery_worker_config[queue_name][host].append(celery_worker_name)
    return celery_worker_config


def find_celery_worker_name(environment_name, queue_name, host, worker_num=None):
    celery_workers_config = get_celery_workers_config(environment_name)
    queue_workers_for_host = celery_workers_config.get(queue_name, {}).get(host)
    if queue_workers_for_host:
        for worker in queue_workers_for_host:
            if worker.endswith(worker_num):
                return worker
