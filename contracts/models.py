from django.db import models
from django.conf import settings

class Contract(models.Model):
    order = models.OneToOneField('cart.Order', on_delete=models.CASCADE, related_name='contract')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='contracts')
    contract_number = models.CharField(max_length=50, unique=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    pdf_file = models.FileField(upload_to='contracts/', blank=True, null=True)
    blockchain_hash = models.CharField(max_length=64, blank=True)
    
    def __str__(self):
        return f"Contrat {self.contract_number}"
