from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import APIKey, APILog, APIVersion

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model
    """
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class APIKeySerializer(serializers.ModelSerializer):
    """
    Serializer for APIKey model
    """
    user = UserSerializer(read_only=True)
    secret_key = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = APIKey
        fields = [
            'key_id', 'name', 'user', 'description', 'is_active',
            'rate_limit_per_minute', 'rate_limit_per_hour', 'rate_limit_per_day',
            'allowed_ips', 'allowed_methods', 'allowed_endpoints',
            'requests_today', 'total_requests', 'last_used',
            'created_at', 'expires_at', 'secret_key'
        ]
        read_only_fields = [
            'key_id', 'user', 'requests_today', 'total_requests',
            'last_used', 'created_at'
        ]

    def create(self, validated_data):
        """
        Create a new API key
        """
        user = self.context['request'].user
        validated_data['user'] = user
        return super().create(validated_data)


class APILogSerializer(serializers.ModelSerializer):
    """
    Serializer for APILog model
    """
    api_key_name = serializers.CharField(source='api_key.name', read_only=True)
    
    class Meta:
        model = APILog
        fields = [
            'id', 'api_key', 'api_key_name', 'method', 'endpoint',
            'status_code', 'response_time', 'ip_address',
            'created_at'
        ]
        read_only_fields = fields


class APIVersionSerializer(serializers.ModelSerializer):
    """
    Serializer for APIVersion model
    """
    class Meta:
        model = APIVersion
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class APIRequestSerializer(serializers.Serializer):
    """
    Serializer for API request validation
    """
    api_key = serializers.CharField(required=True, max_length=50)
    signature = serializers.CharField(required=True)
    timestamp = serializers.IntegerField(required=True)
    
    def validate_timestamp(self, value):
        """
        Validate that timestamp is not too old (5 minutes)
        """
        from django.utils import timezone
        import time
        
        current_time = int(time.time())
        if abs(current_time - value) > 300:  # 5 minutes
            raise serializers.ValidationError('Timestamp is too old or in the future')
        return value


class PredictionRequestSerializer(serializers.Serializer):
    """
    Serializer for prediction requests
    """
    disease_type = serializers.ChoiceField(choices=[
        ('diabetes', 'Diabetes'),
        ('heart', 'Heart Disease'),
        ('kidney', 'Kidney Disease'),
        ('parkinson', 'Parkinson'),
        ('breast_cancer', 'Breast Cancer'),
        ('liver', 'Liver Disease')
    ])
    
    # Common parameters
    age = serializers.IntegerField(min_value=0, max_value=120, required=True)
    gender = serializers.ChoiceField(choices=[('male', 'Male'), ('female', 'Female')], required=True)
    
    # Disease-specific parameters
    parameters = serializers.JSONField(required=True)


class PredictionResponseSerializer(serializers.Serializer):
    """
    Serializer for prediction responses
    """
    prediction_id = serializers.CharField()
    disease_type = serializers.CharField()
    prediction = serializers.CharField()
    probability = serializers.FloatField()
    confidence_level = serializers.CharField()
    parameters_used = serializers.JSONField()
    timestamp = serializers.DateTimeField()
    recommendations = serializers.ListField(child=serializers.CharField())


class ErrorResponseSerializer(serializers.Serializer):
    """
    Serializer for error responses
    """
    error = serializers.CharField()
    code = serializers.CharField()
    message = serializers.CharField()
    timestamp = serializers.DateTimeField()
    request_id = serializers.CharField(required=False)


class RateLimitResponseSerializer(serializers.Serializer):
    """
    Serializer for rate limit responses
    """
    error = serializers.CharField(default='rate_limit_exceeded')
    message = serializers.CharField()
    retry_after = serializers.IntegerField()
    limit_type = serializers.CharField()
    current_usage = serializers.IntegerField()
    limit = serializers.IntegerField()