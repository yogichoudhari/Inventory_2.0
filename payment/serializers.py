from rest_framework import serializers
from .models import PaymentLog


class PaymentLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentLog
        fields = ['id', "amount", "customer_stripe_id", "status"]