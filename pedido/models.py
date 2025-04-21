from django.db import models
from django.contrib.auth.models import AbstractUser

class Cliente(models.Model):
    nome = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.id} - {self.nome}" 

class Produto(models.Model):
    nome = models.CharField(max_length=70, unique=True) 
    preco = models.DecimalField(max_digits=10, decimal_places=2)  # Preço do produto
    imagem = models.ImageField(upload_to='imagem_produto', null=True, blank=True) # torna a imagem como opcional 
    quantidade = models.PositiveIntegerField(default=0)  # Estoque do produto

    def __str__(self):
        return f"{self.nome}"

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

    def __str__(self):
        return f"{self.cliente}"
    
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

    def __str__(self):
        return f"{self.quantidade}x {self.produto.nome} -> {self.pedido.cliente}"
    
    def save(self, *args, **kwargs):
        if self.pk:  
            item_antigo = ItemPedido.objects.get(pk=self.pk)
            diferenca = self.quantidade - item_antigo.quantidade
        else:
            diferenca = self.quantidade

        if diferenca > self.produto.quantidade:
            raise ValueError(f"Estoque insuficiente para {self.produto.nome}. Disponível: {self.produto.quantidade}")

        self.produto.quantidade -= diferenca
        self.produto.save()

        super().save(*args, **kwargs)
        self.pedido.atualizar_total()


    def delete(self, *args, **kwargs):
        self.produto.quantidade += self.quantidade  # Devolve a quantidade ao estoque ao excluir
        self.produto.save()
        super().delete(*args, **kwargs)  # Remove o item primeiro
        self.pedido.atualizar_total()  # Atualiza o total do pedido após excluir o item

class PedidoEntregue(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    itens = models.TextField()
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0) 
    metodo_pagamento = models.CharField(max_length=10, choices=Pedido.FORMA_PAGAMENTO, default='PIX') 
    entregue_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.cliente.nome}"
    
class Usuario(AbstractUser):
    usuario = models.ManyToManyField("usurio") # SO para ter algo 