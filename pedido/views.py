from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import TemplateView, ListView, View
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Produto, ItemPedido, Pedido, Cliente, PedidoEntregue, PedidoCancelado
from django.http import HttpResponse
from django.db import transaction 
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
import pandas as pd 
import json
from django.db.models import Case, When, Value, IntegerField
from django.utils import timezone
from datetime import datetime
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from collections import defaultdict
import re


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

    def dispatch(self, request, *args, **kwargs):
        cliente_id = self.kwargs.get('cliente_id')
        cliente = get_object_or_404(Cliente, id=cliente_id)

        pedido_existente = Pedido.objects.filter(cliente=cliente).last()

        if pedido_existente and pedido_existente.liberado_para_caixa:
            print("entrou")
            return redirect('pag_final_cliente', pedido_id=pedido_existente.id)

        return super().dispatch(request, *args, **kwargs)
 
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

                for item in itens:
                    produto_id = item.get("produto_id")
                    quantidade = item.get("quantidade")

                    produto = Produto.objects.select_for_update().get(id=produto_id)

                    if produto.quantidade < quantidade:
                        mensagens_erro.append(
                            f'Produto "{produto.nome}" não tem estoque suficiente. Disponível: {produto.quantidade}'
                        )

                if mensagens_erro:
                    return JsonResponse({"status": "erro", "mensagens": mensagens_erro})

                pedido = Pedido.objects.create(
                    cliente=cliente,
                    metodo_pagamento=metodo_pagamento,
                    tipo_consumo=tipo_consumo,
                    observacoes=observacoes
                )

                # Agrupa os itens por produto_id somando a quantidade
                itens_agrupados = defaultdict(int)
                for item in itens:
                    produto_id = item.get("produto_id")
                    quantidade = item.get("quantidade")
                    itens_agrupados[produto_id] += quantidade

                for produto_id, quantidade_total in itens_agrupados.items():
                    produto = Produto.objects.select_for_update().get(id=produto_id)
                    
                    if produto.quantidade < quantidade_total:
                        mensagens_erro.append(
                            f'Produto "{produto.nome}" não tem estoque suficiente. Disponível: {produto.quantidade}'
                        )

                if mensagens_erro:
                    return JsonResponse({"status": "erro", "mensagens": mensagens_erro})

                pedido = Pedido.objects.create(
                    cliente=cliente,
                    metodo_pagamento=metodo_pagamento,
                    tipo_consumo=tipo_consumo,
                    observacoes=observacoes
                )

                for produto_id, quantidade_total in itens_agrupados.items():
                    produto = Produto.objects.select_for_update().get(id=produto_id)
                    ItemPedido.objects.create(pedido=pedido, produto=produto, quantidade=quantidade_total)
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

    def dispatch(self, request, *args, **kwargs):
        cliente_id = self.kwargs.get('cliente_id')
        cliente = get_object_or_404(Cliente, id=cliente_id)

        pedido_existente = Pedido.objects.filter(cliente=cliente).last()

        if pedido_existente and pedido_existente.liberado_para_caixa:
            print("entrou")
            return redirect('pag_final_cliente', pedido_id=pedido_existente.id)

        return super().dispatch(request, *args, **kwargs)

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
        pedido.observacoes = observacoes
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
        pedidos = Pedido.objects.filter(liberado_para_cozinha=True).order_by( # Só pedidos liberados e ordenados
        # Primeiro por tipo de consumo: viagem antes de local
            Case(
                When(tipo_consumo='viagem', then=Value(0)),
                When(tipo_consumo='local', then=Value(1)),
                default=Value(2),
                output_field=IntegerField(),
            ),
            'time_liberado_para_cozinha'  # depois por ordem de liberação  
        )
        return render(request, 'pag_cozinha.html', {'pedidos': pedidos})

    def post(self, request):
        data = json.loads(request.body)
        if data.get("acao") == "cancelar":
            try:
                pedido = Pedido.objects.get(pk=data["id"])
                
                # Salvar no modelo PedidoCancelado
                itens_str = " | ".join(f"{item.produto.nome} ({item.quantidade})" for item in pedido.itens.all())
                PedidoCancelado.objects.create(
                    cliente=pedido.cliente,
                    itens=itens_str,
                    metodo_pagamento=pedido.metodo_pagamento
                )

                # Devolver estoque
                for item in pedido.itens.all():
                    item.produto.quantidade += item.quantidade
                    item.produto.save()

                pedido.delete()  # Excluir pedido original

                return JsonResponse({"status": "success"})
            except Pedido.DoesNotExist:
                return JsonResponse({"status": "error", "message": "Pedido não encontrado"}, status=404)
        
        elif data.get("acao") == "confirmar":
            try:
                pedido = Pedido.objects.get(pk=data["id"])

                # Salvar como entregue
                itens_str = " | ".join(f"{item.produto.nome} ({item.quantidade})" for item in pedido.itens.all())
                PedidoEntregue.objects.create(
                    cliente=pedido.cliente,
                    itens=itens_str,
                    metodo_pagamento=pedido.metodo_pagamento,
                    total=pedido.total  # se aplicável
                )

                pedido.delete()

                return JsonResponse({"status": "success"})
            except Pedido.DoesNotExist:
                return JsonResponse({"status": "error", "message": "Pedido não encontrado"}, status=404)
 
        
        else:
            return JsonResponse({"status": "error", "message": "Ação inválida"}, status=400)
        

