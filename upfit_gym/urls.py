from django.urls import path
from .views import (
    CustomerListView,
    CustomerCreateView,
    CustomerUpdateDestroyView,
    ExpenseListView,
    ExpenseCreateView,
    ExpenseUpdateDestroyView,
    RevenueListView,
    RevenueCreateView,
    RevenueUpdateDestroyView,
)

urlpatterns = [
    path('customer/', CustomerListView.as_view(), name='customer-list'),
    path('customer/create/', CustomerCreateView.as_view(), name='customer-create'),
    path('customer/<int:pk>/', CustomerUpdateDestroyView.as_view(), name='customer-update-destroy'),
    
    path('expense/', ExpenseListView.as_view(), name='expense-list'),
    path('expense/create/', ExpenseCreateView.as_view(), name='expense-create'),
    path('expense/<int:pk>/', ExpenseUpdateDestroyView.as_view(), name='expense-update-destroy'),
    
    path('revenue/', RevenueListView.as_view(), name='revenue-list'),
    path('revenue/create/', RevenueCreateView.as_view(), name='revenue-create'),
    path('revenue/<int:pk>/', RevenueUpdateDestroyView.as_view(), name='revenue-update-destroy'),
]