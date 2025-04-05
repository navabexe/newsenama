# # File: src/celery_config.py
# from celery import Celery
#
# celery_app = Celery(
#     "senama",
#     broker="amqp://guest:guest@172.30.233.230:5672//",  # Use WSL IP
#     include=["domain.notification.notification_services.notification_service"]
# )
#
# if __name__ == "__main__":
#     celery_app.worker_main(["worker", "--loglevel=info"])