@method_decorator(staff_member_required, name='dispatch')
class CaixaView(View):
    def get(self, request):
        pedidos = Pedido.objects.filter(liberado_para_cozinha=False, liberado_para_caixa=True)
        return render(request, 'pag_caixa.html', {'pedidos': pedidos})

    def post(self, request):
        data = json.loads(request.body)

        if data.get("acao") == "cancelar":
            try:
                pedido = Pedido.objects.get(pk=data["id"])
                
                # Salvar no modelo PedidoCancelado
                itens_str = " | ".join(f"{item.produto.nome} ({item.quantidade})" for item in pedido.itens.all())
                PedidoCancelado.objects.create(
                    cliente=pedido.cliente,
                    itens=itens_str,
                    metodo_pagamento=pedido.metodo_pagamento
                )

                # Devolver estoque
                for item in pedido.itens.all():
                    item.produto.quantidade += item.quantidade
                    item.produto.save()

                pedido.delete()

                return JsonResponse({"status": "success"})
            except Pedido.DoesNotExist:
                return JsonResponse({"status": "error", "message": "Pedido não encontrado"}, status=404)
        
           
        else:
            try:
                pedido_id = data.get("pedido_id")

                if not pedido_id:
                    return JsonResponse({'success': False, 'error': 'ID do pedido não encontrado'})

                pedido = get_object_or_404(Pedido, id=pedido_id)

                pedido.liberado_para_cozinha = True
                pedido.time_liberado_para_cozinha = timezone.now()
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
                    # item.quantidade = nova_quantidade
                    # item.save()
                    diferenca = nova_quantidade - item.quantidade
                    if diferenca > 0:
                        if item.produto.quantidade >= diferenca:
                            item.produto.quantidade -= diferenca
                            item.produto.save()
                            item.quantidade = nova_quantidade
                            item.save()

        return redirect('detalhe_pedido', pedido_id=pedido.id)

    return render(request, 'pag_detalhe_pedido.html', {'pedido': pedido, 'modo_edicao': True})


@staff_member_required
def pedidos_json(request):
    pedidos = Pedido.objects.filter(liberado_para_cozinha=True).order_by(
        Case(
            When(tipo_consumo='viagem', then=Value(0)),
            When(tipo_consumo='local', then=Value(1)),
            default=Value(2),
            output_field=IntegerField(),
        ),
        'time_liberado_para_cozinha'
    )

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
# def pedidos_json(request):
#     pedidos = Pedido.objects.filter(liberado_para_cozinha=True).order_by('-id').reverse()

