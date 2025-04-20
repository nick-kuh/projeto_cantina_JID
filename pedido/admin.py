from django.contrib import admin
from .models import Produto, Pedido, ItemPedido, Cliente, PedidoEntregue

admin.site.register(Produto)
admin.site.register(Pedido)
admin.site.register(ItemPedido)
admin.site.register(Cliente)
admin.site.register(PedidoEntregue)