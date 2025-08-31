# Celery Config
CELERY_BROKER_URL = 'amqp://localhost'  # RabbitMQ broker
CELERY_RESULT_BACKEND = 'rpc://'

# Email Config (example with console backend for dev)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your_email@gmail.com'
EMAIL_HOST_PASSWORD = 'your_password'
DEFAULT_FROM_EMAIL = 'ALX Travel <your_email@gmail.com>'
