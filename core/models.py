from django.db import models

class HeroSlide(models.Model):
    title = models.CharField(max_length=200)
    subtitle = models.TextField(blank=True)
    image = models.ImageField(upload_to='hero/')
    button_text = models.CharField(max_length=50, default='Découvrir')
    button_link = models.CharField(max_length=200, default='/equipements/')
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return self.title

class SiteInfo(models.Model):
    company_name = models.CharField(max_length=200, default='RAOLY BTP')
    slogan = models.CharField(max_length=300, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    about_text = models.TextField(blank=True)
    facebook = models.URLField(blank=True)
    instagram = models.URLField(blank=True)
    twitter = models.URLField(blank=True)
    whatsapp = models.CharField(max_length=20, blank=True)
    
    class Meta:
        verbose_name = "Informations du site"
        verbose_name_plural = "Informations du site"
    
    def __str__(self):
        return self.company_name
