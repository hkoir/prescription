from django.apps import AppConfig


class PaymentGatewayConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'payment_gateway'


    def ready(self):
        import payment_gateway.signals
