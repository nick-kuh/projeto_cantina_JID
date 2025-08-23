from django.db import models

class Cliente(models.Model):
    nome = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.id} - {self.nome}" 

class Produto(models.Model):
    CATEGORIAS = [
        ('Salgados', 'Salgados'),
        ('Doces', 'Doces'),
        ('Bebidas', 'Bebidas'),
        ('Caldos', 'Caldos'),
        ('Combos', 'Combos')
    ]

    nome = models.CharField(max_length=70, unique=True) 
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    imagem = models.ImageField(upload_to='imagem_produto', null=True, blank=True)
    quantidade = models.PositiveIntegerField(default=0)
    categoria = models.CharField(max_length=20, choices=CATEGORIAS, default='Outros')  # <- agora é dropdown no admin

    def __str__(self):
        return f"{self.nome}"


class Combo(models.Model):
    produto_ptr = models.OneToOneField(Produto, on_delete=models.CASCADE, related_name='combo')
    TIPO_COMBO = [
        ('fixo', 'Fixo'),
        ('opcional', 'Com opções'),
    ]
    tipo = models.CharField(max_length=10, choices=TIPO_COMBO, default='fixo')

    def __str__(self):
        return f"{self.produto_ptr.nome} ({self.get_tipo_display()})"

    def descricao_itens(self):
        return " e ".join(
            [f"{item.produto.nome}" for item in self.itens.all()]
        )
    
    def descricao_completa(self):
        return f"{self.produto_ptr.nome} ({', '.join([f'{item.quantidade}x {item.produto.nome}' for item in self.itens.all()])})"

    @property
    def descricao_resumida(self):
        partes = []

        # Produtos fixos no combo
        for item in self.itens.all():
            partes.append(f"{item.produto.nome}")

        # Opções para o cliente escolher
        for opcao in self.opcoes.all():
            partes.append(f"escolha alguma opção de {opcao.get_categoria_display()}")

        return ", ".join(partes)
    

class ItemCombo(models.Model):
    combo = models.ForeignKey(Combo, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    quantidade = models.PositiveIntegerField(default=1)  # ✅ Isso representa quantos do produto vão no combo!


    def __str__(self):
        return f"{self.combo.produto_ptr.nome} - {self.produto.nome}"



class OpcaoCombo(models.Model):
    combo = models.ForeignKey(Combo, on_delete=models.CASCADE, related_name='opcoes')
    categoria = models.CharField(max_length=20, choices=Produto.CATEGORIAS)

    def __str__(self):
        return f"{self.combo} - Escolha 1 de {self.get_categoria_display()}"

    def validar_escolhas_opcionais(self, escolhas: dict):
        """
        escolhas = {'Bebidas': produto_id, 'Salgados': produto_id}
        """
        for opcao in self.combo.opcoes.all():
            produto_id = escolhas.get(opcao.categoria)
            if not produto_id:
                raise ValueError(f"Escolha de {opcao.get_categoria_display()} não fornecida.")
            produto = Produto.objects.get(id=produto_id)
            if produto.quantidade < 1:
                raise ValueError(f"Produto {produto.nome} sem estoque.")


class Pedido(models.Model):

    FORMA_PAGAMENTO = [
        ('PIX', 'PIX'),
        ('Dinheiro', 'Dinheiro'),
    ]
    TIPO_CONSUMO = [
        ('local', 'Comer no local'),
        ('viagem', 'Levar para viagem'),
    ]

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)  # Relacionamento correto
    produtos = models.ManyToManyField(Produto, through='ItemPedido')
    metodo_pagamento = models.CharField(max_length=10, choices=FORMA_PAGAMENTO)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tipo_consumo = models.CharField(max_length=10, choices=TIPO_CONSUMO, default='local')
    observacoes = models.TextField(blank=True, null=True)  # Observações do cliente
    liberado_para_cozinha = models.BooleanField(default=False)
    liberado_para_caixa = models.BooleanField(default=False)
    time_liberado_para_cozinha = models.DateTimeField(null=True, blank=True)
    time_off = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        itens = self.itens.all()
        produtos_str = ', '.join([f"{item.produto.nome} (x{item.quantidade})" for item in itens])
        return f"{self.cliente} -> {produtos_str} -> R$ {self.total:.2f}"
    
    def calcular_total(self):
        total = sum(item.produto.preco * item.quantidade for item in self.itens.all())
        return total
    
    def atualizar_total(self):
        self.total = self.calcular_total()
        super().save(update_fields=['total'])  # Atualiza apenas o campo total

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)  # Salva o pedido primeiro para obter um ID válido
        self.atualizar_total()  # Calcula e salva o total atualizado

class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    quantidade = models.IntegerField(default=0)
    escolhas_combo = models.JSONField(null=True, blank=True)  # 👈 Salva os produtos escolhidos no combo

    def __str__(self):
        return f"{self.quantidade}x {self.produto.nome} -> {self.pedido.cliente}"
    
    def save(self, *args, **kwargs):
        if self.pk:  
            item_antigo = ItemPedido.objects.get(pk=self.pk)
            diferenca = self.quantidade - item_antigo.quantidade
        else:
            diferenca = self.quantidade

        combo = getattr(self.produto, 'combo', None)
        if combo and combo.tipo == 'fixo':
            for item_combo in combo.itens.all():
                produto_estoque = item_combo.produto
                total_a_abater = item_combo.quantidade * diferenca
                if produto_estoque.quantidade < total_a_abater:
                    raise ValueError(f"Estoque insuficiente para {produto_estoque.nome}")
                # produto_estoque.quantidade -= total_a_abater
                produto_estoque.save()
        else:
            if diferenca > self.produto.quantidade:
                raise ValueError(f"Estoque insuficiente para {self.produto.nome}")
            # self.produto.quantidade -= diferenca
            self.produto.save()

        super().save(*args, **kwargs)
        self.pedido.atualizar_total()


    def delete(self, *args, **kwargs):
        # self.produto.quantidade += self.quantidade  # Devolve a quantidade ao estoque ao excluir
        # self.produto.save()
        # super().delete(*args, **kwargs)  # Remove o item primeiro
        # self.pedido.atualizar_total()  # Atualiza o total do pedido após excluir o item
        if hasattr(self.produto, 'combo') and self.produto.combo.tipo == 'fixo':
            combo = self.produto.combo
            for item_combo in combo.itens.all():
                item_combo.produto.quantidade += item_combo.quantidade * self.quantidade
                item_combo.produto.save()
        else:
            self.produto.quantidade += self.quantidade
            self.produto.save()

        super().delete(*args, **kwargs)
        self.pedido.atualizar_total()

class PedidoEntregue(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    itens = models.TextField()
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0) 
    metodo_pagamento = models.CharField(max_length=10, choices=Pedido.FORMA_PAGAMENTO, default='PIX') 
    entregue_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.cliente.nome}"
    
class PedidoCancelado(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True)
    itens = models.TextField()
    metodo_pagamento = models.CharField(max_length=100)
    cancelado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.cliente.nome} -> {self.itens}"