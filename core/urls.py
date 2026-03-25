from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    # Auth
    path('auth/register/', views.RegisterView.as_view(), name='register'),
    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('auth/logout/', views.LogoutView.as_view(), name='logout'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/me/', views.MeView.as_view(), name='me'),

    # Categories
    path('categories/', views.CategoryListView.as_view(), name='category-list'),
    path('categories/<slug:slug>/', views.CategoryDetailView.as_view(), name='category-detail'),

    # Products
    path('products/', views.ProductListView.as_view(), name='product-list'),
    path('products/<slug:slug>/', views.ProductDetailView.as_view(), name='product-detail'),

    # Cart
    path('cart/', views.CartView.as_view(), name='cart'),
    path('cart/add/', views.AddToCartView.as_view(), name='cart-add'),
    path('cart/items/<int:item_id>/update/', views.UpdateCartItemView.as_view(), name='cart-update'),
    path('cart/items/<int:item_id>/remove/', views.RemoveCartItemView.as_view(), name='cart-remove'),
    path('cart/clear/', views.ClearCartView.as_view(), name='cart-clear'),

    # Orders
    path('orders/', views.OrderListView.as_view(), name='order-list'),
    path('orders/<int:order_id>/', views.OrderDetailView.as_view(), name='order-detail'),
    
    # Payments
    path('orders/<int:order_id>/pay/', views.InitializePaymentView.as_view(), name='order-pay'),
    path('orders/<int:order_id>/verify/', views.VerifyPaymentView.as_view(), name='order-verify'),
]