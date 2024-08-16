from django.urls import path
from .views import *
from .views_test import *

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

    path('test/customer/', CustomerTestListView.as_view(), name='customer-list'),
    path('test/customer/create/', CustomerTestCreateView.as_view(), name='customer-create'),
    path('test/customer/<int:pk>/', CustomerTestUpdateDestroyView.as_view(), name='customer-update-destroy'),
    
    path('test/expense/', ExpenseTestListView.as_view(), name='expense-list'),
    path('test/expense/create/', ExpenseTestCreateView.as_view(), name='expense-create'),
    path('test/expense/<int:pk>/', ExpenseTestUpdateDestroyView.as_view(), name='expense-update-destroy'),
    
    path('test/revenue/', RevenueTestListView.as_view(), name='revenue-list'),
    path('test/revenue/create/', RevenueTestCreateView.as_view(), name='revenue-create'),
    path('test/revenue/<int:pk>/', RevenueTestUpdateDestroyView.as_view(), name='revenue-update-destroy'),
]