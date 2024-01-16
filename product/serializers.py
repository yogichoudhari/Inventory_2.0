from product.models import Product
from rest_framework import serializers


class ProductSerializer(serializers.ModelSerializer):
    in_stock = serializers.SerializerMethodField(read_only=True)
    class Meta:
        model = Product
        exclude = ['account','created_by']

    def update(self, instance, validated_data):
        validated_data['quantity']+=instance.quantity
        return super().update(instance, validated_data)
    def create(self,validated_data):
        user_instance = self.context.get('user_instance')
        acccount_instance = user_instance.account
        validated_data["account"] = acccount_instance
        validated_data["created_by"] = user_instance
        return super().create(validated_data)
    def get_in_stock(self,obj):
        return obj.in_stock
    

class SearchedProductListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"