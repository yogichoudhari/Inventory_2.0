from django.db import models
from user.models import Account
from datetime import datetime
from django.utils import timezone
# Create your models here.
class AccountCredentials(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    client_id = models.BinaryField()
    client_secret = models.BinaryField()
    base_url = models.URLField()

    

class EncryptionKeyId(models.Model):
    keyid = models.CharField(max_length=256)
    
class Auth(models.Model):
    expires_at = models.DateTimeField()
    access_token = models.BinaryField()
    refresh_token = models.BinaryField()
    account = models.ForeignKey(Account,on_delete=models.CASCADE)
    def save(self, *args, **kwargs):
        self.expires_at = timezone.now() + timezone.timedelta(hours=2)
        super(Auth, self).save(*args, **kwargs)
