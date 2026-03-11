from django.urls import path
from .views import *


urlpatterns = [
    path('expense/', ExpenseListView.as_view(), name='expense-list'),
    path('expense/create/', ExpenseCreateView.as_view(), name='expense-create'),
    path('expense/<int:pk>/', ExpenseUpdateDestroyView.as_view(), name='expense-update-destroy'),
    
    path('revenue/', RevenueListView.as_view(), name='revenue-list'),
    path('revenue/create/', RevenueCreateView.as_view(), name='revenue-create'),
    path('revenue/<int:pk>/', RevenueUpdateDestroyView.as_view(), name='revenue-update-destroy'),

    path('appointment/', AppointmentListView.as_view(), name='appointment-list'),
    path('appointment/create/', AppointmentCreateView.as_view(), name='appointment-create'),
    path('appointment/<int:pk>/', AppointmentUpdateDestroyView.as_view(), name='appointment-update-destroy'),

    path('month_closing/', MonthClosingListView.as_view(), name='month-closing-list'),
    path('month_closing/create/', MonthClosingCreateView.as_view(), name='month-closing-create'),
    path('month_closing/<int:pk>/', MonthClosingUpdateDestroyView.as_view(), name='month-closing-update-destroy'),

    path('update_net_values/', UpdateNetValuesView.as_view(), name='update-net-values'),
    path('dashboard_charts/', DashboardChartsView.as_view(), name='dashboard-charts-list')
]