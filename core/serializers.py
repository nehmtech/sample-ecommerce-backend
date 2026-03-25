from rest_framework import serializers
from .models import Product, Category, CartItem, Cart, OrderItem, Order
from django.contrib.auth.models import User
from django.conf import settings

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name"]

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only = True, min_length = 8)
    password2 = serializers.CharField(write_only = True)
    
    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "password2", "first_name", "last_name"]
        
    def validate(self, data ):
        if data["password"] != data["password2"]:
            raise serializers.ValidationError("Password do not match")
        return data
    
    def create(self, validated_data):
        validated_data.pop("password2")
        user = User.objects.create_user(**validated_data)
        return user
    

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'created_at', 'is_active']


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source = 'category.name', read_only = True)
    image = serializers.SerializerMethodField()
    class Meta:
        model = Product
        fields = ['id', 'name', 'slug', 'description', 'price', 'stock', 'image', 'category_name', 'created_at', 'is_available']
        
    def get_image(self, obj):
        if not obj.image:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.image.url)
        return f'{settings.SITE_URL}{obj.image.url}'
        
class CartItemSerializer(serializers.ModelSerializer):
    
    product = ProductSerializer(read_only = True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset = Product.objects.all(), source = 'product', write_only = True
    )
    subtotal = serializers.SerializerMethodField()
    
    class Meta:
        model = CartItem
        fields = ["id", "product", "product_id", "quantity", "subtotal", "added_at"]
        
    
    def get_subtotal(self, obj):
        return obj.product.price * obj.quantity
    
    
    
    
class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many = True, read_only = True)
    total = serializers.SerializerMethodField()
    item_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Cart
        fields = ["id", "user", "items", "total", "item_count", "created_at", "updated_at"]
        
    
    def get_total(self, obj):
        return sum(item.product.price * item.quantity for item in obj.items.all())
    
    def get_item_count(self, obj):
        return sum(item.quantity for item in obj.items.all())
    
    
class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only = True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset = Product.objects.all(), source = 'product', write_only = True
    )
    
    
    class Meta:
        model = OrderItem
        fields = ["id", "product", "product_id", "quantity", "price"]
        
        
class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many = True, read_only = True)
    user = UserSerializer(read_only = True)
    
    class Meta:
        model = Order
        fields = ['id', 'user', 'status', 'total_price', 'items', 'shipping_address',
                  'shipping_city', 'shipping_postal_code', 'shipping_country', 'created_at',
                  'updated_at', 'paystack_reference', 'payment_status'
                  ]
        
class CreateOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = [
               'shipping_address',  'shipping_city', 
               'shipping_postal_code', 'shipping_country'
                  ]
    
    
        
    
   
    
    
        
        

