from django.contrib import admin
from .models import Produto, Pedido, ItemPedido, Cliente, PedidoEntregue, PedidoCancelado

admin.site.register(Produto)
admin.site.register(Pedido)
admin.site.register(ItemPedido)
admin.site.register(Cliente)
admin.site.register(PedidoEntregue)
admin.site.register(PedidoCancelado)