#     lista = []
#     for pedido in pedidos:
#         itens = [f"{item.produto.nome} ({item.quantidade})" for item in pedido.itens.all()]
#         lista.append({
#             'id': pedido.id,
#             'cliente': pedido.cliente.nome,
#             'itens': ' | '.join(itens),
#             'observacoes': pedido.observacoes,
#             'tipo_consumo': pedido.tipo_consumo,
#         })

#     return JsonResponse({'pedidos': lista})

@staff_member_required
def pedidos_caixa_json(request):
    pedidos = Pedido.objects.filter(
        liberado_para_cozinha=False,
        liberado_para_caixa=True
    ).order_by('-id').reverse()

    lista = []
    for pedido in pedidos:
        itens_agrupados = defaultdict(int)
        for item in pedido.itens.all():
            itens_agrupados[item.produto.nome] += item.quantidade

        itens_formatados = [f"{nome} (x{quantidade})" for nome, quantidade in itens_agrupados.items()]

        lista.append({
            'id': pedido.id,
            'cliente': pedido.cliente.nome,
            'itens': ' | '.join(itens_formatados),
            'observacoes': pedido.observacoes,
            'metodo_pagamento': pedido.metodo_pagamento,
            'tipo_consumo': pedido.tipo_consumo,
        })

    return JsonResponse({'pedidos': lista})


