from rest_framework import serializers
from .models import PaymentLog, Subscription, SubscriptionPlan
from user.serializers import AccountSerializer

class PaymentLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentLog
        fields = ['id', "amount", "customer_stripe_id", "status"]
        
class SubscriptionSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='pk')
    account = AccountSerializer(write_only=True)
    product_id = serializers.CharField(write_only=True)
    class Meta:
        model = Subscription
        fields = ['id',"account","product_id","name"]
class SubscriptionPlanSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source="pk")
    product = SubscriptionSerializer()
    class Meta:
        model = SubscriptionPlan
        fields = ["id","name","price_id","product"]