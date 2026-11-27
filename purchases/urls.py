from django.urls import path

from . import views

app_name = 'purchases'
urlpatterns = [
    path('', views.InvoiceList.as_view(), name='list'),
    path('datos/', views.InvoiceData.as_view(), name='data'),
    path('nueva/', views.invoice_edit, name='create'),
    path('seleccion/<str:kind>/', views.choices, name='choices'),
    path('proveedores/', views.SupplierList.as_view(), name='suppliers'),
    path('proveedores/datos/', views.SupplierData.as_view(), name='supplier-data'),
    path('proveedores/nuevo/', views.SupplierCreate.as_view(), name='supplier-create'),
    path('proveedores/<int:pk>/', views.SupplierDetail.as_view(), name='supplier'),
    path('proveedores/<int:pk>/editar/', views.SupplierUpdate.as_view(), name='supplier-edit'),
    path('proveedores/<int:pk>/precios/', views.PriceData.as_view(), name='price-data'),
    path('proveedores/<int:pk>/precios/nuevo/', views.reference_price, name='price-create'),
    path('<int:pk>/', views.InvoiceDetail.as_view(), name='invoice'),
    path('<int:pk>/corregir/', views.invoice_edit, name='correct'),
    path('<int:pk>/lineas/', views.invoice_lines, name='lines'),
    path('<int:pk>/recibir/', views.invoice_action, {'action': 'receive'}, name='receive'),
    path('<int:pk>/anular/', views.invoice_action, {'action': 'cancel'}, name='cancel'),
    path('<int:pk>/pagar/', views.invoice_action, {'action': 'pay'}, name='pay'),
]
