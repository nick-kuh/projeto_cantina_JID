from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import TemplateView, ListView, View
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Produto, ItemPedido, Pedido, Cliente, PedidoEntregue
from django.http import HttpResponse
from django.db import transaction 
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
import pandas as pd 
import json

class PagInicial(TemplateView):
    template_name = "pag_inicial.html"

@csrf_exempt
def salvar_nome(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        nome = data.get('nome')

        if nome:
            cliente = Cliente.objects.create(nome=nome)
            return JsonResponse({'redirect_url': f'/pedido/{cliente.id}/'})
        
        return JsonResponse({'erro': 'Nome não pode estar vazio'}, status=400)

    return JsonResponse({'erro': 'Método não permitido'}, status=405)

class PagCliente(ListView):
    template_name = "pag_cliente.html"
    model = Produto  

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        cliente_id = self.kwargs.get('cliente_id')
        cliente = get_object_or_404(Cliente, id=cliente_id)

        context['cliente'] = cliente
        context['lista_produtos'] = Produto.objects.all()
        context['lista_pedidos'] = Pedido.objects.filter(cliente=cliente)
        context['lista_itens_pedidos'] = ItemPedido.objects.filter(pedido__cliente=cliente)

        return context

 
    def post(self, request, cliente_id):
        try:
            data = json.loads(request.body)

            metodo_pagamento = data.get("metodo_pagamento")
            tipo_consumo = data.get("tipo_consumo")
            observacoes = data.get("observacoes", "")
            itens = data.get("itens")

            if not metodo_pagamento or not tipo_consumo or not itens:
                return JsonResponse({"status": "erro", "mensagens": ["Dados incompletos."]})

            mensagens_erro = []

            with transaction.atomic():
                cliente = get_object_or_404(Cliente, id=cliente_id)

                # Verifica o estoque antes de criar o pedido
                for item in itens:
                    produto_id = item.get("produto_id")
                    quantidade = item.get("quantidade")

                    produto = get_object_or_404(Produto, id=produto_id)

                    if produto.quantidade < quantidade:
                        mensagens_erro.append(
                            f'Produto "{produto.nome}" não tem estoque suficiente. Disponível: {produto.quantidade}'
                        )

                if mensagens_erro:
                    return JsonResponse({"status": "erro", "mensagens": mensagens_erro})

                # Agora que sabemos que tem estoque, criamos o pedido
                pedido = Pedido.objects.create(
                    cliente=cliente,
                    metodo_pagamento=metodo_pagamento,
                    tipo_consumo=tipo_consumo,
                    observacoes=observacoes
                )

                for item in itens:
                    produto_id = item.get("produto_id")
                    quantidade = item.get("quantidade")

                    produto = get_object_or_404(Produto, id=produto_id)

                    ItemPedido.objects.create(pedido=pedido, produto=produto, quantidade=quantidade)
                    produto.quantidade -= quantidade
                    produto.save()

            return JsonResponse({"status": "ok", "pedido_id": pedido.id})

        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return JsonResponse({"status": "erro", "mensagens": [str(e)]}, status=500)

    

class EscolherLocalView(View):
    template_name = "pag_escolher_local.html"

    def get(self, request, cliente_id):
        return render(request, self.template_name, {"cliente_id": cliente_id})

    def post(self, request, cliente_id):
        tipo_consumo = request.POST.get("tipo_consumo", "").lower()
        observacoes = request.POST.get("observacoes", "")

        if tipo_consumo not in ["local", "viagem"]:
            return JsonResponse({"erro": "Opção inválida"}, status=400)

        cliente = get_object_or_404(Cliente, id=cliente_id)
        pedido = Pedido.objects.filter(cliente=cliente).last()

        if not pedido:
            return JsonResponse({"erro": "Nenhum pedido aberto encontrado"}, status=404)

        pedido.tipo_consumo = tipo_consumo
        pedido.observacoes = observacoes  # <- aqui!
        pedido.liberado_para_caixa = True
        pedido.save()

        return JsonResponse({"mensagem": "Tipo de consumo salvo com sucesso", "pedido_id": pedido.id})


class PagFinalCliente(TemplateView):
    pedido = Pedido.objects.all()
    template_name = "pag_final_cliente.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pedido_id = self.kwargs.get("pedido_id")
        context["pedido"] = get_object_or_404(Pedido, id=pedido_id)
        return context

@method_decorator(staff_member_required, name='dispatch')
class CozinhaView(View):
    def get(self, request):
        pedidos = Pedido.objects.filter(liberado_para_cozinha=True)  # Só pedidos liberados
        return render(request, 'pag_cozinha.html', {'pedidos': pedidos})

    def post(self, request):
        try:
            data = json.loads(request.body)
            pedido_id = data.get("pedido_id")

            if not pedido_id:
                return JsonResponse({'success': False, 'error': 'ID do pedido não encontrado'})

            pedido = get_object_or_404(Pedido, id=pedido_id)

            cliente = pedido.cliente
            itens_pedido = ", ".join([f"{item.produto.nome} ({item.quantidade})" for item in pedido.itens.all()])
            
            PedidoEntregue.objects.create(cliente=cliente, itens=itens_pedido, total=pedido.total,
            metodo_pagamento=pedido.metodo_pagamento)

            pedido.delete()

            return JsonResponse({'success': True})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
        

@method_decorator(staff_member_required, name='dispatch')
class CaixaView(View):
    def get(self, request):
        pedidos = Pedido.objects.filter(liberado_para_cozinha=False, liberado_para_caixa=True)  # Só pedidos liberados para caixa
        return render(request, 'pag_caixa.html', {'pedidos': pedidos})

    def post(self, request):
        try:
            data = json.loads(request.body)
            pedido_id = data.get("pedido_id")

            if not pedido_id:
                return JsonResponse({'success': False, 'error': 'ID do pedido não encontrado'})

            pedido = get_object_or_404(Pedido, id=pedido_id)

            pedido.liberado_para_cozinha = True
            pedido.save()

            return JsonResponse({'success': True})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
        
def detalhe_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    return render(request, 'pag_detalhe_pedido.html', {'pedido': pedido})

def editar_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)

    if request.method == 'POST':
        observacoes = request.POST.get('observacoes', '')
        pedido.observacoes = observacoes
        pedido.save()

        for item in pedido.itens.all():
            nova_quantidade = int(request.POST.get(f'quantidade_{item.id}', item.quantidade))
            if nova_quantidade != item.quantidade:
                if nova_quantidade == 0:
                    PedidoEntregue.objects.create(
                        cliente=pedido.cliente,
                        itens=f"{item.produto.nome} ({item.quantidade})"
                    )
                    item.delete()
                elif nova_quantidade < item.quantidade:
                    diferenca = item.quantidade - nova_quantidade
                    PedidoEntregue.objects.create(
                        cliente=pedido.cliente,
                        itens=f"{item.produto.nome} ({diferenca})"
                    )
                    item.quantidade = nova_quantidade
                    item.save()
                else:
                    item.quantidade = nova_quantidade
                    item.save()

        return redirect('detalhe_pedido', pedido_id=pedido.id)

    return render(request, 'pag_detalhe_pedido.html', {'pedido': pedido, 'modo_edicao': True})

