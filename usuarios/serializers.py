from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer para lectura de usuarios"""
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'role_display', 'is_active', 'is_staff', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer para creación de usuarios"""
    password = serializers.CharField(write_only=True, required=True, min_length=8)
    password2 = serializers.CharField(write_only=True, required=True, min_length=8)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password2', 
            'first_name', 'last_name', 'role'
        ]
    
    def validate(self, data):
        """Validar que las contraseñas coincidan"""
        if data['password'] != data['password2']:
            raise serializers.ValidationError({
                'password2': 'Las contraseñas no coinciden'
            })
        
        # Validar que el username no exista
        if User.objects.filter(username=data['username']).exists():
            raise serializers.ValidationError({
                'username': 'Este usuario ya existe'
            })
        
        return data
    
    def create(self, validated_data):
        """Crear nuevo usuario"""
        validated_data.pop('password2')
        password = validated_data.pop('password')
        
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer para actualizar usuarios"""
    
    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name', 'role', 'is_active'
        ]


class UserDetailSerializer(serializers.ModelSerializer):
    """Serializer detallado con información adicional del usuario"""
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    last_login_display = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'role_display', 'is_active', 'is_staff', 'is_superuser',
            'created_at', 'updated_at', 'last_login', 'last_login_display'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_login']
    
    def get_last_login_display(self, obj):
        """Formato legible de último login"""
        if obj.last_login:
            from django.utils.timesince import timesince
            return f"Hace {timesince(obj.last_login)}"
        return "Nunca"


class UserAdminListSerializer(serializers.ModelSerializer):
    """Serializer para listar usuarios en admin panel"""
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    status_display = serializers.SerializerMethodField()
    last_login_display = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'role_display', 'is_active', 'status_display',
            'created_at', 'last_login', 'last_login_display'
        ]
    
    def get_status_display(self, obj):
        """Estado legible del usuario"""
        return 'Activo' if obj.is_active else 'Suspendido'
    
    def get_last_login_display(self, obj):
        """Formato legible de último login"""
        if obj.last_login:
            from django.utils.timesince import timesince
            return f"Hace {timesince(obj.last_login)}"
        return "Nunca"


class UserPasswordChangeSerializer(serializers.Serializer):
    """Serializer para cambio de contraseña"""
    old_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, required=True, min_length=8)
    new_password2 = serializers.CharField(write_only=True, required=True, min_length=8)
    
    def validate(self, data):
        if data['new_password'] != data['new_password2']:
            raise serializers.ValidationError({
                'new_password2': 'Las contraseñas no coinciden'
            })
        return data


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Serializer personalizado para JWT con datos del usuario"""
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Agregar datos al token
        token['username'] = user.username
        token['email'] = user.email
        token['role'] = user.role
        token['full_name'] = user.get_full_name() or user.username
        
        return token
