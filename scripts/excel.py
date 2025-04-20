import os
import sys
import django
import pandas as pd

# Ajuste aqui com o nome da sua pasta de configurações!
# Caminho até a pasta base do projeto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jid_cantina.settings')
django.setup()

from pedido.models import PedidoEntregue

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
df.to_excel("pedidos_exportados.xlsx", index=False)

print("Arquivo Excel gerado com sucesso!")

# python ./scripts/excel.py  
