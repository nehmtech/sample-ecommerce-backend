from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from .models import Category, Product, Cart, CartItem, Order, OrderItem
from .serializers import (
    UserSerializer, RegisterSerializer, CategorySerializer,
    ProductSerializer, CartSerializer, CartItemSerializer,
    OrderSerializer, CreateOrderSerializer
)

import requests
import uuid
from django.conf import settings


# ─── Auth ────────────────────────────────────────────────────────────────────

class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            Cart.objects.create(user=user)          # auto-create cart
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            })
        return Response({'detail': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'detail': 'Logged out successfully.'})
        except Exception:
            return Response({'detail': 'Invalid token.'}, status=status.HTTP_400_BAD_REQUEST)


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)


# ─── Categories ──────────────────────────────────────────────────────────────

class CategoryListView(generics.ListCreateAPIView):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = 'slug'
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


# ─── Products ────────────────────────────────────────────────────────────────

class ProductListView(generics.ListCreateAPIView):
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = Product.objects.filter(is_available=True).select_related('category')
        category = self.request.query_params.get('category')
        search = self.request.query_params.get('search')
        if category:
            qs = qs.filter(category__slug=category)
        if search:
            qs = qs.filter(name__icontains=search)
        return qs


class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    lookup_field = 'slug'
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


# ─── Cart ─────────────────────────────────────────────────────────────────────

class CartView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return Response(CartSerializer(cart).data)


class AddToCartView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 1))

        product = get_object_or_404(Product, id=product_id, is_available=True)

        if product.stock < quantity:
            return Response({'detail': 'Not enough stock.'}, status=status.HTTP_400_BAD_REQUEST)

        item, created = CartItem.objects.get_or_create(cart=cart, 
                                                       product=product,
                                                       defaults={'quantity': quantity}
                                                       )
        if not created:
            item.quantity += quantity
        else:
            item.quantity = quantity
        item.save()

        return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)


class UpdateCartItemView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def patch(self, request, item_id):
        item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        quantity = int(request.data.get('quantity', 1))
        if quantity <= 0:
            item.delete()
        else:
            if item.product.stock < quantity:
                return Response({'detail': 'Not enough stock.'}, status=status.HTTP_400_BAD_REQUEST)
            item.quantity = quantity
            item.save()
        cart = Cart.objects.get(user=request.user)
        return Response(CartSerializer(cart).data)


class RemoveCartItemView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def delete(self, request, item_id):
        item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        item.delete()
        cart = Cart.objects.get(user=request.user)
        return Response(CartSerializer(cart).data)
    

class ClearCartView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def delete(self, request):
        cart = get_object_or_404(Cart, user=request.user)
        cart.items.all().delete()
        return Response(CartSerializer(cart).data)


# ─── Orders ──────────────────────────────────────────────────────────────────
class OrderListView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        orders = Order.objects.filter(user=request.user).prefetch_related('items__product')
        return Response(OrderSerializer(orders, many=True).data)

    def post(self, request):
        serializer = CreateOrderSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        cart = get_object_or_404(Cart, user=request.user)
        cart_items = cart.items.select_related('product').all()

        if not cart_items.exists():
            return Response({'detail': 'Cart is empty.'}, status=status.HTTP_400_BAD_REQUEST)

        # Stock validation
        for item in cart_items:
            if item.product.stock < item.quantity:
                return Response(
                    {'detail': f'Not enough stock for {item.product.name}.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        total = sum(item.product.price * item.quantity for item in cart_items)

        order = Order.objects.create(
            user=request.user,
            total_price=total,
            **serializer.validated_data
        )

        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )
            # Deduct stock
            item.product.stock -= item.quantity
            item.product.save()

        cart.items.all().delete()

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class OrderDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request, order_id):
        order = get_object_or_404(Order, id=order_id, user=request.user)
        return Response(OrderSerializer(order).data)


class InitializePaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, order_id):
        order = get_object_or_404(Order, id=order_id, user=request.user)

        if order.payment_status == 'paid':
            return Response({'detail': 'Order already paid.'}, status=status.HTTP_400_BAD_REQUEST)

        reference = f"order-{order.id}-{uuid.uuid4().hex[:8]}"

        payload = {
            'email': request.user.email,
            'amount': int(order.total_price * 100),  # Paystack uses kobo/cents
            'reference': reference,
            'callback_url': f"{settings.FRONTEND_URL}/orders/{order.id}/verify",
            'metadata': {
                'order_id': order.id,
                'user_id': request.user.id,
            }
        }
        

        headers = {
            'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
            'Content-Type': 'application/json',
        }

        response = requests.post(
            'https://api.paystack.co/transaction/initialize',
            json=payload,
            headers=headers
        )

        if response.status_code == 200:
            data = response.json()
            order.paystack_reference = reference
            order.save()
            return Response({
                'authorization_url': data['data']['authorization_url'],
                'reference': reference,
            })

        return Response({'detail': 'Payment initialization failed.'}, status=status.HTTP_400_BAD_REQUEST)


class VerifyPaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, order_id):
        order = get_object_or_404(Order, id=order_id, user=request.user)
        reference = order.paystack_reference

        if not reference:
            return Response({'detail': 'No payment reference found.'}, status=status.HTTP_400_BAD_REQUEST)

        headers = {
            'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
        }

        response = requests.get(
            f'https://api.paystack.co/transaction/verify/{reference}',
            headers=headers
        )

        if response.status_code == 200:
            data = response.json()['data']
            if data['status'] == 'success':
                order.payment_status = 'paid'
                order.status = 'paid'
                order.save()
                return Response({'detail': 'Payment verified.', 'order': OrderSerializer(order).data})
            else:
                order.payment_status = 'failed'
                order.save()
                return Response({'detail': 'Payment not successful.'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'detail': 'Verification failed.'}, status=status.HTTP_400_BAD_REQUEST)