@csrf_exempt
def cancelar_pedido(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            pedido_id = data.get('pedido_id')
            pedido = Pedido.objects.get(id=pedido_id)

            if pedido.liberado_para_caixa or pedido.liberado_para_cozinha:
                return JsonResponse({'success': False, 'error': 'Pedido já em andamento, não pode ser cancelado'})

            itens_str = " | ".join([f"{item.produto.nome} ({item.quantidade})" for item in pedido.itens.all()])
            PedidoCancelado.objects.create(
                cliente=pedido.cliente,
                itens=itens_str,
                metodo_pagamento=pedido.metodo_pagamento,
            )

            # Retorna ao estoque
            for item in pedido.itens.all():
                item.produto.quantidade += item.quantidade
                item.produto.save()

            pedido.delete()

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    else:
        return JsonResponse({'success': False, 'error': 'Método não permitido'})
    

# Garante que apenas admins acessem essa view
@staff_member_required 
def exportar_excel_pedidos(request):
    pedidos = PedidoEntregue.objects.all().order_by('-entregue_em')

    dados = []
    total_dinheiro = 0
    total_pix = 0
    vendas_por_produto = defaultdict(int)

    for pedido in pedidos:
        metodo = pedido.metodo_pagamento.lower()
        total = float(pedido.total)

        if metodo == "dinheiro":
            total_dinheiro += total
        elif metodo == "pix":
            total_pix += total

        itens_texto = str(pedido.itens)
        itens = re.findall(r'([^\(,]+)\s*\(?(\d+)?\)?', itens_texto)

        for nome_item, qtd in itens:
            nome_item = nome_item.strip()
            quantidade = int(qtd) if qtd else 1
            vendas_por_produto[nome_item] += quantidade

        dados.append({
            "Cliente": pedido.cliente.nome,
            "Itens": pedido.itens,
            "Total (R$)": total,
            "Forma de Pagamento": pedido.metodo_pagamento,
        })

    df_pedidos = pd.DataFrame(dados)

    hoje = datetime.now()
    data_formatada = hoje.strftime("%d/%m/%Y")
    nome_arquivo = f'Cantina JID - {hoje.strftime("%d/%m")}.xlsx'
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{nome_arquivo}"'

    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        workbook = writer.book
        ws = workbook.create_sheet(title='Relatório')

        ws.sheet_view.showGridLines = False

        # Estilos
        header_font = Font(bold=True, color="FFFFFF", size=11)
        header_fill = PatternFill(start_color="305496", end_color="305496", fill_type="solid")
        title_font = Font(bold=True, size=14, color="1F4E78")
        destaque_font = Font(bold=True, size=12)
        destaque_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
        total_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
        alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        left_alignment = Alignment(horizontal="left", vertical="center")
        border = Border(bottom=Side(border_style="thin", color="000000"))

        # Nova borda fina completa
        thin_border = Border(
            left=Side(border_style="thin", color="000000"),
            right=Side(border_style="thin", color="000000"),
            top=Side(border_style="thin", color="000000"),
            bottom=Side(border_style="thin", color="000000")
        )

        row = 1

        # TÍTULO
        ws.cell(row=row, column=1).value = f"RESUMO DE VENDAS - {data_formatada}"
        ws.cell(row=row, column=1).font = title_font
        ws.cell(row=row, column=1).alignment = left_alignment
        row += 2

        # TOTAL DE VENDAS
        ws.cell(row=row, column=1).value = "TOTAL RECEBIDO EM DINHEIRO:"
        ws.cell(row=row, column=1).font = destaque_font
        ws.cell(row=row, column=1).fill = destaque_fill
        ws.cell(row=row, column=2).value = total_dinheiro
        ws.cell(row=row, column=2).number_format = 'R$ #,##0.00'
        ws.cell(row=row, column=2).fill = destaque_fill
        row += 1

        ws.cell(row=row, column=1).value = "TOTAL RECEBIDO EM PIX:"
        ws.cell(row=row, column=1).font = destaque_font
        ws.cell(row=row, column=1).fill = destaque_fill
        ws.cell(row=row, column=2).value = total_pix
        ws.cell(row=row, column=2).number_format = 'R$ #,##0.00'
        ws.cell(row=row, column=2).fill = destaque_fill
        row += 1

        ws.cell(row=row, column=1).value = "TOTAL GERAL:"
        ws.cell(row=row, column=1).font = Font(bold=True, size=13, color="006100")
        ws.cell(row=row, column=1).fill = total_fill
        ws.cell(row=row, column=2).value = total_dinheiro + total_pix
        ws.cell(row=row, column=2).number_format = 'R$ #,##0.00'
        ws.cell(row=row, column=2).fill = total_fill
        row += 2

        # PRODUTOS VENDIDOS
        ws.cell(row=row, column=1).value = "Produto"
        ws.cell(row=row, column=2).value = "Quantidade Vendida"
        for col in range(1, 3):
            cell = ws.cell(row=row, column=col)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = alignment
            cell.border = thin_border
            ws.column_dimensions[get_column_letter(col)].width = 35
        row += 1

        for produto, qtd in sorted(vendas_por_produto.items()):
            ws.cell(row=row, column=1).value = produto
            ws.cell(row=row, column=2).value = qtd
            for col in range(1, 3):
                cell = ws.cell(row=row, column=col)
                cell.alignment = left_alignment if col == 1 else alignment
                cell.border = thin_border
            row += 1

        row += 2  # espaço antes da tabela de pedidos

        # TABELA DE PEDIDOS
        for col_num, column_title in enumerate(df_pedidos.columns, 1):
            cell = ws.cell(row=row, column=col_num)
            cell.value = column_title
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = alignment
            cell.border = thin_border
            ws.column_dimensions[get_column_letter(col_num)].width = 40
        row += 1

        for i, registro in df_pedidos.iterrows():
            for j, value in enumerate(registro, 1):
                cell = ws.cell(row=row + i, column=j)
                cell.value = value
                if j == 3:
                    cell.number_format = 'R$ #,##0.00'
                elif j == 5:
                    cell.number_format = 'DD/MM/YYYY HH:MM'
                cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
                cell.border = thin_border

    return response
