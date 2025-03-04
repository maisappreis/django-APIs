from django.urls import path
from .views import *


urlpatterns = [
    path('expense/', ExpenseListView.as_view(), name='expense-list'),
    path('expense/create/', ExpenseCreateView.as_view(), name='expense-create'),
    path('expense/<int:pk>/', ExpenseUpdateDestroyView.as_view(), name='expense-update-destroy'),
    
    path('revenue/', RevenueListView.as_view(), name='revenue-list'),
    path('revenue/create/', RevenueCreateView.as_view(), name='revenue-create'),
    path('revenue/<int:pk>/', RevenueUpdateDestroyView.as_view(), name='revenue-update-destroy'),

    path('agenda/', AgendaListView.as_view(), name='agenda-list'),
    path('agenda/create/', AgendaCreateView.as_view(), name='agenda-create'),
    path('agenda/<int:pk>/', AgendaUpdateDestroyView.as_view(), name='agenda-update-destroy'),

    path('month_closing/', MonthClosingListView.as_view(), name='month-closing-list'),
    path('month_closing/create/', MonthClosingCreateUpdateView.as_view(), name='month-closing-create'),
    path('month_closing/<int:pk>/', MonthClosingCreateUpdateView.as_view(), name='month-closing-create'),

    path('profit_list/', ProfitListView.as_view(), name='profit-list'),
    path('update-net-values/', UpdateNetValuesView.as_view(), name='update-net-values'),
    
    path('test/expense/', ExpenseTestListView.as_view(), name='expense-list'),
    path('test/expense/create/', ExpenseTestCreateView.as_view(), name='expense-create'),
    path('test/expense/<int:pk>/', ExpenseTestUpdateDestroyView.as_view(), name='expense-update-destroy'),
    
    path('test/revenue/', RevenueTestListView.as_view(), name='revenue-list'),
    path('test/revenue/create/', RevenueTestCreateView.as_view(), name='revenue-create'),
    path('test/revenue/<int:pk>/', RevenueTestUpdateDestroyView.as_view(), name='revenue-update-destroy'),

    path('test/agenda/', AgendaTestListView.as_view(), name='agenda-list'),
    path('test/agenda/create/', AgendaTestCreateView.as_view(), name='agenda-create'),
    path('test/agenda/<int:pk>/', AgendaTestUpdateDestroyView.as_view(), name='agenda-update-destroy'),

    path('test/month_closing/', MonthClosingTestListView.as_view(), name='month-closing-list'),
    path('test/month_closing/create/', MonthClosingTestCreateUpdateView.as_view(), name='month-closing-create'),
    path('test/month_closing/<int:pk>/', MonthClosingTestCreateUpdateView.as_view(), name='month-closing-create'),
   
    path('test/profit_list/', ProfitTestListView.as_view(), name='profit-list'),
    path('test/update-net-values/', UpdateNetValuesTestView.as_view(), name='update-net-values'),
]