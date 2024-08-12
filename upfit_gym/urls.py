from django.urls import path
from .views import *

urlpatterns = [
    path('customers/', CustomerListView.as_view(), name='customer-list'),
    path('customers/create/', CustomerCreateView.as_view(), name='customer-create'),
    path('customers/<int:pk>/', CustomerUpdateDestroyView.as_view(), name='customer-update-destroy'),
    
    path('expenses/', ExpenseListView.as_view(), name='expense-list'),
    path('expenses/create/', ExpenseCreateView.as_view(), name='expense-create'),
    path('expenses/<int:pk>/', ExpenseUpdateDestroyView.as_view(), name='expense-update-destroy'),
    
    path('revenues/', RevenueListView.as_view(), name='revenue-list'),
    path('revenues/create/', RevenueCreateView.as_view(), name='revenue-create'),
    path('revenues/<int:pk>/', RevenueUpdateDestroyView.as_view(), name='revenue-update-destroy'),
]