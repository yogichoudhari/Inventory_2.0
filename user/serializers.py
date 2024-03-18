from rest_framework import serializers
from .models import User, Account, Role, Permission
from payment.models import Subscription
from indian_cities.dj_city import cities
from user.models import state_choices
import logging
from datetime import datetime


logger = logging.getLogger('file_logger')

class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ['name','token_expires_in_seconds']

    def create(self,validated_data):
        admin = self.context.get('user_obj')
        account_instance =  Account.objects.create(admin=admin,**validated_data)
        account_instance.save()
        return account_instance
    
class UserSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True)
    account = AccountSerializer()
    class Meta:
        model = User
        fields = ["username", "password", "password2", 
                  "first_name", "last_name", "email",
                  "phone", 'address', "role", "account"]

    def validate(self,attrs):
        # username = attrs.get('username')
        # regex = "^[A-Za-z]{2,}[0-9^_!@$%^&*()_+{}:\"><?}|][0-9]*"
        # username_pattern = re.compile(regex)
        # if not re.match(username_pattern,username):
        #     raise serializers.ValidationError("Invalid username")
        password = attrs.get('password')
        password2 = attrs.get('password2')
        if password!=password2:
            raise serializers.ValidationError('password does not match')
        email = attrs.get("email")
        print(email)
        user = User.objects.filter(email=email).first()
        if user is not None:
            raise serializers.ValidationError("email already registered")
        # regex = "^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!#%*?&]{6,20}$"
        # password_pattern = re.compile(regex)
        # if not re.match(password_pattern,password):
        #     raise serializers.ValidationError("password should be 6-20 charachters alphanumerical")
        return attrs
    def create(self,validated_data):
            validated_data.pop("password2",None)
            account_instance = self.context.get("account",None)
            role_id = validated_data.pop("role",None)
            permission_set_ids = validated_data.pop("permission_set_ids",None)
            subscription_id = validated_data.pop("subscription",None)
            permission_instances = Permission.objects.filter(id__in=[permission_set_ids])
            subscription_instance = Subscription.objects.filter(id=subscription_id).first() 
            role_instance = Role.objects.filter(id=role_id).first()
            account_data = validated_data.pop('account', None)
            if self.context.get('is_admin'):
                if account_data:
                    user_instance = User.objects.create_superuser(account=account_instance,
                                                                         role=role_instance,
                                                                         **validated_data)
                    account_serialize = AccountSerializer(data=account_data,context={'user_obj':user_instance})
                    if account_serialize.is_valid():
                        account_instance = account_serialize.save()
                        user_instance.account = account_instance
                        user_instance.save()
                else:
                    raise serializers.ValidationError("account details details not provided")
            else:
                user_instance = User.objects.create_user(account=account_instance,
                                                          subscription=subscription_instance,
                                                                     role=role_instance,
                                                                    **validated_data)
                for permission_set in permission_instances:
                    user_instance.permissions.add(permission_set)
                user_instance.save(update_fields=['permissions'])
            return user_instance

class RoleSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='pk')
    class Meta:
        model = Role
        fields = ["id","name"]



class UpdateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email"]

    def update(self,instance,validated_data):
        instance.username = validated_data.get('username',instance.username)
        instance.first_name = validated_data.get('first_name',instance.first_name)
        instance.last_name = validated_data.get('last_name',instance.last_name)
        instance.email = validated_data.get('email',instance.email)
        instance.save()
        return instance


    

class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = "__all__" 
    
    def create(self,validated_data):
        permission_dict_keys = ['can_create','can_update','can_delete'] 
        for k in validated_data['permission_set'].keys():
            if k not in permission_dict_keys:
                raise serializers.ValidationError("invalid permission set")
        def permission_dict_format():
            return  {
            'can_create':False,
            'can_update':False,
            'can_delete':False
        }
        permission_dict = permission_dict_format()
        permission_dict.update(validated_data['permission_set'])
        validated_data['permission_set'] = permission_dict
        return super().create(validated_data)
    
class UpdateUserSerializer(serializers.ModelSerializer):
    user = UpdateUserSerializer()
    account = AccountSerializer(read_only=True)
    class Meta:
        model = User
        fields = ["id", "user", "phone", "state", "city", 'account']

    def update(self,instance,validated_data):
        user_data = validated_data.pop("user")
        user_id = self.context.get("user_id")
        user_instance = User.objects.get(pk=user_id)
        user_serializer = UpdateUserSerializer(user_instance,data=user_data,partial=True)
        if user_serializer.is_valid():
            user_serializer.save()
        instance.phone = validated_data.get("phone",instance.phone)
        instance.city = validated_data.get("city",instance.city)
        instance.state = validated_data.get("state",instance.state)
        instance.save()
        return instance
    

class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField()
    new_password = serializers.CharField(max_length=128)
    confirm_new_password = serializers.CharField(max_length=128)
    
    def validate(self, attrs):
        current_password = attrs.get('current_password', None)
        new_password = attrs.get('new_password', None)
        confirm_new_password = attrs.get('confirm_new_password', None)
        user = self.instance
        if not user.check_password(current_password):
            raise serializers.ValidationError("incorrect password entered")
        elif new_password!=confirm_new_password:
            raise serializers.ValidationError("password does not match confirm password")
        return attrs
    
    def update(self, instance, validated_data):
        instance.set_password(validated_data['new_password'])
        instance.last_password_change = datetime.now()
        instance.save()
        return instance
        
    
class ResetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(max_length=128)
    confirm_new_password = serializers.CharField(max_length=128)    

    def validate(self, attrs):
        new_password = attrs.get('new_password', None)
        confirm_new_password = attrs.get('confirm_new_password', None)
        user = self.instance
        if new_password!=confirm_new_password:
            raise serializers.ValidationError("password does not match confirm password")
        return attrs
    def update(self, instance, validated_data):
        instance.set_password(validated_data['new_password'])
        instance.last_password_change = datetime.now()
        instance.save()
        return instance
        
        
        