# Garante que apenas admins acessem essa view
@staff_member_required 
def exportar_excel_pedidos(request):
    dados = []

    for pedido in PedidoEntregue.objects.all():
        dados.append({
            "Cliente": pedido.cliente.nome,
            "Itens": pedido.itens,
            "Total": float(pedido.total),
            "Forma de Pagamento": pedido.metodo_pagamento,
            "Entregue em": pedido.entregue_em.strftime("%d/%m/%Y %H:%M"),
        })

    df = pd.DataFrame(dados)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="pedidos_exportados.xlsx"'
    df.to_excel(response, index=False)
    return response


@staff_member_required
def pedidos_json(request):
    pedidos = Pedido.objects.filter(liberado_para_cozinha=True).order_by('-id').reverse()

    lista = []
    for pedido in pedidos:
        itens = [f"{item.produto.nome} ({item.quantidade})" for item in pedido.itens.all()]
        lista.append({
            'id': pedido.id,
            'cliente': pedido.cliente.nome,
            'itens': ' | '.join(itens),
            'observacoes': pedido.observacoes,
            'tipo_consumo': pedido.tipo_consumo,
        })

    return JsonResponse({'pedidos': lista})

@staff_member_required
def pedidos_caixa_json(request):
    pedidos = Pedido.objects.filter(liberado_para_cozinha=False, liberado_para_caixa=True).order_by('-id').reverse()

    lista = []
    for pedido in pedidos:
        itens = [f"{item.produto.nome} ({item.quantidade})" for item in pedido.itens.all()]
        lista.append({
            'id': pedido.id,
            'cliente': pedido.cliente.nome,
            'itens': ' | '.join(itens),
            'metodo_pagamento':pedido.metodo_pagamento,
            'tipo_consumo': pedido.tipo_consumo,
            'total': f"{pedido.total:.2f}".replace('.', ',') if pedido.total else "0,00",
        })

    return JsonResponse({'pedidos': lista})



