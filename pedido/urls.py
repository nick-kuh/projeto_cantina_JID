from django.urls import path, include
from .views import PagInicial, PagCliente, EscolherLocalView ,PagFinalCliente, salvar_nome, CozinhaView, CaixaView,detalhe_pedido, editar_pedido, exportar_excel_pedidos

urlpatterns = [
    path('', PagInicial.as_view()),
    path('salvar_nome/', salvar_nome, name='salvar_nome'),
    path("pedido/<int:cliente_id>/", PagCliente.as_view(), name="pag_cliente"),
    path("pedido/<int:cliente_id>/escolher-local/", EscolherLocalView.as_view(), name="escolher_local"),
    path('pedido/<int:pedido_id>/final/', PagFinalCliente.as_view(), name='pag_final_cliente'),
    path('caixa/', CaixaView.as_view(), name='caixa'),
    path('cozinha/', CozinhaView.as_view(), name='cozinha'),
    path('cozinha/<int:pedido_id>/', detalhe_pedido, name='detalhe_pedido'),
    path('cozinha/<int:pedido_id>/editar/', editar_pedido, name='editar_pedido'),
    path('excel/', exportar_excel_pedidos, name='exportar_excel'),
] 