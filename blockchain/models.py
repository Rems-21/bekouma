from django.db import models
import hashlib
import json
from datetime import datetime

class Block(models.Model):
    index = models.PositiveIntegerField(unique=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    data = models.JSONField()
    previous_hash = models.CharField(max_length=64)
    hash = models.CharField(max_length=64)
    
    class Meta:
        ordering = ['index']
    
    def __str__(self):
        return f"Block #{self.index}"
    
    @staticmethod
    def calculate_hash(index, timestamp, data, previous_hash):
        value = f"{index}{timestamp}{json.dumps(data, sort_keys=True, default=str)}{previous_hash}"
        return hashlib.sha256(value.encode()).hexdigest()
    
    def save(self, *args, **kwargs):
        if not self.hash:
            self.hash = self.calculate_hash(
                self.index,
                self.timestamp or datetime.now(),
                self.data,
                self.previous_hash
            )
        super().save(*args, **kwargs)
