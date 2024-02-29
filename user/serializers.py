from rest_framework import serializers
from .models import User as CustomUser, Account, Role, Permission
from django.contrib.auth.models import User
from indian_cities.dj_city import cities
from user.models import state_choices
from datetime import time
class UserSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True)
    class Meta:
        model = User
        fields = ["username", "password", "password2", 
                  "first_name", "last_name", "email"]

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
        user = User.objects.filter(email=email).first()
        if user is not None:
            raise serializers.ValidationError("email already registered")
        # regex = "^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!#%*?&]{6,20}$"
        # password_pattern = re.compile(regex)
        # if not re.match(password_pattern,password):
        #     raise serializers.ValidationError("password should be 6-20 charachters alphanumerical")

        return attrs
    
    def create(self,validated_data):
        password = validated_data.get('password')
        validated_data.pop("password2",None)
        if self.context.get('is_admin'):
            user = User.objects.create_superuser(**validated_data)
        else:
            user = super().create(validated_data)
        user.set_password(password)
        user.save()
        return user

class RoleSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='pk')
    class Meta:
        model = Role
        fields = ["id","name"]

class CustomUserSerializer(serializers.ModelSerializer):
    role = serializers.IntegerField()
    user = UserSerializer()
    class Meta:
        model = CustomUser
        fields = ["user", "phone", "role", "state", 
                  "city", "account","is_verified"]

    def validate(self,data):
        state_value = data.get('state')
        city_value = data.get('city')
        for state,city_list in cities:
            if state == state_value:
                for city,_ in city_list:
                    if city==city_value:
                        break
                else:
                    raise serializers.ValidationError("please enter correct city")
        return data

    def create(self,validated_data):
        user_data = validated_data.pop("user")
        role_id = validated_data.pop("role")
        account_instance = self.context.get("account")
        role_obj = Role.objects.get(id=role_id)
        if not role_obj:
            raise serializers.ValidationError("incorrect role id provided")
        user_serialize = UserSerializer(data=user_data,context={"is_admin":False})
        if user_serialize.is_valid():
            user_instance = user_serialize.save()
        custom_user , created = CustomUser.objects.get_or_create(user=user_instance,
                                                                account=account_instance,
                                                                 role=role_obj,
                                                                **validated_data)
        return custom_user

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

class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ['name','token_expires_in_seconds']

    def create(self,validated_data):
        admin = self.context.get('user_obj')
        return Account.objects.create(admin=admin,**validated_data)
    

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
    
class UpdateCustomUserSerializer(serializers.ModelSerializer):
    user = UpdateUserSerializer()
    account = AccountSerializer(read_only=True)
    class Meta:
        model = CustomUser
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
    
class AdminUserSerializer(serializers.ModelSerializer):
    account = AccountSerializer()
    user = UserSerializer()
    class Meta:
        model = CustomUser
        fields = ['user', 'phone', 'state', 'city', "account"]
    def validate(self,data):
        state_value = data.get('state')
        city_value = data.get('city')
        for state,city_list in cities:
            if state == state_value:
                for city,_ in city_list:
                    if city==city_value:
                        break
                else:
                    raise serializers.ValidationError("please enter correct city")
        return data
    
    def create(self,validated_data):
        user_data = validated_data.pop('user')
        account_data = validated_data.pop('account')
        user_serialize = UserSerializer(data=user_data,context={'is_admin':True})
        role_obj = Role.objects.get(name="Admin")
        if user_serialize.is_valid():
            user_instance = user_serialize.save()
        admin_user , created = CustomUser.objects.get_or_create(user=user_instance,role=role_obj,**validated_data)
        account_serialize = AccountSerializer(data=account_data,context={'user_obj':admin_user})
        if account_serialize.is_valid():
            account_instance = account_serialize.save()
            admin_user.account = account_instance
            admin_user.save()
        return admin_user
    
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        # try:
        #     user = User.objects.get(username=username)
        # except User.DoesNotExist:
        #     raise serializers.ValidationError("incorrect username")
        # if not user.check_password(password):
        #     raise serializers.ValidationError("incorrect password entered")
        # return attr