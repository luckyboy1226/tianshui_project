from rest_framework import serializers
from .models import User, UserPermission, UserSession


MODULE_PERMISSION_CHOICES = {
    'remote_sensing': ['view', 'use', 'manage'],
    'ecological_index': ['view', 'use', 'manage'],
    'overlay_analysis': ['view', 'use', 'manage'],
    'climate_monitoring': ['view', 'use', 'manage'],
    'feedback': ['view', 'manage'],
    'business_layers': ['view', 'manage'],
    'user_management': ['manage'],
}


class UserSerializer(serializers.ModelSerializer):
    """用户序列化器"""
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    permissions = serializers.SerializerMethodField()
    is_admin = serializers.SerializerMethodField()
    
    def get_permissions(self, obj):
        permission_map = {}
        for item in obj.userpermission_set.filter(granted=True).order_by('module', 'permission'):
            permission_map.setdefault(item.module, []).append(item.permission)
        return permission_map

    def get_is_admin(self, obj):
        return bool(obj.is_superuser or obj.role == 'admin')
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'role', 'role_display',
            'phone', 'organization', 'department', 'position', 'avatar',
            'is_active', 'date_joined', 'last_login', 'permissions', 'is_admin'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']


class UserCreateSerializer(serializers.ModelSerializer):
    """用户创建序列化器"""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm', 'first_name', 'last_name',
            'role', 'phone', 'organization', 'department', 'position'
        ]
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("密码确认不匹配")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create(**validated_data)
        user.set_password(password)
        if user.role == 'admin':
            user.is_staff = True
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """用户更新序列化器"""
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'phone', 'organization',
            'department', 'position', 'avatar'
        ]


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    """管理员用户更新序列化器"""
    password = serializers.CharField(write_only=True, required=False, min_length=8)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name', 'role',
            'phone', 'organization', 'department', 'position',
            'is_active', 'password'
        ]

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if instance.role == 'admin':
            instance.is_staff = True
        elif not instance.is_superuser:
            instance.is_staff = False
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class UserPermissionAssignmentSerializer(serializers.Serializer):
    """用户权限分配序列化器"""
    permissions = serializers.DictField(
        child=serializers.ListField(
            child=serializers.CharField(max_length=50),
            allow_empty=True
        )
    )

    def validate_permissions(self, value):
        normalized = {}
        for module, permissions in value.items():
            if module not in MODULE_PERMISSION_CHOICES:
                raise serializers.ValidationError(f'不支持的模块: {module}')
            allowed_permissions = MODULE_PERMISSION_CHOICES[module]
            invalid = [item for item in permissions if item not in allowed_permissions]
            if invalid:
                raise serializers.ValidationError(
                    f'模块 {module} 包含无效权限: {", ".join(invalid)}'
                )
            normalized[module] = sorted(set(permissions))
        return normalized


class UserPermissionSerializer(serializers.ModelSerializer):
    """用户权限序列化器"""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserPermission
        fields = ['id', 'user', 'module', 'permission', 'granted', 'created_at']
        read_only_fields = ['id', 'created_at']


class UserSessionSerializer(serializers.ModelSerializer):
    """用户会话序列化器"""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserSession
        fields = [
            'id', 'user', 'session_key', 'ip_address', 'user_agent',
            'login_time', 'logout_time', 'is_active'
        ]
        read_only_fields = ['id', 'login_time'] 
